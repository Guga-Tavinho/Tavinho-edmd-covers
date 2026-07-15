from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

from PIL import Image

from scimg_tool import encode_tile, make_opaque_scimg, palette_words, preview_scimg, quantize_image, read_scimg, write_linear_scimg
from edmd_build_cover_pack_paged_h160 import build_paged_pack


IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
ROM_EXTS = {".bin"}
SKIP_ROM_DIRS = {"EDMD", "SAVE", "SYSTEM VOLUME INFORMATION"}
SKIP_ROM_PREFIXES = ("POC", "OS-UPDATE", "DANGER-", "EXPERIMENT-")
SKIP_ROM_NAMES = {"MDOS.BIN", "OS-V36.BIN"}
VISIBLE_WIDTH_TILES = 16
STORAGE_WIDTH_TILES = 16
HEIGHT_TILES = 20
INDEX_SECTORS = 15


def load_crop_map(path: Path | None) -> dict[str, tuple[float, float, float, float]]:
    if path is None or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    crops = raw.get("crops", raw if isinstance(raw, dict) else {})
    result: dict[str, tuple[float, float, float, float]] = {}
    if not isinstance(crops, dict):
        return result
    for key, value in crops.items():
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            continue
        try:
            result[str(key).upper()] = tuple(float(v) for v in value)  # type: ignore[assignment]
        except (TypeError, ValueError):
            continue
    return result


