import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "M29W640-extract-os_bank_10000.bin"
BUILDER = ROOT / "tools" / "edmd_build_browser_cover_pack_scp2_root_all_letters_poc135_h160_fatstate_wide_instagram_readable_y1_at.py"
PATCH_DIR = ROOT / "patches"


NORMAL_STRINGS = {
    0x941C: "OS error",
    0x9425: "required firmware v3 or more new",
    0x9446: "press any key for continue",
    0x948B: "enter name",
    0x9496: "(B)erase/back, (A)write, (start)done",
    0x950A: "rom patching...      ",
    0x9520: "rom patching... ",
    0x9531: "done ",
    0x9537: "GG codes list",
    0x9545: "(A)change, (B)back, (start)apply",
    0x956F: "enter gg codes",
    0x957E: "load gg codes",
    0x958C: "load error: ",
    0x962A: "!!!DO NOT TURN OFF THE SYSTEM!!!",
    0x964B: "copy sram to sd...",
    0x965E: "ROM type: SMS",
    0x966C: "ROM type: MD",
    0x9679: "erase...",
    0x9682: "copy...",
    0x968A: "copy sram from sd...",
    0x969F: "copy sram to flash...",
    0x96B5: "done!",
    0x96C8: "play game",
    0x96D2: "select game",
    0x96DE: "options",
    0x96E6: "cheats",
    0x96ED: "toolbox",
    0x96F5: "sel error: ",
    0x9701: "prog error: ",
    0x970E: "(A/START)open, (B)back",
    0x9725: "OS v",
    0x973A: "hard reset:",
    0x9746: "genny3 mode:",
    0x9753: "sram auto backup:",
    0x9765: "region free:",
    0x9772: "(A)change, (B)back",
    0x9785: "OFF",
    0x9789: "ON",
    0x978C: "AUTO",
    0x9791: "save...",
    0x979D: "fat init...",
    0x97AF: "open root...",
    0x97BC: "page: ",
    0x97C5: "ERROR: dir repaint: ",
    0x97DA: "ERROR: can not open dir: ",
    0x97F4: "file already exist ",
    0x9808: "press any key",
    0x9816: "save to file",
    0x9823: "save to new file",
    0x9834: "load from SD",
    0x9841: "save error: ",
    0x984E: "OS version: ",
    0x985B: "firmware version: ",
    0x986E: "megakey: ",
    0x988A: "file system: ",
    0x98A4: "console region: ",
    0x9905: "UNKNOWN",
    0x990D: "dir size: ",
    0x9918: "SMS key: ",
    0x9922: "pressed    ",
    0x992E: "not pressed",
    0x99B1: "assembly date:",
    0x99D0: "timer calibration...",
    0x99EF: "init mmc...",
    0x99FB: "ERROR: ",
    0x9A03: "testing...",
    0x9A0E: "time 1/10 sec: ",
    0x9A1E: "speed kb/s: ",
    0x9A2B: "OS update tool",
    0x9A3A: "are you sure?",
    0x9A48: "A(yes)  B(no)",
    0x9A56: "updating...",
    0x9A62: "OS to buff...",
    0x9A70: "verify buff...",
    0x9A7F: "verify flash...",
    0x9A8F: "success!",
    0x9A98: "device info",
    0x9AA4: "save/load sram",
    0x9AB3: "update OS",
    0x9ABD: "about",
    0x9AC3: "spi speed test",
    0x9AD2: "update error: ",
    0x9AE1: "(up/down)select page, (B)back",
}


