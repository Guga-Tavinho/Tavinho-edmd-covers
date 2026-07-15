from __future__ import annotations

import hashlib
from pathlib import Path

from capstone import CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, Cs


BASE_ADDR = 0xFF0000
PATCH_OFFSETS: dict[int, bytes] = {}
AFTER_REPAINT_PATCH = (0x65E2, bytes.fromhex("303900FFE30C"))
BACK_AFTER_CLEAR_PATCH = (0x67AE, bytes.fromhex("33FCFFFF00FFE302"))
PAGE_TOP_PATCHES = {
    0x6934: (bytes.fromhex("D640"), bytes.fromhex("3600")),  # next page: move page start into d3
    0x69A8: (bytes.fromhex("D640"), bytes.fromhex("3600")),  # previous page: move page start into d3
}
CODE_OFFSET = 0x9C00
RETURN_REPAINT = BASE_ADDR + 0x64B4
PREVIEW_X = 24
PREVIEW_Y = 2
HEIGHT_ROWS = 20
VISIBLE_WIDTH_TILES = 16
STORAGE_WIDTH_TILES = 16
COVER_FLAG_ADDR = 0x00FFE31A
COVER_FLAG_MAGIC = 0x434F5652
FAT_STATE_BYTES = 0x100
FAT_STATE_LONGS = FAT_STATE_BYTES // 4
BROWSER_TAG_X = 2
BROWSER_TAG_ROW = 1
BROWSER_TAG_TILE_BASE = 0x360
BROWSER_TAG_ATTR = 0x8000
BROWSER_TAG_TEXT = "Siga no instagram: @tavinho.games"


