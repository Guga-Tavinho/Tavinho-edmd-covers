from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageEnhance


MAGIC = b"SCIM"
VERSION = 1
HEADER_STRUCT = struct.Struct(">4sBBBBHHHHIIII")
HEADER_SIZE = HEADER_STRUCT.size
DEFAULT_TILE_BASE = 0x0200
FLAG_LINEAR_TILES = 0x01


def genesis_color(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    r3 = round(r * 7 / 255)
    g3 = round(g * 7 / 255)
    b3 = round(b * 7 / 255)
    return (b3 << 9) | (g3 << 5) | (r3 << 1)


def rgb_from_genesis(word: int) -> tuple[int, int, int]:
    r3 = (word >> 1) & 7
    g3 = (word >> 5) & 7
    b3 = (word >> 9) & 7
    return (round(r3 * 255 / 7), round(g3 * 255 / 7), round(b3 * 255 / 7))


def crop_to_ratio(img: Image.Image, width: int, height: int) -> Image.Image:
    target = width / height
    ratio = img.width / img.height
    if ratio > target:
        new_width = int(img.height * target)
        left = (img.width - new_width) // 2
        return img.crop((left, 0, left + new_width, img.height))
    new_height = int(img.width / target)
    top = (img.height - new_height) // 2
    return img.crop((0, top, img.width, top + new_height))


def adjust_levels(img: Image.Image, black: int = 14, white: int = 248) -> Image.Image:
    scale = 255 / max(1, white - black)
    lut = [max(0, min(255, round((value - black) * scale))) for value in range(256)]
    return img.point(lut * 3)


def nearest_color_index(pixel: tuple[int, int, int], palette: list[tuple[int, int, int]], usable: list[int]) -> int:
    r, g, b = pixel[:3]
    best_index = usable[0]
    best_dist = 1 << 30
    for index in usable:
        pr, pg, pb = palette[index]
        dr = r - pr
        dg = g - pg
        db = b - pb
        dist = dr * dr + dg * dg + db * db
        if dist < best_dist:
            best_dist = dist
            best_index = index
    return best_index


def build_natural_palette(image: Image.Image) -> list[tuple[int, int, int]]:
    quantized = image.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    raw = quantized.getpalette()[: 16 * 3]
    palette: list[tuple[int, int, int]] = []
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
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 146, 0),
        (146, 73, 0), (146, 0, 0), (0, 146, 0), (0, 0, 146),
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


def normalize_crop_box(img: Image.Image, width: int, height: int, crop_box: tuple[float, float, float, float] | None) -> Image.Image:
    if crop_box is None:
        return crop_to_ratio(img, width, height)

    left, top, right, bottom = crop_box
    left = max(0.0, min(1.0, left))
    top = max(0.0, min(1.0, top))
    right = max(0.0, min(1.0, right))
    bottom = max(0.0, min(1.0, bottom))
    if right <= left or bottom <= top:
        return crop_to_ratio(img, width, height)

    px_left = max(0, min(img.width - 1, round(left * img.width)))
    px_top = max(0, min(img.height - 1, round(top * img.height)))
    px_right = max(px_left + 1, min(img.width, round(right * img.width)))
    px_bottom = max(px_top + 1, min(img.height, round(bottom * img.height)))
    cropped = img.crop((px_left, px_top, px_right, px_bottom))
    return crop_to_ratio(cropped, width, height)


def quantize_image(
    src: Image.Image,
    width_tiles: int,
    height_tiles: int,
    crop_box: tuple[float, float, float, float] | None = None,
) -> Image.Image:
    size = (width_tiles * 8, height_tiles * 8)
    img = src.convert("RGB")
    canvas = normalize_crop_box(img, size[0], size[1], crop_box).resize(size, Image.Resampling.LANCZOS)
    canvas = adjust_levels(canvas)
    canvas = ImageEnhance.Contrast(canvas).enhance(1.12)
    canvas = ImageEnhance.Color(canvas).enhance(1.12)
    canvas = ImageEnhance.Sharpness(canvas).enhance(1.08)
    rgb_palette = build_natural_palette(canvas)
    qimg = Image.new("P", size)
    flat_palette: list[int] = []
    for color in rgb_palette:
        flat_palette.extend(color)
    qimg.putpalette(flat_palette)
    pixels = bytearray()
    usable_indices = list(range(15))
    for y in range(size[1]):
        for x in range(size[0]):
            pixels.append(nearest_color_index(canvas.getpixel((x, y)), rgb_palette, usable_indices))
    qimg.frombytes(bytes(pixels))
    return qimg