PTBR = {
    "tag": "Siga no instagram: @tavinho.games",
    "title": "Firmware de capas",
    "by": "desenvolvida por:",
    "contact": "Contato:",
    "date_label": "Data da firmware",
    "pool_texts": ["Carregando", "Truques", "Atualizar SO"],
    "pointer_patches": {
        0x4D5C: (0x00FF9682, "Carregando"),
        0x6C74: (0x00FF9682, "Carregando"),
        0x52B0: (0x00FF96E6, "Truques"),
        0x7B82: (0x00FF9AB3, "Atualizar SO"),
    },
    "translations": {
        0x941C: "Erro OS",
        0x9425: "Firmware v3 ou maior requerido",
        0x9446: "Aperte tecla p/ continuar",
        0x948B: "Nome",
        0x9496: "B Apaga/Volta A Grava START Fim",
        0x950A: "Patch ROM...       ",
        0x9520: "Patch ROM... ",
        0x9531: "Ok   ",
        0x9537: "Lista Truques",
        0x9545: "A Muda, B Volta, START Aplica",
        0x956F: "Digitar Truque",
        0x957E: "Ler Truques",
        0x958C: "Erro Carga:",
        0x962A: "!!!NAO DESLIGUE O SISTEMA!!!",
        0x964B: "SRAM Para SD...",
        0x965E: "Tipo ROM: SMS",
        0x966C: "Tipo ROM: MD",
        0x9679: "Apagando",
        0x9682: "Carreg.",
        0x968A: "SRAM Do SD...",
        0x969F: "SRAM Para Flash...",
        0x96B5: "Feito",
        0x96C8: "Jogar ROM",
        0x96D2: "Selecionar",
        0x96DE: "Opcoes",
        0x96E6: "Truq.",
        0x96ED: "Extras",
        0x96F5: "Erro Sel: ",
        0x9701: "Erro Prog: ",
        0x970E: "A/START Abre, B Volta",
        0x9725: "SO v",
        0x973A: "Reset Hard:",
        0x9746: "Modo Genny3:",
        0x9753: "Backup Auto SRAM:",
        0x9765: "Reg. Livre:",
        0x9772: "A Muda, B Volta",
        0x9785: "Nao",
        0x9789: "ON",
        0x978C: "Auto",
        0x9791: "Salva..",
        0x979D: "Inic Fat...",
        0x97AF: "Abre Raiz...",
        0x97BC: "Pag.: ",
        0x97C5: "ERRO: Redesen. Dir:",
        0x97DA: "ERRO: Nao Pode Abrir Dir",
        0x97F4: "Arquivo Ja Existe ",
        0x9808: "Aperte Tecla",
        0x9816: "Salvar Arq.",
        0x9823: "Salvar Novo Arq",
        0x9834: "Carregar SD",
        0x9841: "Erro Salvar:",
        0x984E: "Versao SO: ",
        0x985B: "Versao Firmware:",
        0x986E: "Megakey: ",
        0x988A: "Sistema Arq:",
        0x98A4: "Regiao Console:",
        0x9905: "Desconh",
        0x990D: "Tam Dir: ",
        0x9918: "SMS key: ",
        0x9922: "Apertado",
        0x992E: "Nao Apert.",
        0x99B1: "Data Firmware:",
        0x99D0: "Calibrando Timer...",
        0x99EF: "Inic MMC...",
        0x99FB: "ERRO: ",
        0x9A03: "Testando..",
        0x9A0E: "Tempo 1/10s: ",
        0x9A1E: "Vel. KB/s: ",
        0x9A2B: "Atualizar SO",
        0x9A3A: "Tem Certeza?",
        0x9A48: "A(Sim) B(Nao)",
        0x9A56: "Atualiza..",
        0x9A62: "SO P/ Buff..",
        0x9A70: "Verif. Buff..",
        0x9A7F: "Verif. Flash..",
        0x9A8F: "Sucesso!",
        0x9A98: "Info Disp.",
        0x9AA4: "Salva/Ler SRAM",
        0x9AB3: "Atualizar",
        0x9ABD: "Sobre",
        0x9AC3: "Teste Vel SPI",
        0x9AD2: "Erro Update:",
        0x9AE1: "Cima/Baixo Pag., B Volta",
    },
}


