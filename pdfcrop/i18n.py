"""Tiny translation layer. Two languages: English and Spanish.

Usage: ``from .i18n import t`` then ``t("open_pdf")`` or
``t("status_page").format(n, total)`` for strings with placeholders.
"""

LANGUAGES = ("en", "es")
_lang = "en"

STRINGS = {
    # Sidebar / header
    "subtitle": {"en": "Crop images out of any PDF by hand",
                 "es": "Recorta imágenes de cualquier PDF a mano"},
    "open_pdf": {"en": "Open PDF  (Ctrl+O)", "es": "Abrir PDF  (Ctrl+O)"},
    "extract": {"en": "Extract data (text + prices)",
                "es": "Extraer datos (texto + precios)"},
    "load_csv": {"en": "Load label list (CSV)", "es": "Cargar lista (CSV)"},
    "goto": {"en": "Go to page:", "es": "Ir a página:"},
    "go": {"en": "Go", "es": "Ir"},
    "zoom": {"en": "Zoom", "es": "Zoom"},
    "search": {"en": "Search (Ctrl+F)", "es": "Buscar (Ctrl+F)"},
    "only_pending": {"en": "Only pending", "es": "Solo pendientes"},
    "only_price": {"en": "Only items with a price", "es": "Solo con precio"},
    "open_folder": {"en": "Open output folder", "es": "Abrir carpeta de salida"},
    "delete_crop": {"en": "Delete selected crop", "es": "Borrar recorte seleccionado"},
    "export_sql": {"en": "Export to SQL", "es": "Exportar a SQL"},
    "mode_crop": {"en": "✂  Crop mode  (drag to select)",
                  "es": "✂  Modo recorte  (arrastra para seleccionar)"},
    "mode_pan": {"en": "✋  Pan mode  (drag to move)",
                 "es": "✋  Modo mano  (arrastra para mover)"},
    "tip": {"en": ("Drag to crop. Switch to Pan mode (or hold Space) to move the\n"
                   "page. Wheel scrolls · Shift+wheel sideways · Ctrl+wheel zooms.\n"
                   "Ctrl+F searches; Enter jumps to that page."),
            "es": ("Arrastra para recortar. Cambia a Modo mano (o mantén Espacio)\n"
                   "para mover. Rueda = scroll · Shift+rueda = lateral · Ctrl+rueda\n"
                   "= zoom. Ctrl+F busca; Enter salta a esa página.")},

    # Counts
    "count_labels": {"en": "{0} done · {1} pending of {2}",
                     "es": "{0} hechos · {1} pendientes de {2}"},
    "count_crops": {"en": "{0} crops saved", "es": "{0} recortes guardados"},
    "count_shown": {"en": " · {0} shown", "es": " · {0} mostrados"},

    # Status bar
    "status_open_begin": {"en": "Open a PDF to begin.", "es": "Abre un PDF para empezar."},
    "empty_canvas": {"en": "Open a PDF (Ctrl+O) to start cropping",
                     "es": "Abre un PDF (Ctrl+O) para empezar a recortar"},
    "status_page": {"en": "Page {0} of {1}  ·  drag over the page to crop an image",
                    "es": "Página {0} de {1}  ·  arrastra sobre la página para recortar"},
    "status_extracting": {"en": "Extracting text from the PDF…",
                          "es": "Extrayendo texto del PDF…"},
    "status_extracting_page": {"en": "Extracting text… page {0}/{1}",
                               "es": "Extrayendo texto… página {0}/{1}"},
    "status_extracted": {"en": ("Extracted {0} key items · {1} look like prices. "
                                "Crops now auto-fill their label from nearby text."),
                         "es": ("Extraídos {0} datos clave · {1} parecen precios. "
                                "Los recortes ahora autollenan su etiqueta con el texto cercano.")},
    "status_small": {"en": "Selection too small — ignored",
                     "es": "Selección demasiado pequeña — ignorada"},
    "status_loaded_csv": {"en": "Loaded {0} labels from {1}",
                          "es": "Cargadas {0} etiquetas de {1}"},
    "status_saved": {"en": "Saved: {0}  ·  page {1}", "es": "Guardado: {0}  ·  página {1}"},
    "status_deleted": {"en": "Deleted crop {0}.", "es": "Recorte {0} borrado."},
    "status_no_page": {"en": "No page recorded for this item yet.",
                       "es": "Aún no hay página registrada para este ítem."},
    "status_nothing_delete": {"en": "Nothing to delete for this item.",
                              "es": "Nada que borrar para este ítem."},
    "status_invalid_page": {"en": "Invalid page number", "es": "Número de página inválido"},
    "sel_next": {"en": "Next crop: {0} — {1}", "es": "Siguiente recorte: {0} — {1}"},

    # Message boxes
    "mb_no_pdf_t": {"en": "No PDF open", "es": "No hay PDF abierto"},
    "mb_no_pdf_m": {"en": "Open a PDF first, then extract its data.",
                    "es": "Abre un PDF primero y luego extrae sus datos."},
    "mb_open_err": {"en": "Could not open PDF", "es": "No se pudo abrir el PDF"},
    "mb_extract_err": {"en": "Extraction failed", "es": "Falló la extracción"},
    "mb_csv_err": {"en": "Could not read CSV", "es": "No se pudo leer el CSV"},
    "mb_render_err": {"en": "Render error", "es": "Error al renderizar"},
    "mb_render_page": {"en": "Could not render page {0}\n{1}",
                       "es": "No se pudo renderizar la página {0}\n{1}"},
    "mb_delete_t": {"en": "Delete crop", "es": "Borrar recorte"},
    "mb_delete_m": {"en": "Delete crop '{0}'? The PNG is removed too.",
                    "es": "¿Borrar el recorte '{0}'? También se elimina el PNG."},
    "mb_export_none_t": {"en": "Nothing to export", "es": "Nada que exportar"},
    "mb_export_none_m": {"en": "You haven't saved any crops yet.",
                         "es": "Todavía no has guardado ningún recorte."},
    "mb_export_ok_t": {"en": "SQL exported", "es": "SQL exportado"},
    "mb_export_ok_m": {"en": "{0} rows written to:\n{1}",
                       "es": "{0} filas escritas en:\n{1}"},
    "mb_export_err": {"en": "Could not write SQL file", "es": "No se pudo escribir el SQL"},

    # Crop dialog
    "dlg_title": {"en": "Save crop", "es": "Guardar recorte"},
    "dlg_confirm": {"en": "Confirm this crop", "es": "Confirma este recorte"},
    "dlg_selection": {"en": "Selection: {0} x {1} px  ·  page {2}",
                      "es": "Selección: {0} x {1} px  ·  página {2}"},
    "f_id": {"en": "ID (optional)", "es": "ID (opcional)"},
    "f_label": {"en": "Label", "es": "Etiqueta"},
    "f_price": {"en": "Price (optional)", "es": "Precio (opcional)"},
    "f_category": {"en": "Category (optional)", "es": "Categoría (opcional)"},
    "save": {"en": "Save", "es": "Guardar"},
    "cancel": {"en": "Cancel", "es": "Cancelar"},
    "dlg_exists": {"en": "⚠  A crop with this ID exists — it will be overwritten.",
                   "es": "⚠  Ya existe un recorte con este ID — se sobrescribirá."},
    "dlg_not_in_list": {"en": "·  ID not in the loaded list",
                        "es": "·  El ID no está en la lista cargada"},
    "err_nolabel_t": {"en": "Missing label", "es": "Falta la etiqueta"},
    "err_nolabel_m": {"en": "Enter a label for this crop.",
                      "es": "Escribe una etiqueta para este recorte."},
    "err_price_t": {"en": "Invalid price", "es": "Precio inválido"},
    "err_price_m": {"en": "Price must be a number, e.g. 199.90 (or leave it empty).",
                    "es": "El precio debe ser un número, ej. 199.90 (o déjalo vacío)."},
    "err_img_t": {"en": "Could not save image", "es": "No se pudo guardar la imagen"},
}


def set_lang(lang):
    global _lang
    if lang in LANGUAGES:
        _lang = lang


def get_lang():
    return _lang


def t(key):
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(_lang) or entry.get("en") or key
