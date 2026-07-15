from __future__ import annotations

import contextlib
import json
import queue
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import BooleanVar, Button, Canvas, END, Label, Listbox, StringVar, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk

import edmd_bulk_convert_covers


APP_TITLE = "EDMD Cover Pack Tool"
CREDIT_INSTAGRAM_URL = "https://instagram.com/tavinho.games"
CREDIT_YOUTUBE_URL = "https://youtube.com/@tavinho-games"


class QueueWriter:
    def __init__(self, out_queue: queue.Queue[str]) -> None:
        self.out_queue = out_queue

    def write(self, text: str) -> int:
        if text:
            self.out_queue.put(text)
        return len(text)

    def flush(self) -> None:
        return


TEXT = {
    "pt": {
        "window_title": "Gerador de PAKs",
        "heading": "Gerador de PAKs",
        "credits_button": "Créditos",
        "credits_title": "Créditos",
        "credits_message": "Firmware de capas e ferramenta por:\nTavinho Games",
        "credits_instagram": "Instagram",
        "credits_youtube": "YouTube",
        "open_link_error": "Não foi possível abrir o link:\n{url}",
        "language": "Idioma",
        "rom_dir": "Pasta das ROMs",
        "cover_dir": "Pasta das capas",
        "crop_file": "Arquivo de recortes",
        "crop_search": "Pesquisar capa:",
        "map_csv": "Mapa manual CSV (opcional)",
        "output_dir": "Destino dos .PAK",
        "report_dir": "Pasta de relatório",
        "select": "Selecionar",
        "relative_names": "Nome relativo",
        "match_variants": "Associar capa a variantes do mesmo jogo",
        "previews": "Previews:",
        "generate": "Gerar .PAK",
        "crop_editor": "Editor de recorte",
        "open_output": "Abrir destino",
        "open_report": "Abrir relatório",
        "ready": "Pronto",
        "invalid_folder": "Pasta inválida: ",
        "folder_missing": "Pasta não existe:\n{path}",
        "generating": "Gerando packs... 0%",
        "new_generation": "\n=== Nova geração ===\n",
        "report_ok": "\nOK. Relatório: {path}\n",
        "finished_with_code": "\nTerminou com código {code}. Veja o log acima.\n",
        "process_error": "Erro ao gerar packs",
        "unexpected_error": "\nERRO: {error}\n",
        "report_missing": "\nConcluído. Relatório não encontrado para resumo.\n",
        "done_status": "Concluído: {matched} capas em {packs} PAK(s)",
        "done_header": "\n=== Concluído ===",
        "associated": "Capas associadas: {count}",
        "paks_generated": "PAKs gerados: {count}",
        "roms_without_cover": "ROMs sem capa: {count}",
        "images_without_match": "Imagens sem match: {count}",
        "generated_files": "Arquivos gerados:",
        "pack_cover_count": "capas",
        "convert_status": "Convertendo capas... {percent}% ({done}/{total})",
        "pack_status": "Montando PAKs... {percent}% ({done}/{total})",
        "wait_running": "Aguarde a geração terminar antes de trocar o idioma.",
        "map_help": "Arquivo CSV opcional com colunas cover,rom. Use para forçar qual capa pertence a qual ROM quando o match automático falhar ou escolher a capa errada.",
        "relative_help": "Marcado: usa comparação inteligente por nome, aceitando diferenças de pontuação, região e variantes. Desmarcado: exige nome idêntico entre capa e ROM, mudando apenas a extensão.",
        "variants_help": "Quando ativado, uma capa pode ser aplicada a variantes da mesma ROM, por exemplo USA, Europe, Rev A ou Final Cut, desde que o título principal combine.",
        "previews_help": "Quantidade de PNGs de preview gerados no PC para conferir a conversão. Não altera os PAKs nem muda o que aparece no EverDrive.",
        "crop_file_help": "Arquivo JSON onde a ferramenta salva o enquadramento manual de cada capa. Ele é usado automaticamente ao gerar os .PAK em 128x160.",
        "crop_editor_missing": "Escolha uma pasta de capas válida antes de abrir o editor de recorte.",
        "crop_window_title": "Editor de recorte",
        "crop_instructions": "Selecione uma capa. Arraste o quadro para mover; use a roda do mouse ou Zoom para aproximar/afastar. Salve o recorte para usar na próxima conversão.",
        "crop_save": "Salvar recorte",
        "crop_remove": "Remover recorte",
        "crop_reset": "Centralizar",
        "crop_zoom_in": "Zoom +",
        "crop_zoom_out": "Zoom -",
        "crop_close": "Fechar",
        "crop_saved": "Recorte salvo: {name}",
        "crop_removed": "Recorte removido: {name}",
        "flow": (
            "Fluxo:\n"
            "1. Escolha a raiz das ROMs ou do SD.\n"
            "2. Escolha a pasta com PNG/JPG das capas.\n"
            "3. Opcional: escolha um CSV manual com colunas cover,rom.\n"
            "4. Escolha o destino dos .PAK, normalmente a raiz do SD.\n"
            "5. Clique em Gerar .PAK.\n\n"
            "Ao final do processo, confira cover-map-template.csv, unmatched-roms.txt e unmatched-images.txt na pasta de relatório.\n"
            "Obs: a firmware atual mostra capas para ROMs .bin iniciando com 0-9 ou A-Z.\n\n"
        ),
    },
    "en": {
        "window_title": "PAK Generator",
        "heading": "PAK Generator",
        "credits_button": "Credits",
        "credits_title": "Credits",
        "credits_message": "Cover firmware and tool by:\nTavinho Games",
        "credits_instagram": "Instagram",
        "credits_youtube": "YouTube",
        "open_link_error": "Could not open this link:\n{url}",
        "language": "Language",
        "rom_dir": "ROM folder",
        "cover_dir": "Cover folder",
        "crop_file": "Crop file",
        "crop_search": "Search cover:",
        "map_csv": "Manual CSV map (optional)",
        "output_dir": ".PAK output folder",
        "report_dir": "Report folder",
        "select": "Browse",
        "relative_names": "Relative name",
        "match_variants": "Apply cover to variants of the same game",
        "previews": "Previews:",
        "generate": "Generate .PAK",
        "crop_editor": "Crop editor",
        "open_output": "Open output",
        "open_report": "Open report",
        "ready": "Ready",
        "invalid_folder": "Invalid folder: ",
        "folder_missing": "Folder does not exist:\n{path}",
        "generating": "Generating packs... 0%",
        "new_generation": "\n=== New generation ===\n",
        "report_ok": "\nOK. Report: {path}\n",
        "finished_with_code": "\nFinished with code {code}. Check the log above.\n",
        "process_error": "Error generating packs",
        "unexpected_error": "\nERROR: {error}\n",
        "report_missing": "\nDone. Report was not found for summary.\n",
        "done_status": "Done: {matched} covers in {packs} PAK(s)",
        "done_header": "\n=== Done ===",
        "associated": "Matched covers: {count}",
        "paks_generated": "Generated PAKs: {count}",
        "roms_without_cover": "ROMs without cover: {count}",
        "images_without_match": "Images without match: {count}",
        "generated_files": "Generated files:",
        "pack_cover_count": "covers",
        "convert_status": "Converting covers... {percent}% ({done}/{total})",
        "pack_status": "Building PAKs... {percent}% ({done}/{total})",
        "wait_running": "Wait for generation to finish before changing the language.",
        "map_help": "Optional CSV file with cover,rom columns. Use it to force which cover belongs to which ROM when automatic matching fails or chooses the wrong cover.",
        "relative_help": "Checked: uses smart name matching, accepting punctuation, region and variant differences. Unchecked: requires identical cover and ROM names, changing only the extension.",
        "variants_help": "When enabled, one cover can be applied to variants of the same ROM, such as USA, Europe, Rev A or Final Cut, as long as the main title matches.",
        "previews_help": "Number of preview PNGs generated on the PC to check the conversion. It does not change the PAKs or what appears on the EverDrive.",
        "crop_file_help": "JSON file where the tool saves the manual framing for each cover. It is used automatically when generating 128x160 .PAK files.",
        "crop_editor_missing": "Choose a valid cover folder before opening the crop editor.",
        "crop_window_title": "Crop editor",
        "crop_instructions": "Select a cover. Drag the frame to move it; use the mouse wheel or Zoom to crop closer/farther. Save the crop to use it in the next conversion.",
        "crop_save": "Save crop",
        "crop_remove": "Remove crop",
        "crop_reset": "Center",
        "crop_zoom_in": "Zoom +",
        "crop_zoom_out": "Zoom -",
        "crop_close": "Close",
        "crop_saved": "Crop saved: {name}",
        "crop_removed": "Crop removed: {name}",
        "flow": (
            "Flow:\n"
            "1. Choose the ROM or SD root folder.\n"
            "2. Choose the folder with PNG/JPG covers.\n"
            "3. Optional: choose a manual CSV with cover,rom columns.\n"
            "4. Choose the .PAK output folder, usually the SD root.\n"
            "5. Click Generate .PAK.\n\n"
            "When the process finishes, check cover-map-template.csv, unmatched-roms.txt and unmatched-images.txt in the report folder.\n"
            "Note: the current firmware shows covers for .bin ROMs starting with 0-9 or A-Z.\n\n"
        ),
    },
    "es": {
        "window_title": "Generador de PAKs",
        "heading": "Generador de PAKs",
        "credits_button": "Créditos",
        "credits_title": "Créditos",
        "credits_message": "Firmware de carátulas y herramienta por:\nTavinho Games",
        "credits_instagram": "Instagram",
        "credits_youtube": "YouTube",
        "open_link_error": "No fue posible abrir el enlace:\n{url}",
        "language": "Idioma",
        "rom_dir": "Carpeta de ROMs",
        "cover_dir": "Carpeta de carátulas",
        "crop_file": "Archivo de recortes",
        "crop_search": "Buscar carátula:",
        "map_csv": "Mapa manual CSV (opcional)",
        "output_dir": "Destino de los .PAK",
        "report_dir": "Carpeta de informe",
        "select": "Seleccionar",
        "relative_names": "Nombre relativo",
        "match_variants": "Asociar carátula a variantes del mismo juego",
        "previews": "Previews:",
        "generate": "Generar .PAK",
        "crop_editor": "Editor de recorte",
        "open_output": "Abrir destino",
        "open_report": "Abrir informe",
        "ready": "Listo",
        "invalid_folder": "Carpeta inválida: ",
        "folder_missing": "La carpeta no existe:\n{path}",
        "generating": "Generando packs... 0%",
        "new_generation": "\n=== Nueva generación ===\n",
        "report_ok": "\nOK. Informe: {path}\n",
        "finished_with_code": "\nTerminó con código {code}. Revisa el log arriba.\n",
        "process_error": "Error al generar packs",
        "unexpected_error": "\nERROR: {error}\n",
        "report_missing": "\nConcluido. No se encontró el informe para el resumen.\n",
        "done_status": "Concluido: {matched} carátulas en {packs} PAK(s)",
        "done_header": "\n=== Concluido ===",
        "associated": "Carátulas asociadas: {count}",
        "paks_generated": "PAKs generados: {count}",
        "roms_without_cover": "ROMs sin carátula: {count}",
        "images_without_match": "Imágenes sin coincidencia: {count}",
        "generated_files": "Archivos generados:",
        "pack_cover_count": "carátulas",
        "convert_status": "Convirtiendo carátulas... {percent}% ({done}/{total})",
        "pack_status": "Creando PAKs... {percent}% ({done}/{total})",
        "wait_running": "Espera a que termine la generación antes de cambiar el idioma.",
        "map_help": "Archivo CSV opcional con columnas cover,rom. Úsalo para forzar qué carátula pertenece a cada ROM cuando la coincidencia automática falle o elija una carátula incorrecta.",
        "relative_help": "Marcado: usa comparación inteligente por nombre, aceptando diferencias de puntuación, región y variantes. Desmarcado: exige nombre idéntico entre carátula y ROM, cambiando solo la extensión.",
        "variants_help": "Cuando está activado, una carátula puede aplicarse a variantes de la misma ROM, por ejemplo USA, Europe, Rev A o Final Cut, siempre que el título principal coincida.",
        "previews_help": "Cantidad de PNGs de preview generados en el PC para revisar la conversión. No cambia los PAKs ni lo que aparece en el EverDrive.",
        "crop_file_help": "Archivo JSON donde la herramienta guarda el encuadre manual de cada carátula. Se usa automáticamente al generar los .PAK en 128x160.",
        "crop_editor_missing": "Elige una carpeta de carátulas válida antes de abrir el editor de recorte.",
        "crop_window_title": "Editor de recorte",
        "crop_instructions": "Selecciona una carátula. Arrastra el marco para moverlo; usa la rueda del mouse o Zoom para acercar/alejar. Guarda el recorte para usarlo en la próxima conversión.",
        "crop_save": "Guardar recorte",
        "crop_remove": "Eliminar recorte",
        "crop_reset": "Centrar",
        "crop_zoom_in": "Zoom +",
        "crop_zoom_out": "Zoom -",
        "crop_close": "Cerrar",
        "crop_saved": "Recorte guardado: {name}",
        "crop_removed": "Recorte eliminado: {name}",
        "flow": (
            "Flujo:\n"
            "1. Elige la raíz de las ROMs o de la SD.\n"
            "2. Elige la carpeta con carátulas PNG/JPG.\n"
            "3. Opcional: elige un CSV manual con columnas cover,rom.\n"
            "4. Elige el destino de los .PAK, normalmente la raíz de la SD.\n"
            "5. Haz clic en Generar .PAK.\n\n"
            "Al finalizar el proceso, revisa cover-map-template.csv, unmatched-roms.txt y unmatched-images.txt en la carpeta de informe.\n"
            "Nota: la firmware actual muestra carátulas para ROMs .bin que empiezan con 0-9 o A-Z.\n\n"
        ),
    },
}