ES = {
    "tag": "Sigue en instagram: @tavinho.games",
    "title": "Firmware caratulas",
    "by": "desarrollada por:",
    "contact": "Contacto",
    "date_label": "Fecha firmware",
    "pool_texts": ["Cargando", "Actualizar SO"],
    "pointer_patches": {
        0x4D5C: (0x00FF9682, "Cargando"),
        0x6C74: (0x00FF9682, "Cargando"),
        0x7B82: (0x00FF9AB3, "Actualizar SO"),
    },
    "translations": {
        0x941C: "Error OS",
        0x9425: "Requiere firmware v3 o +",
        0x9446: "Pulsa tecla p/ continuar",
        0x948B: "Nombre",
        0x9496: "B Borra/Vuelve A Escribe START Fin",
        0x950A: "Patch ROM...       ",
        0x9520: "Patch ROM... ",
        0x9531: "Ok   ",
        0x9537: "Lista Trucos",
        0x9545: "A Cambia, B Atras, START Aplica",
        0x956F: "Ingresar Truco",
        0x957E: "Cargar Trucos",
        0x958C: "Error Carga:",
        0x962A: "!!!NO APAGUE EL SISTEMA!!!",
        0x964B: "SRAM A SD...",
        0x965E: "Tipo ROM: SMS",
        0x966C: "Tipo ROM: MD",
        0x9679: "Borrando",
        0x9682: "Cargan.",
        0x968A: "SRAM Desde SD...",
        0x969F: "SRAM A Flash...",
        0x96B5: "Listo",
        0x96C8: "Jugar ROM",
        0x96D2: "Seleccionar",
        0x96DE: "Opcion",
        0x96E6: "Trucos",
        0x96ED: "Extras",
        0x96F5: "Err Sel: ",
        0x9701: "Err Prog: ",
        0x970E: "A/START Abre, B Atras",
        0x9725: "SO v",
        0x973A: "Reset Hard:",
        0x9746: "Modo Genny3:",
        0x9753: "Backup Auto SRAM:",
        0x9765: "Reg. Libre:",
        0x9772: "A Cambia, B Atras",
        0x9785: "No ",
        0x9789: "SI",
        0x978C: "Auto",
        0x9791: "Guarda.",
        0x979D: "Inic Fat...",
        0x97AF: "Abre Raiz...",
        0x97BC: "Pag.: ",
        0x97C5: "ERROR: Redib. Dir:",
        0x97DA: "ERROR: No Puede Abrir Dir",
        0x97F4: "Archivo Ya Existe ",
        0x9808: "Pulsa Tecla",
        0x9816: "Guardar Arch",
        0x9823: "Guardar Nuevo",
        0x9834: "Cargar De SD",
        0x9841: "Error Guard:",
        0x984E: "Version SO: ",
        0x985B: "Version Firmware",
        0x986E: "Megakey: ",
        0x988A: "Sistema Arch",
        0x98A4: "Region Consola:",
        0x9905: "Descon",
        0x990D: "Tam Dir: ",
        0x9918: "SMS key: ",
        0x9922: "Pulsado",
        0x992E: "No Pulsado",
        0x99B1: "Fecha Firm.:",
        0x99D0: "Calibrar Timer...",
        0x99EF: "Inic MMC...",
        0x99FB: "ERROR: ",
        0x9A03: "Probando..",
        0x9A0E: "Tiempo 1/10s:",
        0x9A1E: "Vel. KB/s: ",
        0x9A2B: "Actualizar SO",
        0x9A3A: "Seguro?",
        0x9A48: "A(Si) B(No)",
        0x9A56: "Actualiza.",
        0x9A62: "SO A Buff...",
        0x9A70: "Verif. Buff..",
        0x9A7F: "Verif. Flash.",
        0x9A8F: "Exito!",
        0x9A98: "Info Disp.",
        0x9AA4: "Guardar/Cargar",
        0x9AB3: "Actualiza",
        0x9ABD: "Info",
        0x9AC3: "Test Vel SPI",
        0x9AD2: "Error Act.: ",
        0x9AE1: "Arr/Aba Pag., B Atras",
    },
}


