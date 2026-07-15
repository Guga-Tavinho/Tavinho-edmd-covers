from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageEnhance

from scimg_tool import adjust_levels, crop_to_ratio, encode_tile, genesis_color, rgb_from_genesis


MAGIC = b"SC2P"
VERSION = 1
WIDTH_TILES = 16
HEIGHT_TILES = 14
TILE_COUNT = WIDTH_TILES * HEIGHT_TILES
HEADER_SIZE = 0x20
PALETTE_OFFSET = 0x20
ATTR_OFFSET = 0x60
TILE_DATA_OFFSET = 0x200
FILE_SIZE = TILE_DATA_OFFSET + TILE_COUNT * 32


def nearest_color_index(pixel: tuple[int, int, int], palette: list[tuple[int, int, int]]) -> int:
    r, g, b = pixel
    best_index = 0
    best_dist = 1 << 30
    for index, (pr, pg, pb) in enumerate(palette):
        dr = r - pr
        dg = g - pg
        db = b - pb
        dist = dr * dr + dg * dg + db * db
        if dist < best_dist:
            best_dist = dist
            best_index = index
    return best_index


def preprocess(src: Image.Image) -> Image.Image:
    size = (WIDTH_TILES * 8, HEIGHT_TILES * 8)
    img = crop_to_ratio(src.convert("RGB"), size[0], size[1]).resize(size, Image.Resampling.LANCZOS)
    img = adjust_levels(img)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.12)
    img = ImageEnhance.Sharpness(img).enhance(1.08)
    return img


def tile_average(img: Image.Image, tx: int, ty: int) -> tuple[float, float, float]:
    rs = gs = bs = 0
    for y in range(8):
        for x in range(8):
            r, g, b = img.getpixel((tx * 8 + x, ty * 8 + y))
            rs += r
            gs += g
            bs += b
    return rs / 64, gs / 64, bs / 64


def cluster_tiles(img: Image.Image) -> list[int]:
    averages = [tile_average(img, tx, ty) for ty in range(HEIGHT_TILES) for tx in range(WIDTH_TILES)]
    centers = [min(averages, key=lambda c: c[0] + c[1] + c[2]), max(averages, key=lambda c: c[0] + c[1] + c[2])]
    assignments = [0] * len(averages)
    for _ in range(8):
        for idx, avg in enumerate(averages):
            distances = []
            for center in centers:
                distances.append(sum((avg[ch] - center[ch]) ** 2 for ch in range(3)))
            assignments[idx] = 0 if distances[0] <= distances[1] else 1
        for cluster in range(2):
            members = [avg for avg, assigned in zip(averages, assignments) if assigned == cluster]
            if not members:
                continue
            centers[cluster] = tuple(sum(m[ch] for m in members) / len(members) for ch in range(3))
    return assignments