LANGUAGE_BUTTONS = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
}


class Tooltip:
    def __init__(self, widget: object, text: str, delay_ms: int = 450) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip: Toplevel | None = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: object | None = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self._tip is not None:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip = Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        Label(
            self._tip,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=5,
            wraplength=380,
        ).pack()

    def _hide(self, _event: object | None = None) -> None:
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
TARGET_ASPECT = 128 / 160


class CropEditor:
    def __init__(self, parent: Tk, cover_dir: Path, crop_path: Path, language: str) -> None:
        self.parent = parent
        self.cover_dir = cover_dir
        self.crop_path = crop_path
        self.text = TEXT[language]
        self.images = sorted([p for p in cover_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS], key=lambda p: p.name.upper())
        self.filtered_images: list[Path] = list(self.images)
        self.search_text = StringVar(value="")
        self.crops = self._load_crops()
        self.current: Path | None = None
        self.source_image: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None
        self.crop_box: tuple[float, float, float, float] | None = None
        self.display_scale = 1.0
        self.display_offset = (0, 0)
        self.dragging = False
        self.drag_offset = (0.0, 0.0)

        self.win = Toplevel(parent)
        self.win.title(self.text["crop_window_title"])
        self.win.geometry("960x680")
        self.win.minsize(840, 600)

        self._build_ui()
        self._refresh_list()
        if self.images:
            self.listbox.selection_set(0)
            self._select_index(0)

    def _build_ui(self) -> None:
        root = ttk.Frame(self.win)
        root.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(root, text=self.text["crop_instructions"], wraplength=900).pack(fill="x", pady=(0, 8))

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(left, text=self.text["crop_search"]).pack(anchor="w")
        search_entry = ttk.Entry(left, textvariable=self.search_text, width=36)
        search_entry.pack(fill="x", pady=(0, 6))
        self.search_text.trace_add("write", lambda *_args: self._apply_filter())
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="y", expand=True)
        self.listbox = Listbox(list_frame, width=36, exportselection=False)
        self.listbox.pack(side="left", fill="y", expand=False)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.canvas = Canvas(right, width=620, height=500, background="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Configure>", lambda _event: self._redraw())

        controls = ttk.Frame(root)
        controls.pack(fill="x", pady=(10, 0))
        ttk.Button(controls, text=self.text["crop_zoom_in"], command=lambda: self._zoom(0.88)).pack(side="left")
        ttk.Button(controls, text=self.text["crop_zoom_out"], command=lambda: self._zoom(1.14)).pack(side="left", padx=6)
        ttk.Button(controls, text=self.text["crop_reset"], command=self._reset_crop).pack(side="left")
        ttk.Button(controls, text=self.text["crop_save"], command=self._save_crop).pack(side="left", padx=(18, 6))
        ttk.Button(controls, text=self.text["crop_remove"], command=self._remove_crop).pack(side="left")
        ttk.Button(controls, text=self.text["crop_close"], command=self.win.destroy).pack(side="right")
        self.status = StringVar(value="")
        ttk.Label(root, textvariable=self.status).pack(fill="x", pady=(8, 0))

    def _load_crops(self) -> dict[str, list[float]]:
        if not self.crop_path.exists():
            return {}
        try:
            raw = json.loads(self.crop_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {}
        crops = raw.get("crops", {})
        if not isinstance(crops, dict):
            return {}
        result: dict[str, list[float]] = {}
        for key, value in crops.items():
            if isinstance(value, list) and len(value) == 4:
                try:
                    result[str(key)] = [float(v) for v in value]
                except (TypeError, ValueError):
                    continue
        return result

    def _write_crops(self) -> None:
        self.crop_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "target": "128x160", "crops": self.crops}
        self.crop_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _refresh_list(self) -> None:
        selected = self.current.name if self.current else None
        self.listbox.delete(0, END)
        new_index = 0
        for idx, path in enumerate(self.filtered_images):
            marker = "* " if path.name in self.crops else "  "
            self.listbox.insert(END, marker + path.name)
            if selected == path.name:
                new_index = idx
        if self.filtered_images:
            self.listbox.selection_clear(0, END)
            self.listbox.selection_set(new_index)

    def _apply_filter(self) -> None:
        needle = self.search_text.get().strip().lower()
        if not needle:
            self.filtered_images = list(self.images)
        else:
            terms = [term for term in needle.split() if term]
            self.filtered_images = [
                path for path in self.images
                if all(term in path.name.lower() for term in terms)
            ]
        self._refresh_list()
        if self.filtered_images:
            selection = self.listbox.curselection()
            index = int(selection[0]) if selection else 0
            self._select_index(index)
        else:
            self.current = None
            self.source_image = None
            self.crop_box = None
            self.canvas.delete("all")

    def _on_select(self, _event: object | None = None) -> None:
        selection = self.listbox.curselection()
        if selection:
            self._select_index(int(selection[0]))

    def _select_index(self, index: int) -> None:
        if index < 0 or index >= len(self.filtered_images):
            return
        self.current = self.filtered_images[index]
        self.source_image = Image.open(self.current).convert("RGB")
        saved = self.crops.get(self.current.name)
        self.crop_box = tuple(saved) if saved else self._auto_crop(self.source_image)
        self.status.set("")
        self._redraw()

    def _auto_crop(self, image: Image.Image) -> tuple[float, float, float, float]:
        img_ratio = image.width / image.height
        if img_ratio > TARGET_ASPECT:
            crop_w = image.height * TARGET_ASPECT
            left = (image.width - crop_w) / 2
            return (left / image.width, 0.0, (left + crop_w) / image.width, 1.0)
        crop_h = image.width / TARGET_ASPECT
        top = (image.height - crop_h) / 2
        return (0.0, top / image.height, 1.0, (top + crop_h) / image.height)

    def _redraw(self) -> None:
        self.canvas.delete("all")
        if self.source_image is None or self.crop_box is None:
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        scale = min(width / self.source_image.width, height / self.source_image.height)
        disp_w = max(1, round(self.source_image.width * scale))
        disp_h = max(1, round(self.source_image.height * scale))
        offset_x = (width - disp_w) // 2
        offset_y = (height - disp_h) // 2
        self.display_scale = scale
        self.display_offset = (offset_x, offset_y)

        preview = self.source_image.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(preview)
        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self.tk_image)

        left, top, right, bottom = self._box_canvas_coords()
        self.canvas.create_rectangle(left, top, right, bottom, outline="#ffd400", width=3)
        self.canvas.create_rectangle(left + 3, top + 3, right - 3, bottom - 3, outline="#111111", width=1)

    def _box_canvas_coords(self) -> tuple[float, float, float, float]:
        assert self.source_image is not None
        assert self.crop_box is not None
        ox, oy = self.display_offset
        left, top, right, bottom = self.crop_box
        return (
            ox + left * self.source_image.width * self.display_scale,
            oy + top * self.source_image.height * self.display_scale,
            ox + right * self.source_image.width * self.display_scale,
            oy + bottom * self.source_image.height * self.display_scale,
        )

    def _canvas_to_norm(self, x: float, y: float) -> tuple[float, float]:
        assert self.source_image is not None
        ox, oy = self.display_offset
        nx = (x - ox) / (self.source_image.width * self.display_scale)
        ny = (y - oy) / (self.source_image.height * self.display_scale)
        return max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))

    def _on_press(self, event: object) -> None:
        if self.source_image is None or self.crop_box is None:
            return
        x = float(getattr(event, "x"))
        y = float(getattr(event, "y"))
        left, top, right, bottom = self._box_canvas_coords()
        cx, cy = self._canvas_to_norm(x, y)
        box_left, box_top, box_right, box_bottom = self.crop_box
        if left <= x <= right and top <= y <= bottom:
            center_x = (box_left + box_right) / 2
            center_y = (box_top + box_bottom) / 2
            self.drag_offset = (center_x - cx, center_y - cy)
        else:
            self.drag_offset = (0.0, 0.0)
            self._set_center(cx, cy)
        self.dragging = True

    def _on_drag(self, event: object) -> None:
        if not self.dragging or self.crop_box is None:
            return
        cx, cy = self._canvas_to_norm(float(getattr(event, "x")), float(getattr(event, "y")))
        self._set_center(cx + self.drag_offset[0], cy + self.drag_offset[1])

    def _on_release(self, _event: object | None = None) -> None:
        self.dragging = False

    def _on_wheel(self, event: object) -> None:
        delta = int(getattr(event, "delta"))
        self._zoom(0.92 if delta > 0 else 1.08)

    def _set_center(self, center_x: float, center_y: float) -> None:
        if self.crop_box is None:
            return
        left, top, right, bottom = self.crop_box
        width = right - left
        height = bottom - top
        center_x = max(width / 2, min(1.0 - width / 2, center_x))
        center_y = max(height / 2, min(1.0 - height / 2, center_y))
        self.crop_box = (
            center_x - width / 2,
            center_y - height / 2,
            center_x + width / 2,
            center_y + height / 2,
        )
        self._redraw()

    def _zoom(self, factor: float) -> None:
        if self.crop_box is None:
            return
        left, top, right, bottom = self.crop_box
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        width = min(1.0, max(0.08, (right - left) * factor))
        height = min(1.0, max(0.08, (bottom - top) * factor))
        if width >= 1.0 or height >= 1.0:
            self._reset_crop()
            return
        self.crop_box = (0, 0, width, height)
        self._set_center(center_x, center_y)

    def _reset_crop(self) -> None:
        if self.source_image is None:
            return
        self.crop_box = self._auto_crop(self.source_image)
        self._redraw()

    def _save_crop(self) -> None:
        if self.current is None or self.crop_box is None:
            return
        self.crops[self.current.name] = [round(v, 6) for v in self.crop_box]
        self._write_crops()
        self._refresh_list()
        self.status.set(self.text["crop_saved"].format(name=self.current.name))

    def _remove_crop(self) -> None:
        if self.current is None:
            return
        self.crops.pop(self.current.name, None)
        self._write_crops()
        if self.source_image is not None:
            self.crop_box = self._auto_crop(self.source_image)
        self._refresh_list()
        self._redraw()
        self.status.set(self.text["crop_removed"].format(name=self.current.name))