class Code:
    def __init__(self, origin: int) -> None:
        self.origin = origin
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []
        self.fixups_b: list[tuple[int, str]] = []
        self.fixups_l: list[tuple[int, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = self.origin + len(self.data)

    def emit(self, hex_text: str) -> None:
        self.data.extend(bytes.fromhex(hex_text))

    def word(self, value: int) -> None:
        self.data.extend((value & 0xFFFF).to_bytes(2, "big"))

    def long(self, value: int) -> None:
        self.data.extend((value & 0xFFFFFFFF).to_bytes(4, "big"))

    def long_label(self, label: str) -> None:
        self.fixups_l.append((len(self.data), label))
        self.long(0)

    def dbra(self, reg: int, label: str) -> None:
        self.word(0x51C8 | reg)
        self.fixups.append((len(self.data), label))
        self.word(0)

    def branch_word(self, opcode: int, label: str) -> None:
        self.word(opcode)
        self.fixups.append((len(self.data), label))
        self.word(0)

    def branch_byte(self, opcode: int, label: str) -> None:
        self.data.append(opcode & 0xFF)
        self.fixups_b.append((len(self.data), label))
        self.data.append(0)

    def resolve(self) -> bytes:
        for pos, label in self.fixups:
            target = self.labels[label]
            extension_addr = self.origin + pos
            disp = target - extension_addr
            if not -0x8000 <= disp <= 0x7FFF:
                raise ValueError(f"branch to {label} out of range")
            self.data[pos : pos + 2] = (disp & 0xFFFF).to_bytes(2, "big")
        for pos, label in self.fixups_b:
            target = self.labels[label]
            extension_addr = self.origin + pos + 1
            disp = target - extension_addr
            if not -0x80 <= disp <= 0x7F or disp == 0:
                raise ValueError(f"short branch to {label} out of range")
            self.data[pos] = disp & 0xFF
        for pos, label in self.fixups_l:
            target = self.labels[label]
            self.data[pos : pos + 4] = (target & 0xFFFFFFFF).to_bytes(4, "big")
        return bytes(self.data)


def vdp_vram_write_cmd(addr: int) -> int:
    return ((0x4000 + (addr & 0x3FFF)) << 16) | ((addr >> 14) & 0x03)


def plane_a_addr(x: int, y: int) -> int:
    return 0xC000 + ((y * 64 + x) * 2)


def plane_b_addr(x: int, y: int) -> int:
    return 0xE000 + ((y * 64 + x) * 2)


def emit_selected_name_ptr(c: Code) -> None:
    # a0 = visible selected name pointer: 0xFFCCC0 + (d3 % 21) * 0x110.
    # MULU only uses the low word, so the quotient left in the high word after
    # SWAP does not need to be cleared.
    c.emit("7000")  # d0 = 0
    c.emit("3003")  # d0.w = d3.w
    c.emit("7415")
    c.emit("80C2")
    c.emit("4840")
    c.emit("C0FC0110")
    c.emit("068000FFCCC0")
    c.emit("2040")


def emit_clear_rect_loop(c: Code, name: str, addr_fn, attr: int) -> None:
    c.emit("43F900C00000")  # a1 = VDP data
    c.emit("45F900C00004")  # a2 = VDP control
    c.emit("2E3C")
    c.long(vdp_vram_write_cmd(addr_fn(PREVIEW_X, PREVIEW_Y)))  # d7 = row VRAM write command
    c.emit("263C00800000")  # d3 = command delta for next 64-cell plane row
    c.word(0x343C)  # move.w #rows-1,d2
    c.word(HEIGHT_ROWS - 1)
    c.word(0x323C)  # move.w #attr,d1
    c.word(attr)

    c.label(f"{name}_row_loop")
    c.emit("2487")  # move.l d7,(a2)
    c.emit("700F")  # 16 cells
    c.label(f"{name}_col_loop")
    c.emit("3281")  # move.w d1,(a1)
    c.dbra(0, f"{name}_col_loop")
    c.emit("DE83")  # add.l d3,d7
    c.dbra(2, f"{name}_row_loop")


READABLE_FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00000", "00100"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "@": ("01110", "10001", "10111", "10101", "10111", "10000", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
}


def readable_tag_assets(text: str) -> tuple[bytes, list[int]]:
    chars: list[str] = []
    for ch in text.upper():
        if ch not in chars:
            chars.append(ch)

    char_index = {ch: i for i, ch in enumerate(chars)}
    tiles = bytearray()
    for ch in chars:
        pixels = [[0] * 8 for _ in range(8)]
        glyph = READABLE_FONT_5X7.get(ch, READABLE_FONT_5X7[" "])
        for y, row in enumerate(glyph):
            for x, bit in enumerate(row, start=1):
                if bit == "1":
                    pixels[y][x] = 0xF
        for row in pixels:
            for x in range(0, 8, 2):
                tiles.append((row[x] << 4) | row[x + 1])

    map_words = [
        BROWSER_TAG_ATTR | BROWSER_TAG_TILE_BASE | char_index.get(ch, char_index[" "])
        for ch in text.upper()
    ]
    return bytes(tiles), map_words


def emit_browser_tag_small(c: Code) -> None:
    tiles, map_words = readable_tag_assets(BROWSER_TAG_TEXT)

    c.emit("43F900C00000")  # a1 = VDP data
    c.emit("45F900C00004")  # a2 = VDP control

    c.emit("41F9")          # a0 = small packed text tile data
    c.long_label("browser_tag_tiles")
    c.emit("24BC")
    c.long(vdp_vram_write_cmd(BROWSER_TAG_TILE_BASE * 32))
    c.word(0x303C)          # move.w #word_count-1,d0
    c.word((len(tiles) // 2) - 1)
    c.label("browser_tag_tile_loop")
    c.emit("3298")          # move.w (a0)+,(a1)
    c.dbra(0, "browser_tag_tile_loop")

    c.emit("41F9")          # a0 = plane map words for the tag
    c.long_label("browser_tag_map")
    c.emit("24BC")
    c.long(vdp_vram_write_cmd(plane_a_addr(BROWSER_TAG_X, BROWSER_TAG_ROW)))
    c.word(0x303C)          # move.w #tile_count-1,d0
    c.word(len(map_words) - 1)
    c.label("browser_tag_map_loop")
    c.emit("3298")          # move.w (a0)+,(a1)
    c.dbra(0, "browser_tag_map_loop")


def build_code() -> tuple[bytes, dict[str, int]]:
    c = Code(BASE_ADDR + CODE_OFFSET)

    # Called after the original list repaint. It returns to the browser input
    # wait with the original joypad read restored in d0/CCR.
    c.emit("48E7FFFE")

    emit_browser_tag_small(c)

    c.emit("4FEF")
    c.word((-FAT_STATE_BYTES) & 0xFFFF)
    c.emit("41F900FFCC64")
    c.emit("224F")
    c.word(0x303C)
    c.word(FAT_STATE_LONGS - 1)
    c.label("save_loop")
    c.emit("22D8")
    c.dbra(0, "save_loop")

    # Path-open for /EDMD/COVERS.PAK mutates the current directory-list
    # buffer pointed by FFCC7C. Save its small header so B/back still knows
    # which ROM folder the browser is in.
    c.emit("4FEFFFC0")
    c.emit("267900FFCC7C")
    c.emit("224F")
    c.emit("700F")
    c.label("save_dir_header_loop")
    c.emit("22DB")
    c.dbra(0, "save_dir_header_loop")

    # Do not touch the cover area unless the selected browser item looks like
    # a ROM. This prevents an empty black cover box on folders/non-ROM files.
    emit_selected_name_ptr(c)
    c.emit("723F")
    c.label("ext_scan_loop")
    c.emit("1018")
    c.emit("4A00")
    c.branch_word(0x6700, "maybe_clear_no_alloc")
    c.emit("0C00002E")
    c.branch_word(0x6600, "ext_scan_next")
    c.emit("1010")
    c.emit("0C000042")
    c.branch_word(0x6700, "ext_b_ok")
    c.emit("0C000062")
    c.branch_word(0x6600, "ext_scan_next")
    c.label("ext_b_ok")
    c.emit("10280001")
    c.emit("0C000049")
    c.branch_word(0x6700, "ext_i_ok")
    c.emit("0C000069")
    c.branch_word(0x6600, "ext_scan_next")
    c.label("ext_i_ok")
    c.emit("10280002")
    c.emit("0C00004E")
    c.branch_word(0x6700, "ext_ok")
    c.emit("0C00006E")
    c.branch_word(0x6700, "ext_ok")
    c.label("ext_scan_next")
    c.dbra(1, "ext_scan_loop")
    c.branch_word(0x6000, "maybe_clear_no_alloc")

    c.label("ext_ok")

    # Build a short absolute root pack path: /0.PAK for numeric names and
    # /A.PAK../Z.PAK for alphabetic names. Keep this compact; the clone has a
    # boot-sensitive edge near 0xA800.
    c.emit("4FEFFFC0")
    c.emit("2C0F")  # d6 = path buffer pointer
    c.emit("4BEF0000")  # a5 = path write pointer
    emit_selected_name_ptr(c)
    c.emit("1010")  # first filename char
    c.emit("0C000030")
    c.branch_word(0x6500, "check_lower_pack")
    c.emit("0C000039")
    c.branch_word(0x6300, "use_digit_pack")

    c.label("check_lower_pack")
    c.emit("0C000061")
    c.branch_word(0x6500, "check_upper_pack")
    c.emit("0C00007A")
    c.branch_word(0x6200, "check_upper_pack")
    c.emit("04000020")  # lowercase -> uppercase

    c.label("check_upper_pack")
    c.emit("0C000041")
    c.branch_word(0x6500, "free_path_maybe_clear_no_alloc")
    c.emit("0C00005A")
    c.branch_word(0x6200, "free_path_maybe_clear_no_alloc")
    c.branch_word(0x6000, "write_root_pack_path")

    c.label("use_digit_pack")
    c.emit("7030")  # "0"
    c.branch_word(0x6000, "write_root_pack_path")

    c.label("write_root_pack_path")
    c.emit("1AFC002F")      # /
    c.emit("1AC0")          # selected pack letter
    c.emit("2AFC2E50414B")  # .PAK
    c.emit("4215")          # NUL

    c.emit("42A7")
    c.emit("2F06")
    c.emit("4EB900FF3854")
    c.emit("4FEF0008")
    c.emit("4A00")
    c.branch_word(0x6600, "free_path_restore")
    c.emit("4FEF0040")

    c.emit("4FEFFE00")
    c.emit("284F")
    c.emit("48780001")
    c.emit("2F0C")
    c.emit("4EB900FF2C1C")
    c.emit("4FEF0008")
    c.emit("4A00")
    c.branch_word(0x6600, "clear_readbuf")
    c.emit("0C9453435032")  # SCP2
    c.branch_word(0x6600, "clear_readbuf")

    emit_selected_name_ptr(c)

    # Search the first catalog sector, then fourteen more sectors. d5 tracks how
    # many catalog sectors have already been read, so the later seek skips the
    # correct distance from the current file pointer to the cover payload.
    c.emit("7A01")  # d5 = sectors read, first catalog sector already in a4
    c.emit("780E")  # d4 = fourteen extra catalog sectors after the first
    c.emit("45EC0014")  # first sector entries start after the 20-byte header
    c.branch_word(0x6000, "pack_scan_sector")

    c.label("pack_read_next_catalog_sector")
    c.emit("2F04")  # preserve search state; the SD read helper may clobber it
    c.emit("2F05")
    c.emit("2F08")
    c.emit("48780001")
    c.emit("2F0C")
    c.emit("4EB900FF2C1C")
    c.emit("4FEF0008")
    c.emit("205F")
    c.emit("2A1F")
    c.emit("281F")
    c.emit("4A00")
    c.branch_word(0x6600, "clear_readbuf")
    c.emit("5245")  # d5++
    c.emit("45EC0000")  # next sectors start entries at buffer+0

    c.label("pack_scan_sector")
    c.emit("7E09")  # ten entries per catalog sector, DBRA count = 9

    c.label("pack_entry_loop")
    c.emit("264A")  # a3 = entry name pointer
    c.emit("2248")  # a1 = selected visible name pointer

    c.label("pack_name_loop")
    c.emit("101B")  # d0 = (a3)+, uppercase catalog char
    c.branch_word(0x6700, "pack_name_end")
    c.emit("1219")  # d1 = (a1)+, selected char
    c.emit("0C010061")
    c.branch_word(0x6500, "pack_no_lower")
    c.emit("0C01007A")
    c.branch_word(0x6200, "pack_no_lower")
    c.emit("04010020")  # uppercase selected char
    c.label("pack_no_lower")
    c.emit("B200")
    c.branch_word(0x6600, "pack_next_entry")
    c.branch_word(0x6000, "pack_name_loop")

    c.label("pack_name_end")
    # If the catalog key used all 31 name bytes, accept it as a prefix. This
    # lets long ROM names match the truncated pack key while the pack builder
    # still rejects duplicate 31-byte prefixes.
    c.emit("200B")  # d0 = a3
    c.emit("908A")  # d0 -= a2
    c.emit("0C400020")  # key bytes + NUL == 32
    c.branch_word(0x6700, "pack_found")
    c.emit("0C11002E")  # selected char must now be dot or NUL
    c.branch_word(0x6700, "pack_found")
    c.emit("4A11")
    c.branch_word(0x6700, "pack_found")

    c.label("pack_next_entry")
    c.emit("45EA0030")  # a2 += 48
    c.dbra(7, "pack_entry_loop")
    c.dbra(4, "pack_read_next_catalog_sector")
    c.branch_word(0x6000, "clear_readbuf")

    c.label("pack_found")
    c.emit("2E2A0020")  # d7 = entry offset
    c.emit("E08F")  # d7 >>= 8
    c.emit("E28F")  # d7 >>= 1 ; sector index
    c.emit("9E45")  # skip sectors from current file pointer to cover sector

    c.label("pack_skip_check")
    c.emit("4A47")
    c.branch_word(0x6700, "pack_read_cover_header")
    c.emit("2F07")
    c.emit("4EB900FF2AE0")
    c.emit("588F")
    c.emit("4A00")
    c.branch_word(0x6600, "clear_readbuf")

    c.label("pack_read_cover_header")
    c.emit("48780001")
    c.emit("2F0C")
    c.emit("4EB900FF2C1C")
    c.emit("4FEF0008")
    c.emit("4A00")
    c.branch_word(0x6600, "clear_readbuf")
    c.emit("0C945343494D")
    c.branch_word(0x6600, "clear_readbuf")

    # Load palette 3 from sector 0. In aligned linear SCIMG files, each next
    # sector contains exactly one 16-tile row.
    c.emit("43F900C00000")
    c.emit("45F900C00004")
    c.emit("24BCC0600000")
    c.emit("41EC0020")
    c.emit("720F")
    c.label("pal_loop")
    c.emit("3298")
    c.dbra(1, "pal_loop")

    # Tile 0x200: solid palette index 15. Used to wipe both planes under the
    # cover area before mapping the cover tiles.
    c.emit("24BC")
    c.long(vdp_vram_write_cmd(0x200 * 32))
    c.emit("303CFFFF")
    c.emit("7207")
    c.label("blank_tile_loop")
    c.emit("3280")
    c.emit("3280")
    c.dbra(1, "blank_tile_loop")

    emit_clear_rect_loop(c, "clear_initial_a", plane_a_addr, 0x0000)
    emit_clear_rect_loop(c, "clear_initial_b", plane_b_addr, 0xE200)

    for row in range(HEIGHT_ROWS):
        c.emit("48780001")
        c.emit("2F0C")
        c.emit("4EB900FF2C1C")
        c.emit("4FEF0008")
        c.emit("4A00")
        c.branch_word(0x6600, "clear_readbuf")

        tile_base = 0x201 + row * STORAGE_WIDTH_TILES
        c.emit("43F900C00000")
        c.emit("45F900C00004")
        c.emit("24BC")
        c.long(vdp_vram_write_cmd(tile_base * 32))
        c.emit("204C")
        c.word(0x7000 | (VISIBLE_WIDTH_TILES * 8 - 1))
        c.label(f"tile_loop_{row}")
        c.emit("2298")
        c.dbra(0, f"tile_loop_{row}")

        c.emit("24BC")
        c.long(vdp_vram_write_cmd(plane_b_addr(PREVIEW_X, PREVIEW_Y + row)))
        c.word(0x323C)
        c.word(0xE000 | tile_base)
        c.word(0x7000 | (VISIBLE_WIDTH_TILES - 1))
        c.label(f"map_loop_{row}")
        c.emit("3281")
        c.emit("5241")
        c.dbra(0, f"map_loop_{row}")

    c.emit("23FC434F565200FFE31A")
    c.branch_word(0x6000, "free_readbuf")

    c.label("maybe_clear_no_alloc")
    c.emit("203900FFE31A")
    c.emit("0C80434F5652")
    c.branch_word(0x6600, "restore_wait")
    c.emit("4246")
    c.branch_word(0x6000, "clear_common")

    c.label("clear_readbuf")
    c.emit("203900FFE31A")
    c.emit("0C80434F5652")
    c.branch_word(0x6600, "free_readbuf")
    c.emit("3C3C0200")

    c.label("clear_common")
    emit_clear_rect_loop(c, "clear_missing_a", plane_a_addr, 0x0000)
    emit_clear_rect_loop(c, "clear_missing_b", plane_b_addr, 0x0000)
    c.emit("42B900FFE31A")
    c.emit("4A46")
    c.branch_word(0x6700, "restore_wait")

    c.label("free_readbuf")
    c.emit("4FEF0200")
    c.branch_word(0x6000, "restore_wait")

    c.label("free_path_restore")
    c.emit("4FEF0040")
    c.branch_word(0x6000, "restore_wait")

    c.label("free_path_maybe_clear_no_alloc")
    c.emit("4FEF0040")
    c.branch_word(0x6000, "maybe_clear_no_alloc")

    c.label("restore_wait")
    c.emit("206F0058")
    c.emit("224F")
    c.emit("700F")
    c.label("restore_dir_header_loop")
    c.emit("20D9")
    c.dbra(0, "restore_dir_header_loop")

    c.emit("41F900FFCC64")
    c.emit("224F")
    c.emit("43E90040")
    c.word(0x303C)
    c.word(FAT_STATE_LONGS - 1)
    c.label("restore_loop")
    c.emit("20D9")
    c.dbra(0, "restore_loop")

    c.emit("4FEF")
    c.word(FAT_STATE_BYTES + 0x40)
    c.emit("4CDF7FFF")
    c.emit("303900FFE30C")
    c.emit("4E75")

    c.label("browser_tag_tiles")
    tiles, map_words = readable_tag_assets(BROWSER_TAG_TEXT)
    c.data.extend(tiles)
    c.label("browser_tag_map")
    for word in map_words:
        c.word(word)

    if len(c.data) & 1:
        c.emit("00")
    return c.resolve(), c.labels


def disassemble(code: bytes) -> str:
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN)
    return "\n".join(
        f"{ins.address - BASE_ADDR:04X}: {ins.bytes.hex().upper():<20} {ins.mnemonic} {ins.op_str}"
        for ins in md.disasm(code, BASE_ADDR + CODE_OFFSET)
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    base = root / "M29W640-extract-os_bank_10000.bin"
    out = root / "OS-UPDATE-clone-main-poc135-h160-fatstate-wide-instagram-readable-y1-at.bin"
    patch_json = root / "patches" / "update-main-poc135-h160-fatstate-wide-instagram-readable-y1-at.json"

    data = bytearray(base.read_bytes())
    for off, (old, _new) in PAGE_TOP_PATCHES.items():
        if data[off : off + len(old)] != old:
            raise SystemExit(f"bytes antigos em 0x{off:04X} nao conferem")
    for off, old in PATCH_OFFSETS.items():
        if data[off : off + len(old)] != old:
            raise SystemExit(f"bytes antigos em 0x{off:04X} nao conferem")
    repaint_off, repaint_old = AFTER_REPAINT_PATCH
    if data[repaint_off : repaint_off + len(repaint_old)] != repaint_old:
        raise SystemExit(f"bytes antigos em 0x{repaint_off:04X} nao conferem")
    code, labels = build_code()
    end = CODE_OFFSET + len(code)
    if end > 0xA800:
        raise SystemExit(f"codigo ficou grande demais: 0x{end:04X}")

    for off, old in PATCH_OFFSETS.items():
        extension_addr = BASE_ADDR + off + 2
        disp = (BASE_ADDR + CODE_OFFSET) - extension_addr
        if not -0x8000 <= disp <= 0x7FFF:
            raise SystemExit(f"BSR fora de alcance em 0x{off:04X}")
        data[off : off + 4] = bytes.fromhex("6100") + (disp & 0xFFFF).to_bytes(2, "big")
    repaint_extension_addr = BASE_ADDR + repaint_off + 2
    repaint_disp = (BASE_ADDR + CODE_OFFSET) - repaint_extension_addr
    if not -0x8000 <= repaint_disp <= 0x7FFF:
        raise SystemExit("BSR fora de alcance para after repaint")
    for off, (_old, new) in PAGE_TOP_PATCHES.items():
        data[off : off + len(new)] = new
    data[repaint_off : repaint_off + len(repaint_old)] = (
        bytes.fromhex("6100") + (repaint_disp & 0xFFFF).to_bytes(2, "big") + bytes.fromhex("4E71")
    )
    data[CODE_OFFSET:end] = code
    out.write_bytes(data)

    patch_json.write_text(
        "[\n"
        "".join(
            "  {\n"
            f'    "offset": "0x{off:04X}",\n'
            f'    "old": "{old.hex().upper()}",\n'
            f'    "new": "{data[off:off+4].hex().upper()}"\n'
            "  },\n"
            for off, old in PATCH_OFFSETS.items()
        ) +
        "".join(
            "  {\n"
            f'    "offset": "0x{off:04X}",\n'
            f'    "old": "{old.hex().upper()}",\n'
            f'    "new": "{new.hex().upper()}"\n'
            "  },\n"
            for off, (old, new) in PAGE_TOP_PATCHES.items()
        ) +
        "  {\n"
        f'    "offset": "0x{repaint_off:04X}",\n'
        f'    "old": "{repaint_old.hex().upper()}",\n'
        f'    "new": "{data[repaint_off:repaint_off+len(repaint_old)].hex().upper()}"\n'
        "  },\n"
        "  {\n"
        f'    "offset": "0x{CODE_OFFSET:04X}",\n'
        f'    "new": "{code.hex().upper()}"\n'
        "  }\n"
        "]\n",
        encoding="utf-8",
    )

    print(f"wrote {out}")
    print(f"sha256: {hashlib.sha256(data).hexdigest()}")
    print(f"code: 0x{CODE_OFFSET:04X}..0x{end - 1:04X} ({len(code)} bytes)")
    print(disassemble(code))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