def crop_for_image(path: Path, input_dir: Path, crop_map: dict[str, tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    keys = [path.name.upper(), path.stem.upper(), path.as_posix().upper()]
    try:
        keys.append(path.relative_to(input_dir).as_posix().upper())
    except ValueError:
        pass
    for key in keys:
        crop = crop_map.get(key)
        if crop is not None:
            return crop
    return None


def normalize_key(text: str) -> str:
    text = text.replace("_", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def title_key(text: str) -> str:
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = text.split("~", 1)[0]
    return normalize_key(text)


def pack_letter_for_name(name: str) -> str:
    ch = name[:1].upper()
    return "0" if ch.isdigit() else ch if "A" <= ch <= "Z" else "_"


def lookup_keys(path: Path, root: Path | None = None) -> list[str]:
    keys = [path.name.upper(), normalize_key(path.stem)]
    if root is not None:
        try:
            keys.append(path.relative_to(root).as_posix().upper())
        except ValueError:
            pass
    return keys


def build_lookup(paths: list[Path], root: Path | None = None) -> dict[str, list[Path]]:
    lookup: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        for key in lookup_keys(path, root):
            lookup[key].append(path)
    return lookup


def resolve_from_lookup(raw_value: str, root: Path, lookup: dict[str, list[Path]]) -> Path | None:
    value = raw_value.strip().strip('"')
    if not value:
        return None

    raw_path = Path(value)
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path.resolve()

    rooted = root / value
    if rooted.exists():
        return rooted.resolve()

    candidates = lookup.get(value.upper()) or lookup.get(normalize_key(Path(value).stem))
    if candidates:
        return sorted({p.resolve(): p for p in candidates}.values(), key=lambda p: p.as_posix().upper())[0]
    return None


def iter_roms(rom_root: Path) -> list[Path]:
    roms: list[Path] = []
    for path in rom_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ROM_EXTS:
            continue
        parts = {part.upper() for part in path.relative_to(rom_root).parts[:-1]}
        if parts & SKIP_ROM_DIRS:
            continue
        name_upper = path.name.upper()
        if name_upper in SKIP_ROM_NAMES or any(name_upper.startswith(prefix) for prefix in SKIP_ROM_PREFIXES):
            continue
        roms.append(path)
    return sorted({p.resolve(): p for p in roms}.values(), key=lambda p: p.name.upper())


def read_manual_map(
    map_csv: Path | None,
    input_dir: Path,
    images: list[Path],
    rom_root: Path | None,
    roms: list[Path],
) -> tuple[dict[Path, list[Path]], list[dict[str, str]], list[Path]]:
    if map_csv is None:
        return {}, [], images
    if rom_root is None:
        return {}, [{"row": "0", "error": "--map-csv precisa de --rom-root"}], images
    if not map_csv.exists():
        return {}, [{"row": "0", "error": f"mapa CSV nao encontrado: {map_csv}"}], images

    image_lookup = build_lookup(images, input_dir)
    rom_lookup = build_lookup(roms, rom_root)
    mapped: dict[Path, list[Path]] = defaultdict(list)
    errors: list[dict[str, str]] = []
    text = map_csv.read_text(encoding="utf-8-sig")
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    for idx, row in enumerate(reader, start=2):
        lower = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        cover_value = lower.get("cover") or lower.get("image") or lower.get("capa")
        rom_value = lower.get("rom") or lower.get("game") or lower.get("jogo")
        if not cover_value and not rom_value:
            continue
        if not cover_value or not rom_value:
            errors.append({"row": str(idx), "error": "linha precisa de cover e rom"})
            continue

        cover = resolve_from_lookup(cover_value, input_dir, image_lookup)
        rom = resolve_from_lookup(rom_value, rom_root, rom_lookup)
        if cover is None:
            errors.append({"row": str(idx), "error": f"capa nao encontrada: {cover_value}"})
            continue
        if rom is None:
            errors.append({"row": str(idx), "error": f"rom nao encontrada: {rom_value}"})
            continue
        mapped[cover].append(rom)
        if cover.suffix.lower() in IMAGE_EXTS and cover not in images:
            images.append(cover)
            for key in lookup_keys(cover, input_dir):
                image_lookup[key].append(cover)

    images = sorted({p.resolve(): p for p in images}.values(), key=lambda p: p.name.upper())
    return mapped, errors, images


def choose_rom_matches(
    image_stem: str,
    roms_by_stem_exact: dict[str, list[Path]],
    roms_by_exact: dict[str, list[Path]],
    roms_by_title: dict[str, list[Path]],
    match_title_variants: bool = False,
    exact_name_only: bool = False,
) -> list[Path]:
    if exact_name_only:
        return roms_by_stem_exact.get(image_stem.upper(), [])

    exact = roms_by_exact.get(normalize_key(image_stem), [])
    if exact:
        return exact
    title_matches = roms_by_title.get(title_key(image_stem), [])
    if match_title_variants and title_matches:
        return sorted({p.resolve(): p for p in title_matches}.values(), key=lambda p: p.name.upper())
    if len(title_matches) == 1:
        return title_matches
    # Prefer the plain USA variant when multiple ROMs share the same bare title.
    usa_plain = [p for p in title_matches if p.stem.upper().endswith("(USA)")]
    return usa_plain[:1]


def validate_scimg(path: Path) -> dict[str, int]:
    meta, _pal, tiles, _tilemap = read_scimg(path)
    zero_pixels = 0
    for byte in tiles:
        if (byte >> 4) == 0:
            zero_pixels += 1
        if (byte & 0x0F) == 0:
            zero_pixels += 1
    return {
        "width_tiles": int(meta["width_tiles"]),
        "height_tiles": int(meta["height_tiles"]),
        "flags": int(meta["flags"]),
        "tile_data_offset": int(meta["tile_data_offset"]),
        "size_bytes": int(meta["size_bytes"]),
        "zero_pixels": zero_pixels,
    }


def convert_one(
    src: Path,
    dst: Path,
    tmp_dir: Path,
    crop_box: tuple[float, float, float, float] | None = None,
) -> dict[str, object]:
    tmp = tmp_dir / f"{src.stem}.linear.scimg"
    qimg = quantize_image(Image.open(src), VISIBLE_WIDTH_TILES, HEIGHT_TILES, crop_box)
    px = qimg.load()
    pal = palette_words(qimg)
    tiles = bytearray()
    blank_tile = bytes(32)
    for ty in range(HEIGHT_TILES):
        for tx in range(VISIBLE_WIDTH_TILES):
            indices = [px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)]
            tiles.extend(encode_tile(indices))
        for _pad in range(STORAGE_WIDTH_TILES - VISIBLE_WIDTH_TILES):
            tiles.extend(blank_tile)
    write_linear_scimg(tmp, STORAGE_WIDTH_TILES, HEIGHT_TILES, 0x0200, pal, bytes(tiles), True)
    make_opaque_scimg(tmp, dst, 15)
    meta = validate_scimg(dst)
    tmp.unlink(missing_ok=True)
    return {
        "source": str(src),
        "output": str(dst),
        **meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk convert Genesis cover art to EverDrive-MD SCIMG/PAK files.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--rom-root", type=Path, default=None)
    parser.add_argument("--pak-out", type=Path, default=None)
    parser.add_argument("--map-csv", type=Path, default=None)
    parser.add_argument("--crop-json", type=Path, default=None)
    parser.add_argument("--preview-count", type=int, default=12)
    parser.add_argument(
        "--exact-name-only",
        action="store_true",
        help="only match covers to ROMs when their filename stems are identical, ignoring case",
    )
    parser.add_argument(
        "--match-title-variants",
        action="store_true",
        help="map one cover to all ROM variants with the same title key",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    crop_map = load_crop_map(args.crop_json)
    all_dir = output_dir / "scimg_all"
    matched_dir = output_dir / "scimg_matched"
    preview_dir = output_dir / "previews"
    tmp_dir = output_dir / "_tmp"
    for path in (all_dir, matched_dir, preview_dir, tmp_dir):
        path.mkdir(parents=True, exist_ok=True)

    images = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS], key=lambda p: p.name.upper())
    roms: list[Path] = iter_roms(args.rom_root) if args.rom_root else []
    manual_map, manual_map_errors, images = read_manual_map(args.map_csv, input_dir, images, args.rom_root, roms)
    roms_by_stem_exact: dict[str, list[Path]] = defaultdict(list)
    roms_by_exact: dict[str, list[Path]] = defaultdict(list)
    roms_by_title: dict[str, list[Path]] = defaultdict(list)
    for rom in roms:
        roms_by_stem_exact[rom.stem.upper()].append(rom)
        roms_by_exact[normalize_key(rom.stem)].append(rom)
        roms_by_title[title_key(rom.stem)].append(rom)

    converted: list[dict[str, object]] = []
    matched: list[dict[str, object]] = []
    unmatched_images: list[str] = []
    matched_roms: set[Path] = set()
    failures: list[dict[str, str]] = []
    matched_dirs: dict[str, Path] = {}
    crop_used_count = 0

    print(f"__PROGRESS__convert|0|{len(images)}", flush=True)
    for idx, image in enumerate(images, start=1):
        try:
            all_scimg = all_dir / f"{image.stem}.SCIMG"
            crop_box = crop_for_image(image, input_dir, crop_map)
            if crop_box is not None:
                crop_used_count += 1
            converted.append(convert_one(image, all_scimg, tmp_dir, crop_box))
            if idx <= args.preview_count:
                preview_scimg(all_scimg, preview_dir / f"{image.stem}.png")

            manual_matches = manual_map.get(image.resolve())
            matches = manual_matches if manual_matches is not None else (
                choose_rom_matches(
                    image.stem,
                    roms_by_stem_exact,
                    roms_by_exact,
                    roms_by_title,
                    args.match_title_variants,
                    args.exact_name_only,
                )
                if roms
                else []
            )
            if not matches:
                unmatched_images.append(image.name)
            else:
                for rom in matches:
                    matched_roms.add(rom.resolve())
                    letter = pack_letter_for_name(rom.stem)
                    letter_dir = matched_dir / letter
                    letter_dir.mkdir(parents=True, exist_ok=True)
                    matched_scimg = letter_dir / f"{rom.stem}.SCIMG"
                    shutil.copyfile(all_scimg, matched_scimg)
                    matched_dirs[letter] = letter_dir
                    matched.append(
                        {
                            "image": image.name,
                            "rom": rom.name,
                            "letter": letter,
                            "scimg": str(matched_scimg),
                        }
                    )
        except Exception as exc:  # noqa: BLE001 - batch report should continue.
            failures.append({"image": image.name, "error": str(exc)})

        if idx == 1 or idx == len(images) or idx % 5 == 0:
            print(f"__PROGRESS__convert|{idx}|{len(images)}", flush=True)
        if idx % 50 == 0:
            print(f"converted {idx}/{len(images)}", flush=True)

    packs: list[dict[str, object]] = []
    if args.pak_out:
        args.pak_out.mkdir(parents=True, exist_ok=True)
        pack_items = sorted(matched_dirs.items())
        print(f"__PROGRESS__pack|0|{len(pack_items)}", flush=True)
        for pack_idx, (letter, letter_dir) in enumerate(pack_items, start=1):
            pack_path = args.pak_out / f"{letter}.PAK"
            packs.append(build_paged_pack(letter_dir, pack_path, index_sectors_override=INDEX_SECTORS))
            print(f"__PROGRESS__pack|{pack_idx}|{len(pack_items)}", flush=True)

    unmatched_roms = [str(path.relative_to(args.rom_root) if args.rom_root else path) for path in roms if path.resolve() not in matched_roms]
    report = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "match_mode": "exact_name" if args.exact_name_only else "relative_name",
        "crop_json": str(args.crop_json) if args.crop_json else None,
        "crop_map_count": len(crop_map),
        "crop_used_count": crop_used_count,
        "image_count": len(images),
        "rom_count": len(roms),
        "converted_count": len(converted),
        "matched_count": len(matched),
        "unmatched_image_count": len(unmatched_images),
        "unmatched_rom_count": len(unmatched_roms),
        "manual_map_error_count": len(manual_map_errors),
        "failure_count": len(failures),
        "packs": [{"letter": Path(p["output"]).stem, "count": p["count"], "output": p["output"], "size_bytes": p["size_bytes"]} for p in packs],
        "unmatched_images": unmatched_images,
        "unmatched_roms": unmatched_roms,
        "manual_map_errors": manual_map_errors,
        "failures": failures,
        "matched": matched,
    }
    (output_dir / "conversion-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    (output_dir / "unmatched-images.txt").write_text("\n".join(unmatched_images) + ("\n" if unmatched_images else ""), encoding="utf-8")
    (output_dir / "unmatched-roms.txt").write_text("\n".join(unmatched_roms) + ("\n" if unmatched_roms else ""), encoding="utf-8")
    template_rows = ["cover,rom"]
    for rom in unmatched_roms[:500]:
        template_rows.append(f",{rom}")
    (output_dir / "cover-map-template.csv").write_text("\n".join(template_rows) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("image_count", "rom_count", "converted_count", "matched_count", "unmatched_image_count", "unmatched_rom_count", "manual_map_error_count", "failure_count")}, indent=2), flush=True)
    if packs:
        print("packs:", flush=True)
        for pack in report["packs"]:
            print(f"  {pack['letter']}: {pack['count']} covers -> {pack['output']}", flush=True)
    if manual_map_errors:
        print("manual map warnings:", flush=True)
        for error in manual_map_errors[:20]:
            print(f"  row {error['row']}: {error['error']}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