LANGS = {
    "PTBR": PTBR,
    "ES": ES,
}


def load_builder():
    spec = importlib.util.spec_from_file_location("poc135_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load builder")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.READABLE_FONT_5X7.setdefault(
        "U",
        ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    )
    return mod


def build_cover_base(builder, tag: str) -> tuple[bytearray, int, bytes]:
    builder.BROWSER_TAG_TEXT = tag
    data = bytearray(BASE.read_bytes())
    for off, (old, new) in builder.PAGE_TOP_PATCHES.items():
        require(data, off, old)
        data[off : off + len(new)] = new

    repaint_off, repaint_old = builder.AFTER_REPAINT_PATCH
    require(data, repaint_off, repaint_old)
    code, _labels = builder.build_code()
    end = builder.CODE_OFFSET + len(code)
    if end > 0xA800:
        raise SystemExit(f"{tag!r}: injected code too large: 0x{end:04X}")

    extension_addr = builder.BASE_ADDR + repaint_off + 2
    disp = (builder.BASE_ADDR + builder.CODE_OFFSET) - extension_addr
    if not -0x8000 <= disp <= 0x7FFF:
        raise SystemExit("after-repaint BSR out of range")
    data[repaint_off : repaint_off + len(repaint_old)] = (
        bytes.fromhex("6100") + (disp & 0xFFFF).to_bytes(2, "big") + bytes.fromhex("4E71")
    )
    data[builder.CODE_OFFSET : end] = code
    return data, end, code


def require(data: bytearray, off: int, old: bytes) -> None:
    found = data[off : off + len(old)]
    if found != old:
        raise SystemExit(f"old bytes mismatch at 0x{off:04X}: {found.hex().upper()} != {old.hex().upper()}")


def patch_slot(data: bytearray, patches: list[dict[str, str]], off: int, old: str, new: str) -> None:
    old_b = old.encode("ascii")
    new_b = new.encode("ascii")
    if len(new_b) > len(old_b):
        raise SystemExit(f"translation too long at 0x{off:04X}: {new!r} > {old!r}")
    require(data, off, old_b)
    replacement = new_b + (b"\x00" * (len(old_b) - len(new_b)))
    data[off : off + len(old_b)] = replacement
    patches.append({"offset": f"0x{off:04X}", "old": old_b.hex().upper(), "new": replacement.hex().upper()})


def patch_cstr(data: bytearray, patches: list[dict[str, str]], off: int, old: str, new: str) -> None:
    old_b = old.encode("ascii")
    new_b = new.encode("ascii")
    require(data, off, old_b)
    nul = data.find(b"\x00", off)
    if nul < 0:
        raise SystemExit(f"unterminated string at 0x{off:04X}")
    slot = nul - off
    if len(new_b) > slot:
        raise SystemExit(f"cstr too long at 0x{off:04X}: {new!r} ({len(new_b)}) > {slot}")
    original = bytes(data[off : nul + 1])
    data[off : nul + 1] = new_b + b"\x00" + (b"\x00" * (slot - len(new_b)))
    patches.append({"offset": f"0x{off:04X}", "old": original.hex().upper(), "new": bytes(data[off : nul + 1]).hex().upper()})


def patch_long(data: bytearray, patches: list[dict[str, str]], off: int, old: int, new: int) -> None:
    old_b = old.to_bytes(4, "big")
    new_b = new.to_bytes(4, "big")
    require(data, off, old_b)
    data[off : off + 4] = new_b
    patches.append({"offset": f"0x{off:04X}", "old": old_b.hex().upper(), "new": new_b.hex().upper()})


