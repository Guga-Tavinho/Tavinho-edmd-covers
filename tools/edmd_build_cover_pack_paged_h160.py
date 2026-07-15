from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path

from edmd_build_cover_pack import ENTRY_SIZE, ENTRY_STRUCT, NAME_SIZE, SECTOR_SIZE, align, cover_key, is_firmware_ready_scimg


MAGIC = b"SCP2"
VERSION = 1
HEADER_STRUCT = struct.Struct(">4sBBHIII")
FIRST_SECTOR_ENTRIES = 10
NEXT_SECTOR_ENTRIES = SECTOR_SIZE // ENTRY_SIZE


def build_paged_pack(
    input_dir: Path,
    output_path: Path,
    width_tiles: int = 16,
    height_tiles: int = 20,
    index_sectors_override: int | None = None,
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
        if not ok:
            skipped.append({"name": path.name, "reason": reason})
            continue
        data = path.read_bytes()
        accepted.append((path, key, data, zlib.crc32(data) & 0xFFFFFFFF))
        seen.add(key)

    remaining = max(0, len(accepted) - FIRST_SECTOR_ENTRIES)
    extra_sectors = (remaining + NEXT_SECTOR_ENTRIES - 1) // NEXT_SECTOR_ENTRIES
    index_sectors = 1 + extra_sectors
    if index_sectors_override is not None:
        if index_sectors_override < index_sectors:
            raise ValueError(
                f"{len(accepted)} covers need at least {index_sectors} index sectors; "
                f"requested {index_sectors_override}"
            )
        index_sectors = index_sectors_override
    index_size = index_sectors * SECTOR_SIZE
    payload = bytearray(index_size)

    HEADER_STRUCT.pack_into(payload, 0, MAGIC, VERSION, 0, len(accepted), ENTRY_SIZE, index_size, SECTOR_SIZE)
    offset = index_size
    entries = []
    for idx, (path, key, data, crc) in enumerate(accepted):
        if idx < FIRST_SECTOR_ENTRIES:
            entry_pos = HEADER_STRUCT.size + idx * ENTRY_SIZE
        else:
            rel = idx - FIRST_SECTOR_ENTRIES
            sector = 1 + rel // NEXT_SECTOR_ENTRIES
            slot = rel % NEXT_SECTOR_ENTRIES
            entry_pos = sector * SECTOR_SIZE + slot * ENTRY_SIZE

        offset = align(offset)
        ENTRY_STRUCT.pack_into(payload, entry_pos, key, offset, len(data), crc, 0)
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
                "catalog_sector": 0 if idx < FIRST_SECTOR_ENTRIES else 1 + (idx - FIRST_SECTOR_ENTRIES) // NEXT_SECTOR_ENTRIES,
            }
        )
        offset = len(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return {
        "input_dir": str(input_dir),
        "output": str(output_path),
        "count": len(entries),
        "index_sectors": index_sectors,
        "index_size": index_size,
        "sector_size": SECTOR_SIZE,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "size_bytes": len(payload),
        "entries": entries,
        "skipped": skipped,
    }


def inspect_paged_pack(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    magic, version, _reserved, count, entry_size, index_size, sector_size = HEADER_STRUCT.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError("not an SCP2 cover pack")
    entries = []
    for idx in range(count):
        if idx < FIRST_SECTOR_ENTRIES:
            entry_pos = HEADER_STRUCT.size + idx * ENTRY_SIZE
        else:
            rel = idx - FIRST_SECTOR_ENTRIES
            sector = 1 + rel // NEXT_SECTOR_ENTRIES
            slot = rel % NEXT_SECTOR_ENTRIES
            entry_pos = sector * SECTOR_SIZE + slot * ENTRY_SIZE
        raw_name, offset, size, crc, _reserved2 = ENTRY_STRUCT.unpack_from(data, entry_pos)
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
    parser = argparse.ArgumentParser(description="Build or inspect a paged SCP2 cover pack.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_build = sub.add_parser("build")
    p_build.add_argument("input_dir", type=Path)
    p_build.add_argument("output", type=Path)
    p_build.add_argument(
        "--index-sectors",
        type=int,
        default=None,
        help="force/pad the catalog to this many sectors; 15 sectors = 150 entries for POC107",
    )
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("pack", type=Path)
    args = parser.parse_args()
    result = (
        build_paged_pack(args.input_dir, args.output, index_sectors_override=args.index_sectors)
        if args.cmd == "build"
        else inspect_paged_pack(args.pack)
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