def quantize_palette(colors: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    if not colors:
        colors = [(0, 0, 0)]
    sample = Image.new("RGB", (len(colors), 1))
    sample.putdata(colors)
    quantized = sample.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    raw = quantized.getpalette()[: 15 * 3]
    # Palette index 0 is transparent on Mega Drive background planes, so keep
    # it reserved and map real pixels only to indices 1..15.
    palette: list[tuple[int, int, int]] = [(0, 0, 0)]
    used: set[int] = set()
    for i in range(0, len(raw), 3):
        word = genesis_color(tuple(raw[i : i + 3]))
        if word in used:
            continue
        used.add(word)
        palette.append(rgb_from_genesis(word))
        if len(palette) == 16:
            break
    fallback = [
        (0, 0, 0), (255, 255, 255), (146, 146, 146), (73, 73, 73),
        (255, 0, 0), (0, 0, 255), (255, 146, 0), (146, 73, 0),
    ]
    for color in fallback:
        if len(palette) == 16:
            break
        word = genesis_color(color)
        if word in used:
            continue
        used.add(word)
        palette.append(rgb_from_genesis(word))
    return (palette + [(0, 0, 0)] * 16)[:16]


def build_palettes(img: Image.Image, assignments: list[int]) -> list[list[tuple[int, int, int]]]:
    grouped: list[list[tuple[int, int, int]]] = [[], []]
    for ty in range(HEIGHT_TILES):
        for tx in range(WIDTH_TILES):
            cluster = assignments[ty * WIDTH_TILES + tx]
            for y in range(8):
                for x in range(8):
                    grouped[cluster].append(img.getpixel((tx * 8 + x, ty * 8 + y)))
    return [quantize_palette(grouped[0]), quantize_palette(grouped[1])]


def encode_sc2p(input_path: Path, output_path: Path) -> dict[str, object]:
    img = preprocess(Image.open(input_path))
    assignments = cluster_tiles(img)
    palettes = build_palettes(img, assignments)

    tiles = bytearray()
    for ty in range(HEIGHT_TILES):
        for tx in range(WIDTH_TILES):
            tile_index = ty * WIDTH_TILES + tx
            pal = palettes[assignments[tile_index]]
            indices = [
                1 + nearest_color_index(img.getpixel((tx * 8 + x, ty * 8 + y)), pal[1:])
                for y in range(8)
                for x in range(8)
            ]
            tiles.extend(encode_tile(indices))

    data = bytearray(FILE_SIZE)
    crc_payload = (
        struct.pack(">" + "H" * 16, *[genesis_color(c) for c in palettes[0]])
        + struct.pack(">" + "H" * 16, *[genesis_color(c) for c in palettes[1]])
        + bytes(assignments)
        + bytes(tiles)
    )
    crc = zlib.crc32(crc_payload) & 0xFFFFFFFF
    data[:HEADER_SIZE] = struct.pack(
        ">4sBBBBHHHHIIII",
        MAGIC,
        VERSION,
        WIDTH_TILES,
        HEIGHT_TILES,
        32,
        0x10,
        0x0200,
        TILE_COUNT,
        0,
        PALETTE_OFFSET,
        TILE_DATA_OFFSET,
        ATTR_OFFSET,
        crc,
    )
    struct.pack_into(">" + "H" * 16, data, PALETTE_OFFSET, *[genesis_color(c) for c in palettes[0]])
    struct.pack_into(">" + "H" * 16, data, PALETTE_OFFSET + 32, *[genesis_color(c) for c in palettes[1]])
    data[ATTR_OFFSET : ATTR_OFFSET + TILE_COUNT] = bytes(0xE0 if assigned else 0x80 for assigned in assignments)
    data[TILE_DATA_OFFSET : TILE_DATA_OFFSET + len(tiles)] = tiles
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "width_px": WIDTH_TILES * 8,
        "height_px": HEIGHT_TILES * 8,
        "tile_count": TILE_COUNT,
        "size_bytes": len(data),
        "crc32": f"{crc:08x}",
    }


def preview_sc2p(input_path: Path, output_path: Path) -> dict[str, object]:
    data = input_path.read_bytes()
    if data[:4] != MAGIC:
        raise ValueError("not an SC2P file")
    pal0 = [rgb_from_genesis(w) for w in struct.unpack_from(">" + "H" * 16, data, PALETTE_OFFSET)]
    pal1 = [rgb_from_genesis(w) for w in struct.unpack_from(">" + "H" * 16, data, PALETTE_OFFSET + 32)]
    attrs = data[ATTR_OFFSET : ATTR_OFFSET + TILE_COUNT]
    tiles = data[TILE_DATA_OFFSET : TILE_DATA_OFFSET + TILE_COUNT * 32]
    out = Image.new("RGB", (WIDTH_TILES * 8, HEIGHT_TILES * 8))
    for ty in range(HEIGHT_TILES):
        for tx in range(WIDTH_TILES):
            tile_index = ty * WIDTH_TILES + tx
            pal = pal1 if attrs[tile_index] == 0xE0 else pal0
            tile = tiles[tile_index * 32 : tile_index * 32 + 32]
            for y in range(8):
                for x in range(8):
                    byte = tile[y * 4 + x // 2]
                    color = (byte >> 4) if x % 2 == 0 else (byte & 0x0F)
                    out.putpixel((tx * 8 + x, ty * 8 + y), pal[color])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    return {"input": str(input_path), "output": str(output_path), "size": list(out.size)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and preview 2-palette Mega Drive SC2P covers.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build")
    build.add_argument("input", type=Path)
    build.add_argument("output", type=Path)
    preview = sub.add_parser("preview")
    preview.add_argument("input", type=Path)
    preview.add_argument("output", type=Path)
    args = parser.parse_args()
    result = encode_sc2p(args.input, args.output) if args.cmd == "build" else preview_sc2p(args.input, args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