class CoverPackTool:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.geometry("980x700")
        self.root.minsize(840, 600)

        base = Path(__file__).resolve().parents[1]
        self.language = StringVar(value="pt")
        self.rom_dir = StringVar(value="")
        self.cover_dir = StringVar(value="")
        self.crop_json = StringVar(value=str(base / "cover-crops.json"))
        self.map_csv = StringVar(value="")
        self.output_dir = StringVar(value="")
        self.work_dir = StringVar(value=str(base / "cover-tool-output"))
        self.relative_names = BooleanVar(value=True)
        self.match_variants = BooleanVar(value=True)
        self.preview_count = StringVar(value="16")
        self.status = StringVar(value="")
        self.progress_text = StringVar(value="0%")
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._tooltips: list[Tooltip] = []

        self._build_ui()
        self._poll_log()

    def _t(self, key: str) -> str:
        return TEXT[self.language.get()][key]

    def _text_for(self, language: str, key: str) -> str:
        return TEXT[language][key]

    def _build_ui(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self._tooltips = []
        self.root.title(f"{APP_TITLE} - {self._t('window_title')}")
        self.status.set(self._t("ready"))

        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 4))
        title_box = ttk.Frame(top)
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text=self._t("heading"), font=("", 13, "bold")).pack(anchor="w")
        header_actions = ttk.Frame(top)
        header_actions.pack(side="right")
        ttk.Button(header_actions, text=self._t("credits_button"), command=self._show_credits).pack(side="left", padx=(0, 8))
        self._language_selector(header_actions).pack(side="left")

        self._path_row(frm, 1, self._t("rom_dir"), self.rom_dir)
        self._path_row(frm, 2, self._t("cover_dir"), self.cover_dir)
        self._file_row(frm, 3, self._t("crop_file"), self.crop_json, self._t("crop_file_help"), [("JSON", "*.json"), ("All", "*.*")])
        self._file_row(frm, 4, self._t("map_csv"), self.map_csv, self._t("map_help"), [("CSV", "*.csv"), ("All", "*.*")])
        self._path_row(frm, 5, self._t("output_dir"), self.output_dir)
        self._path_row(frm, 6, self._t("report_dir"), self.work_dir)

        opts = ttk.Frame(frm)
        opts.grid(row=7, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Checkbutton(opts, text=self._t("relative_names"), variable=self.relative_names).pack(side="left")
        self._help_icon(opts, self._t("relative_help")).pack(side="left", padx=(4, 14))
        ttk.Checkbutton(opts, text=self._t("match_variants"), variable=self.match_variants).pack(side="left")
        self._help_icon(opts, self._t("variants_help")).pack(side="left", padx=(4, 0))
        ttk.Label(opts, text=self._t("previews")).pack(side="left", padx=(24, 4))
        self._help_icon(opts, self._t("previews_help")).pack(side="left", padx=(0, 4))
        ttk.Entry(opts, textvariable=self.preview_count, width=6).pack(side="left")

        buttons = ttk.Frame(frm)
        buttons.grid(row=8, column=0, columnspan=3, sticky="ew", **pad)
        self.run_button = ttk.Button(buttons, text=self._t("generate"), command=self.run)
        self.run_button.pack(side="left")
        ttk.Button(buttons, text=self._t("crop_editor"), command=self._open_crop_editor).pack(side="left", padx=8)
        ttk.Button(buttons, text=self._t("open_output"), command=lambda: self._open_folder(self.output_dir.get())).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text=self._t("open_report"), command=lambda: self._open_folder(self.work_dir.get())).pack(side="left")

        ttk.Label(frm, textvariable=self.status).grid(row=9, column=0, columnspan=3, sticky="w", **pad)

        progress_frame = ttk.Frame(frm)
        progress_frame.grid(row=10, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)
        ttk.Label(progress_frame, textvariable=self.progress_text, width=8, anchor="e").pack(side="left", padx=(8, 0))

        self.log = ScrolledText(frm, height=18, wrap="word")
        self.log.grid(row=11, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))
        self.log.insert("end", self._t("flow"))
        self.log.configure(state="disabled")

        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(11, weight=1)

    def _language_selector(self, parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.LabelFrame(parent, text=self._t("language"))
        for code, label in LANGUAGE_BUTTONS.items():
            selected = code == self.language.get()
            Button(
                frame,
                text=label,
                command=lambda c=code: self._set_language(c),
                relief="sunken" if selected else "raised",
                bg="#1f6feb" if selected else "#f0f0f0",
                fg="#ffffff" if selected else "#000000",
                activebackground="#388bfd" if selected else "#e6e6e6",
                padx=8,
                pady=2,
            ).pack(side="left", padx=3, pady=3)
        return frame

    def _set_language(self, code: str) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo(APP_TITLE, self._t("wait_running"))
            return
        if code not in TEXT or code == self.language.get():
            return
        self.language.set(code)
        self._build_ui()

    def _show_credits(self) -> None:
        win = Toplevel(self.root)
        win.title(self._t("credits_title"))
        win.transient(self.root)
        win.resizable(False, False)

        body = ttk.Frame(win, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=self._t("credits_title"), font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(body, text=self._t("credits_message"), justify="left", wraplength=360).pack(anchor="w", pady=(10, 12))
        self._credit_link_row(body, self._t("credits_instagram"), CREDIT_INSTAGRAM_URL).pack(anchor="w", pady=(0, 4))
        self._credit_link_row(body, self._t("credits_youtube"), CREDIT_YOUTUBE_URL).pack(anchor="w", pady=(0, 16))
        ttk.Button(body, text="OK", command=win.destroy).pack(anchor="e")

        win.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - win.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - win.winfo_height()) // 2)
        win.geometry(f"+{x}+{y}")
        win.grab_set()

    def _credit_link_row(self, parent: ttk.Frame, label_text: str, url: str) -> ttk.Frame:
        row = ttk.Frame(parent)
        ttk.Label(row, text=f"{label_text}:").pack(side="left")
        self._link_label(row, url, url).pack(side="left", padx=(4, 0))
        return row

    def _link_label(self, parent: ttk.Frame, text: str, url: str) -> ttk.Label:
        label = ttk.Label(parent, text=text, foreground="#0969da", cursor="hand2", font=("", 9, "underline"))
        label.bind("<Button-1>", lambda _event: self._open_url(url))
        return label

    def _open_url(self, url: str) -> None:
        try:
            if not webbrowser.open(url):
                raise RuntimeError("webbrowser.open returned False")
        except Exception:
            messagebox.showerror(APP_TITLE, self._t("open_link_error").format(url=url))

    def _path_row(self, parent: ttk.Frame, row: int, label: str, var: StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=10, pady=6)
        ttk.Button(parent, text=self._t("select"), command=lambda: self._choose_dir(var)).grid(row=row, column=2, sticky="e", padx=10, pady=6)

    def _file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        var: StringVar,
        help_text: str | None = None,
        filetypes: list[tuple[str, str]] | None = None,
    ) -> None:
        label_frame = ttk.Frame(parent)
        label_frame.grid(row=row, column=0, sticky="w", padx=10, pady=6)
        ttk.Label(label_frame, text=label).pack(side="left")
        if help_text:
            self._help_icon(label_frame, help_text).pack(side="left", padx=(4, 0))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=10, pady=6)
        ttk.Button(parent, text=self._t("select"), command=lambda: self._choose_file(var, filetypes)).grid(row=row, column=2, sticky="e", padx=10, pady=6)

    def _help_icon(self, parent: ttk.Frame, text: str) -> ttk.Label:
        icon = ttk.Label(parent, text="?", width=2, anchor="center", relief="solid", cursor="question_arrow")
        self._tooltips.append(Tooltip(icon, text))
        return icon

    def _choose_dir(self, var: StringVar) -> None:
        initial = var.get() if var.get() and Path(var.get()).exists() else str(Path.home())
        selected = filedialog.askdirectory(initialdir=initial)
        if selected:
            var.set(selected)

    def _choose_file(self, var: StringVar, filetypes: list[tuple[str, str]] | None = None) -> None:
        initial = var.get() if var.get() and Path(var.get()).exists() else str(Path.home())
        selected = filedialog.askopenfilename(initialdir=initial, filetypes=filetypes or [("All", "*.*")])
        if selected:
            var.set(selected)

    def _open_folder(self, value: str) -> None:
        path = Path(value)
        if not path.exists():
            messagebox.showwarning(APP_TITLE, self._t("folder_missing").format(path=path))
            return
        subprocess.Popen(["explorer", str(path)])

    def _open_crop_editor(self) -> None:
        cover_dir = Path(self.cover_dir.get())
        if not cover_dir.exists():
            messagebox.showwarning(APP_TITLE, self._t("crop_editor_missing"))
            return
        crop_path = Path(self.crop_json.get()) if self.crop_json.get().strip() else Path(__file__).resolve().parents[1] / "cover-crops.json"
        self.crop_json.set(str(crop_path))
        CropEditor(self.root, cover_dir, crop_path, self.language.get())

    def run(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        rom_dir = Path(self.rom_dir.get())
        cover_dir = Path(self.cover_dir.get())
        crop_json = Path(self.crop_json.get()) if self.crop_json.get().strip() else None
        map_csv = Path(self.map_csv.get()) if self.map_csv.get().strip() else None
        output_dir = Path(self.output_dir.get())
        work_base = Path(self.work_dir.get())

        missing = [name for name, path in ((self._t("rom_dir"), rom_dir), (self._t("cover_dir"), cover_dir)) if not path.exists()]
        if map_csv is not None and not map_csv.exists():
            missing.append(self._t("map_csv"))
        if missing:
            messagebox.showerror(APP_TITLE, self._t("invalid_folder") + ", ".join(missing))
            return
        output_dir.mkdir(parents=True, exist_ok=True)
        work_base.mkdir(parents=True, exist_ok=True)
        run_dir = work_base / datetime.now().strftime("run-%Y%m%d-%H%M%S")

        try:
            preview = max(0, int(self.preview_count.get()))
        except ValueError:
            preview = 16

        converter_args = [
            str(cover_dir),
            str(run_dir),
            "--rom-root",
            str(rom_dir),
            "--pak-out",
            str(output_dir),
            "--preview-count",
            str(preview),
        ]
        if crop_json is not None:
            converter_args.extend(["--crop-json", str(crop_json)])
        if map_csv is not None:
            converter_args.extend(["--map-csv", str(map_csv)])
        if not self.relative_names.get():
            converter_args.append("--exact-name-only")
        if self.relative_names.get() and self.match_variants.get():
            converter_args.append("--match-title-variants")

        self.run_button.configure(state="disabled")
        self._set_progress(0, self._t("generating"))
        self._append_log(self._t("new_generation"))
        display_cmd = ["edmd_bulk_convert_covers"] + converter_args
        self._append_log(" ".join(f'"{part}"' if " " in part else part for part in display_cmd) + "\n\n")

        language = self.language.get()
        self._worker = threading.Thread(target=self._run_converter, args=(converter_args, run_dir, language), daemon=True)
        self._worker.start()

    def _run_converter(self, converter_args: list[str], run_dir: Path, language: str) -> None:
        try:
            writer = QueueWriter(self._queue)
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                code = edmd_bulk_convert_covers.main(converter_args)
            if code == 0:
                status, summary = self._build_finished_summary(run_dir, language)
                self._queue.put(summary)
                self._queue.put(self._text_for(language, "report_ok").format(path=run_dir / "conversion-report.json"))
                self._queue.put("__PROGRESS_DONE__")
                self._queue.put(f"__STATUS__{status}")
            else:
                self._queue.put(self._text_for(language, "finished_with_code").format(code=code))
                self._queue.put(f"__STATUS__{self._text_for(language, 'process_error')}")
            self._queue.put("__DONE__")
        except Exception as exc:  # noqa: BLE001 - GUI should show unexpected errors.
            self._queue.put(self._text_for(language, "unexpected_error").format(error=exc))
            self._queue.put(f"__STATUS__{self._text_for(language, 'process_error')}")
            self._queue.put("__DONE__")

    def _build_finished_summary(self, run_dir: Path, language: str) -> tuple[str, str]:
        report_path = run_dir / "conversion-report.json"
        if not report_path.exists():
            return self._text_for(language, "ready"), self._text_for(language, "report_missing")

        report = json.loads(report_path.read_text(encoding="utf-8"))
        packs = report.get("packs", [])
        matched = int(report.get("matched_count", 0))
        unmatched_roms = int(report.get("unmatched_rom_count", 0))
        unmatched_images = int(report.get("unmatched_image_count", 0))
        status = self._text_for(language, "done_status").format(matched=matched, packs=len(packs))
        lines = [
            self._text_for(language, "done_header"),
            self._text_for(language, "associated").format(count=matched),
            self._text_for(language, "paks_generated").format(count=len(packs)),
            self._text_for(language, "roms_without_cover").format(count=unmatched_roms),
            self._text_for(language, "images_without_match").format(count=unmatched_images),
            self._text_for(language, "generated_files"),
        ]
        for pack in packs:
            lines.append(f"  {pack['letter']}.PAK - {pack['count']} {self._text_for(language, 'pack_cover_count')}")
        return status, "\n".join(lines) + "\n"

    def _handle_progress(self, line: str) -> None:
        try:
            phase, done_raw, total_raw = line.strip().split("|", 2)
            done = int(done_raw)
            total = max(1, int(total_raw))
        except ValueError:
            return

        if phase == "convert":
            percent = min(90, round(done * 90 / total))
            self._set_progress(percent, self._t("convert_status").format(percent=percent, done=done, total=total))
        elif phase == "pack":
            percent = 90 + min(10, round(done * 10 / total))
            self._set_progress(percent, self._t("pack_status").format(percent=percent, done=done, total=total))

    def _set_progress(self, percent: int, status: str | None = None) -> None:
        percent = max(0, min(100, percent))
        self.progress["value"] = percent
        self.progress_text.set(f"{percent}%")
        if status is not None:
            self.status.set(status)

    def _poll_log(self) -> None:
        try:
            while True:
                line = self._queue.get_nowait()
                if line == "__DONE__":
                    self.run_button.configure(state="normal")
                elif line.startswith("__STATUS__"):
                    self.status.set(line.removeprefix("__STATUS__"))
                elif line.startswith("__PROGRESS__"):
                    self._handle_progress(line.removeprefix("__PROGRESS__"))
                elif line == "__PROGRESS_DONE__":
                    self._set_progress(100)
                else:
                    self._append_log(line)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> int:
    root = Tk()
    try:
        root.call("tk", "scaling", 1.2)
    except Exception:
        pass
    CoverPackTool(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