def palette_words(img: Image.Image) -> list[int]:
    raw = img.getpalette()[: 16 * 3]
    colors = [tuple(raw[i : i + 3]) for i in range(0, len(raw), 3)]
    colors += [(0, 0, 0)] * (16 - len(colors))
    return [genesis_color(c) for c in colors[:16]]


def encode_tile(indices: list[int]) -> bytes:
    out = bytearray()
    for row in range(8):
        base = row * 8
        for col in range(0, 8, 2):
            hi = indices[base + col] & 0x0F
            lo = indices[base + col + 1] & 0x0F
            out.append((hi << 4) | lo)
    return bytes(out)


def build_scimg(
    input_path: Path,
    output_path: Path,
    width_tiles: int,
    height_tiles: int,
    tile_base: int,
    crop_box: tuple[float, float, float, float] | None = None,
) -> dict[str, int | str]:
    qimg = quantize_image(Image.open(input_path), width_tiles, height_tiles, crop_box)
    px = qimg.load()
    pal = palette_words(qimg)

    tiles: list[bytes] = []
    tile_to_index: dict[bytes, int] = {}
    tilemap: list[int] = []

    for ty in range(height_tiles):
        for tx in range(width_tiles):
            indices = [px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)]
            tile = encode_tile(indices)
            idx = tile_to_index.get(tile)
            if idx is None:
                idx = len(tiles)
                tile_to_index[tile] = idx
                tiles.append(tile)
            tilemap.append(tile_base + idx)

    palette_offset = HEADER_SIZE
    tile_data_offset = palette_offset + 16 * 2
    tilemap_offset = tile_data_offset + len(tiles) * 32
    payload_for_crc = b"".join(
        [
            struct.pack(">" + "H" * 16, *pal),
            b"".join(tiles),
            struct.pack(">" + "H" * len(tilemap), *tilemap),
        ]
    )
    crc = zlib.crc32(payload_for_crc) & 0xFFFFFFFF
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        width_tiles,
        height_tiles,
        16,
        0,
        tile_base,
        len(tiles),
        0,
        palette_offset,
        tile_data_offset,
        tilemap_offset,
        crc,
    )
    output_path.write_bytes(header + payload_for_crc)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "width_px": width_tiles * 8,
        "height_px": height_tiles * 8,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "tile_base": tile_base,
        "unique_tiles": len(tiles),
        "size_bytes": output_path.stat().st_size,
        "crc32": f"{crc:08x}",
    }


def write_linear_scimg(
    output_path: Path,
    width_tiles: int,
    height_tiles: int,
    tile_base: int,
    pal: list[int],
    tiles: bytes,
    align_tiles: bool = False,
) -> dict[str, int | str]:
    tile_count = width_tiles * height_tiles
    if len(tiles) != tile_count * 32:
        raise ValueError(f"expected {tile_count * 32} tile bytes, got {len(tiles)}")

    pal = (pal + [0] * 16)[:16]
    palette_offset = HEADER_SIZE
    tile_data_offset = 0x200 if align_tiles else palette_offset + 16 * 2
    tilemap_offset = 0
    palette_blob = struct.pack(">" + "H" * 16, *pal)
    padding = bytes(tile_data_offset - (palette_offset + len(palette_blob)))
    payload_for_crc = palette_blob + padding + tiles
    crc = zlib.crc32(payload_for_crc) & 0xFFFFFFFF
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        width_tiles,
        height_tiles,
        16,
        FLAG_LINEAR_TILES | (0x02 if align_tiles else 0),
        tile_base,
        tile_count,
        0,
        palette_offset,
        tile_data_offset,
        tilemap_offset,
        crc,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(header + payload_for_crc)
    return {
        "output": str(output_path),
        "width_px": width_tiles * 8,
        "height_px": height_tiles * 8,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "tile_base": tile_base,
        "tile_count": tile_count,
        "flags": FLAG_LINEAR_TILES | (0x02 if align_tiles else 0),
        "size_bytes": output_path.stat().st_size,
        "crc32": f"{crc:08x}",
    }


