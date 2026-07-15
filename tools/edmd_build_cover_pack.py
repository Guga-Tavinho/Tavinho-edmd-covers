from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path

from scimg_tool import read_scimg


MAGIC = b"SCPK"
VERSION = 1
SECTOR_SIZE = 512
ENTRY_SIZE = 48
NAME_SIZE = 32
HEADER_STRUCT = struct.Struct(">4sBBHIII")
ENTRY_STRUCT = struct.Struct(f">{NAME_SIZE}sIIII")


def align(value: int, amount: int = SECTOR_SIZE) -> int:
    return (value + amount - 1) // amount * amount


def cover_key(path: Path) -> bytes:
    key = path.stem.upper().encode("ascii", "ignore")[: NAME_SIZE - 1]
    return key + bytes(NAME_SIZE - len(key))


def is_firmware_ready_scimg(path: Path, width_tiles: int = 16, height_tiles: int = 14) -> tuple[bool, str]:
    try:
        meta, _pal, _tiles, _tilemap = read_scimg(path)
    except Exception as exc:  # noqa: BLE001 - CLI should report all bad files.
        return False, f"invalid SCIMG: {exc}"
    if meta["width_tiles"] != width_tiles or meta["height_tiles"] != height_tiles:
        return False, f"not {width_tiles}x{height_tiles} tiles"
    if meta["flags"] != 3:
        return False, "not linear sector-aligned opaque format (flags=3)"
    if meta["tile_data_offset"] != 0x200:
        return False, "tile data is not sector aligned at 0x200"
    expected_size = 0x200 + width_tiles * height_tiles * 32
    if meta["size_bytes"] != expected_size:
        return False, f"unexpected size; expected {expected_size} bytes"
    return True, "ok"


def build_pack(
    input_dir: Path,
    output_path: Path,
    include_all: bool = False,
    width_tiles: int = 16,
    height_tiles: int = 14,
) -> dict[str, object]:
    covers_by_path = {path.resolve().as_posix().lower(): path for path in input_dir.glob("*.SCIMG")}
    covers_by_path.update({path.resolve().as_posix().lower(): path for path in input_dir.glob("*.scimg")})
    covers = sorted(covers_by_path.values(), key=lambda p: p.name.upper())
    accepted: list[tuple[Path, bytes, bytes, int]] = []
    skipped: list[dict[str, str]] = []
    seen: set[bytes] = set()

    for path in covers:
        if path.stem.upper().endswith("-AUTO-LINEAR"):
            skipped.append({"name": path.name, "reason": "intermediate auto-linear file"})
            continue
        key = cover_key(path)
        if key in seen:
            skipped.append({"name": path.name, "reason": "duplicate normalized name"})
            continue
        ok, reason = is_firmware_ready_scimg(path, width_tiles, height_tiles)
        if not ok and not include_all:
            skipped.append({"name": path.name, "reason": reason})
            continue
        data = path.read_bytes()
        accepted.append((path, key, data, zlib.crc32(data) & 0xFFFFFFFF))
        seen.add(key)

    index_size = align(HEADER_STRUCT.size + len(accepted) * ENTRY_SIZE)
    offset = index_size
    entries = []
    payload = bytearray(index_size)

    HEADER_STRUCT.pack_into(payload, 0, MAGIC, VERSION, 0, len(accepted), ENTRY_SIZE, index_size, SECTOR_SIZE)
    for idx, (path, key, data, crc) in enumerate(accepted):
        offset = align(offset)
        ENTRY_STRUCT.pack_into(payload, HEADER_STRUCT.size + idx * ENTRY_SIZE, key, offset, len(data), crc, 0)
        if len(payload) < offset:
            payload.extend(bytes(offset - len(payload)))
        payload.extend(data)
        pad = align(len(payload)) - len(payload)
        if pad:
            payload.extend(bytes(pad))
        entries.append(
            {
                "name": path.name,
                "key": key.rstrip(b"\0").decode("ascii"),
                "offset": offset,
                "size": len(data),
                "crc32": f"{crc:08x}",
            }
        )
        offset = len(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return {
        "input_dir": str(input_dir),
        "output": str(output_path),
        "count": len(entries),
        "index_size": index_size,
        "sector_size": SECTOR_SIZE,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "size_bytes": len(payload),
        "entries": entries,
        "skipped": skipped,
    }


def inspect_pack(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    magic, version, _reserved, count, entry_size, index_size, sector_size = HEADER_STRUCT.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError("not an SCPK cover pack")
    entries = []
    for idx in range(count):
        raw_name, offset, size, crc, _reserved2 = ENTRY_STRUCT.unpack_from(data, HEADER_STRUCT.size + idx * entry_size)
        name = raw_name.split(b"\0", 1)[0].decode("ascii")
        entries.append({"key": name, "offset": offset, "size": size, "crc32": f"{crc:08x}"})
    return {
        "path": str(path),
        "version": version,
        "count": count,
        "entry_size": entry_size,
        "index_size": index_size,
        "sector_size": sector_size,
        "size_bytes": len(data),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or inspect an EverDrive-MD SCIMG cover pack.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("input_dir", type=Path)
    p_build.add_argument("output", type=Path)
    p_build.add_argument("--include-all", action="store_true")
    p_build.add_argument("--width-tiles", type=int, default=16)
    p_build.add_argument("--height-tiles", type=int, default=14)

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("pack", type=Path)

    args = parser.parse_args()
    if args.cmd == "build":
        result = build_pack(args.input_dir, args.output, args.include_all, args.width_tiles, args.height_tiles)
    else:
        result = inspect_pack(args.pack)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