def write_pool(data: bytearray, patches: list[dict[str, str]], lang: dict) -> dict[str, int]:
    pos = 0xC06C
    end = pos
    while end < len(data) and data[end] == 0xFF:
        end += 1
    if end - pos < 128:
        raise SystemExit("free text pool not found")
    original = bytes(data[pos:end])
    labels: dict[str, int] = {}
    for text in [
        "instagram.com/tavinho.games",
        "youtube.com/@tavinho-games",
        lang["date_label"],
        *lang.get("pool_texts", []),
    ]:
        if text in labels:
            continue
        labels[text] = pos
        b = text.encode("ascii")
        data[pos : pos + len(b) + 1] = b + b"\x00"
        pos += len(b) + 1
    data[pos:end] = b"\xFF" * (end - pos)
    patches.append({"offset": "0xC06C", "old": original.hex().upper(), "new": bytes(data[0xC06C:end]).hex().upper()})
    return labels


def apply_language(data: bytearray, lang_name: str, lang: dict) -> list[dict[str, str]]:
    patches: list[dict[str, str]] = []

    # Keep the original string end positions. This avoids shifting nearby code or tables.
    for off, old in NORMAL_STRINGS.items():
        patch_slot(data, patches, off, old, lang["translations"][off])

    labels = write_pool(data, patches, lang)

    patch_cstr(data, patches, 0x993A, "EverDrive-MD flashcart", lang["title"])
    patch_cstr(data, patches, 0x9951, "developed by Igor Golubovskiy", lang["by"])
    patch_cstr(data, patches, 0x996F, "assembled in Ukraine", "Tavinho Games")
    patch_cstr(data, patches, 0x9984, "support:", lang["contact"])
    patch_cstr(data, patches, 0x998D, "http://krikzz.com", "")
    patch_cstr(data, patches, 0x999F, "biokrik@gmail.com", "")

    patch_long(data, patches, 0x749C, 0x00FF998D, 0x00FF0000 + labels["instagram.com/tavinho.games"])
    patch_long(data, patches, 0x74CC, 0x00FF999F, 0x00FF0000 + labels["youtube.com/@tavinho-games"])
    patch_long(data, patches, 0x7512, 0x00FF99B1, 0x00FF0000 + labels[lang["date_label"]])
    for off, (old_ptr, text) in lang.get("pointer_patches", {}).items():
        patch_long(data, patches, off, old_ptr, 0x00FF0000 + labels[text])

    patch_slot(data, patches, 0xC004, "05.01.2011", "13/07/2026")
    patch_cstr(data, patches, 0x99C0, "distributed by:", "")
    patch_cstr(data, patches, 0xC024, "gamejoy84", "")
    patch_cstr(data, patches, 0xC04C, "http://shop107027260.taobao.com", "")

    logo_off = 0x7606
    logo_old = bytes.fromhex("4EB900FF8F66")
    logo_new = bytes.fromhex("4E714E714E71")
    require(data, logo_off, logo_old)
    data[logo_off : logo_off + len(logo_new)] = logo_new
    patches.append({"offset": f"0x{logo_off:04X}", "old": logo_old.hex().upper(), "new": logo_new.hex().upper()})

    if lang_name == "ES" and data.find(b"Sigue en instagram") >= 0:
        raise SystemExit("browser tag should be tile data, not ASCII")
    return patches


def main() -> int:
    builder = load_builder()
    PATCH_DIR.mkdir(exist_ok=True)
    results = []
    for lang_name, lang in LANGS.items():
        data, end, code = build_cover_base(builder, lang["tag"])
        patches = apply_language(data, lang_name, lang)
        out = ROOT / f"OS-UPDATE-clone-main-poc135-{lang_name}.bin"
        patch_json = PATCH_DIR / f"update-main-poc135-{lang_name}.json"
        out.write_bytes(data)
        patch_json.write_text(json.dumps(patches, indent=2) + "\n", encoding="utf-8")
        results.append((lang_name, out, hashlib.sha256(data).hexdigest(), end, len(code)))

    for lang_name, out, digest, end, code_len in results:
        print(f"{lang_name}: wrote {out}")
        print(f"{lang_name}: sha256 {digest}")
        print(f"{lang_name}: code 0x9C00..0x{end - 1:04X} ({code_len} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