def build_linear_scimg(
    input_path: Path,
    output_path: Path,
    width_tiles: int,
    height_tiles: int,
    tile_base: int,
    align_tiles: bool = False,
    crop_box: tuple[float, float, float, float] | None = None,
) -> dict[str, int | str]:
    qimg = quantize_image(Image.open(input_path), width_tiles, height_tiles, crop_box)
    px = qimg.load()
    pal = palette_words(qimg)
    tiles = bytearray()
    for ty in range(height_tiles):
        for tx in range(width_tiles):
            indices = [px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)]
            tiles.extend(encode_tile(indices))
    result = write_linear_scimg(output_path, width_tiles, height_tiles, tile_base, pal, bytes(tiles), align_tiles)
    result["input"] = str(input_path)
    return result


def read_scimg(path: Path) -> tuple[dict[str, int], list[int], bytes, list[int]]:
    data = path.read_bytes()
    if len(data) < HEADER_SIZE:
        raise ValueError("file is too small")
    magic, version, width, height, pal_count, flags, tile_base, tile_count, _reserved, pal_off, tile_off, map_off, crc = HEADER_STRUCT.unpack(
        data[:HEADER_SIZE]
    )
    if magic != MAGIC:
        raise ValueError("not a SCIMG file")
    if version != VERSION:
        raise ValueError(f"unsupported SCIMG version {version}")
    payload_end = len(data) if flags & FLAG_LINEAR_TILES else len(data)
    payload = data[pal_off:payload_end]
    if (zlib.crc32(payload) & 0xFFFFFFFF) != crc:
        raise ValueError("CRC32 mismatch")
    pal = list(struct.unpack(">" + "H" * pal_count, data[pal_off : pal_off + pal_count * 2]))
    tiles = data[tile_off : tile_off + tile_count * 32]
    tilemap_count = width * height
    if flags & FLAG_LINEAR_TILES:
        tilemap = [tile_base + idx for idx in range(tilemap_count)]
    else:
        tilemap = list(struct.unpack(">" + "H" * tilemap_count, data[map_off : map_off + tilemap_count * 2]))
    meta = {
        "version": version,
        "width_tiles": width,
        "height_tiles": height,
        "palette_count": pal_count,
        "flags": flags,
        "tile_base": tile_base,
        "tile_count": tile_count,
        "palette_offset": pal_off,
        "tile_data_offset": tile_off,
        "tilemap_offset": map_off,
        "crc32": crc,
        "size_bytes": len(data),
    }
    return meta, pal, tiles, tilemap


def linearize_scimg(input_path: Path, output_path: Path, align_tiles: bool = False) -> dict[str, int | str]:
    meta, pal, tiles, tilemap = read_scimg(input_path)
    width_tiles = meta["width_tiles"]
    height_tiles = meta["height_tiles"]
    tile_base = meta["tile_base"]
    linear_tiles = bytearray()
    for raw_attr in tilemap:
        raw_idx = raw_attr & 0x07FF
        idx = raw_idx - tile_base
        if idx < 0 or idx >= meta["tile_count"]:
            linear_tiles.extend(bytes(32))
        else:
            linear_tiles.extend(tiles[idx * 32 : idx * 32 + 32])
    result = write_linear_scimg(output_path, width_tiles, height_tiles, tile_base, pal, bytes(linear_tiles), align_tiles)
    result["input"] = str(input_path)
    return result


def remap_tile_color(tiles: bytes, source: int, target: int) -> bytes:
    out = bytearray()
    source &= 0x0F
    target &= 0x0F
    for byte in tiles:
        hi = target if (byte >> 4) == source else byte >> 4
        lo = target if (byte & 0x0F) == source else byte & 0x0F
        out.append((hi << 4) | lo)
    return bytes(out)


def make_opaque_scimg(input_path: Path, output_path: Path, opaque_index: int = 15) -> dict[str, int | str]:
    meta, pal, tiles, _tilemap = read_scimg(input_path)
    if not (meta["flags"] & FLAG_LINEAR_TILES):
        raise ValueError("opaque rewrite expects a linear SCIMG; run linearize first")
    pal = pal[:16]
    source_zero_color = pal[0]
    pal[opaque_index & 0x0F] = source_zero_color
    opaque_tiles = remap_tile_color(tiles, 0, opaque_index)
    result = write_linear_scimg(
        output_path,
        meta["width_tiles"],
        meta["height_tiles"],
        meta["tile_base"],
        pal,
        opaque_tiles,
        bool(meta["flags"] & 0x02),
    )
    result["input"] = str(input_path)
    result["opaque_index"] = opaque_index & 0x0F
    return result


def decode_tile(tile: bytes) -> list[int]:
    out: list[int] = []
    for byte in tile:
        out.append(byte >> 4)
        out.append(byte & 0x0F)
    return out


def preview_scimg(input_path: Path, output_path: Path) -> dict[str, int | str]:
    meta, pal, tiles, tilemap = read_scimg(input_path)
    width_px = meta["width_tiles"] * 8
    height_px = meta["height_tiles"] * 8
    rgb = [rgb_from_genesis(word) for word in pal]
    out = Image.new("RGB", (width_px, height_px))
    tile_base = meta["tile_base"]
    for ty in range(meta["height_tiles"]):
        for tx in range(meta["width_tiles"]):
            raw_idx = tilemap[ty * meta["width_tiles"] + tx] & 0x07FF
            idx = raw_idx - tile_base
            if idx < 0 or idx >= meta["tile_count"]:
                continue
            decoded = decode_tile(tiles[idx * 32 : idx * 32 + 32])
            for y in range(8):
                for x in range(8):
                    out.putpixel((tx * 8 + x, ty * 8 + y), rgb[decoded[y * 8 + x]])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "width_px": width_px,
        "height_px": height_px,
        "tile_count": meta["tile_count"],
        "size_bytes": meta["size_bytes"],
        "crc32": f"{meta['crc32']:08x}",
    }


def inspect_scimg(input_path: Path) -> dict[str, int | str]:
    meta, _pal, _tiles, _tilemap = read_scimg(input_path)
    return {k: (f"0x{v:04x}" if k == "tile_base" else v) for k, v in meta.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, inspect, and preview Mega Drive SCIMG cover files.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="convert an image to .scimg")
    build.add_argument("input")
    build.add_argument("output")
    build.add_argument("--width-tiles", type=int, default=16)
    build.add_argument("--height-tiles", type=int, default=14)
    build.add_argument("--tile-base", type=lambda x: int(x, 0), default=DEFAULT_TILE_BASE)

    linear = sub.add_parser("build-linear", help="convert an image to a linear .scimg")
    linear.add_argument("input")
    linear.add_argument("output")
    linear.add_argument("--width-tiles", type=int, default=16)
    linear.add_argument("--height-tiles", type=int, default=14)
    linear.add_argument("--tile-base", type=lambda x: int(x, 0), default=DEFAULT_TILE_BASE)
    linear.add_argument("--align-sector", action="store_true")

    linearize = sub.add_parser("linearize", help="rewrite an existing .scimg with tiles in screen order")
    linearize.add_argument("input")
    linearize.add_argument("output")
    linearize.add_argument("--align-sector", action="store_true")

    opaque = sub.add_parser("opaque", help="rewrite linear .scimg so color index 0 is not used by pixels")
    opaque.add_argument("input")
    opaque.add_argument("output")
    opaque.add_argument("--opaque-index", type=lambda x: int(x, 0), default=15)

    preview = sub.add_parser("preview", help="render a .scimg back to PNG")
    preview.add_argument("input")
    preview.add_argument("output")

    inspect = sub.add_parser("inspect", help="print .scimg metadata")
    inspect.add_argument("input")

    args = parser.parse_args()
    if args.cmd == "build":
        result = build_scimg(Path(args.input), Path(args.output), args.width_tiles, args.height_tiles, args.tile_base)
    elif args.cmd == "build-linear":
        result = build_linear_scimg(
            Path(args.input),
            Path(args.output),
            args.width_tiles,
            args.height_tiles,
            args.tile_base,
            args.align_sector,
        )
    elif args.cmd == "linearize":
        result = linearize_scimg(Path(args.input), Path(args.output), args.align_sector)
    elif args.cmd == "opaque":
        result = make_opaque_scimg(Path(args.input), Path(args.output), args.opaque_index)
    elif args.cmd == "preview":
        result = preview_scimg(Path(args.input), Path(args.output))
    else:
        result = inspect_scimg(Path(args.input))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
