"""The confirm-and-save dialog shown after you drag a crop rectangle."""
import os
import tkinter as tk
from tkinter import messagebox

from PIL import ImageTk

from .i18n import t
from .theme import (
    ACCENT, ACCENT2, BORDER, CANVAS_BG, DANGER, FONT, FONT_H, FONT_MONO,
    FONT_SB, MUTED, PANEL, PANEL2, SUCCESS, TEXT,
)


class CropDialog(tk.Toplevel):
    def __init__(self, master, crop_img, app, page, bbox_px,
                 suggested_label=None, suggested_price=None, suggested_id=None):
        super().__init__(master)
        self.app = app
        self.crop_img = crop_img
        self.page = page
        self.bbox_px = bbox_px  # (ix0, iy0, ix1, iy1) in original page pixels
        self.suggested_label = suggested_label
        self.suggested_price = suggested_price
        self.suggested_id = suggested_id
        self.result = None
        self.configure(bg=PANEL)
        self.title(t("dlg_title"))
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        w, h = crop_img.size

        tk.Label(self, text=t("dlg_confirm"), bg=PANEL, fg=TEXT, font=FONT_H).grid(
            row=0, column=0, columnspan=2, padx=20, pady=(16, 4), sticky="w")
        tk.Label(self, text=t("dlg_selection").format(w, h, page), bg=PANEL,
                 fg=MUTED, font=FONT_SB).grid(row=1, column=0, columnspan=2, padx=20,
                                              pady=(0, 8), sticky="w")

        prev_w = 300
        prev_h = min(int(h * prev_w / w) if w else 100, 380)
        preview = crop_img.copy()
        preview.thumbnail((prev_w, prev_h))
        self.tk_prev = ImageTk.PhotoImage(preview)
        tk.Label(self, image=self.tk_prev, bg=CANVAS_BG, bd=0, highlightthickness=1,
                 highlightbackground=BORDER).grid(row=2, column=0, rowspan=7,
                                                  padx=(20, 12), pady=4, sticky="n")

        form = tk.Frame(self, bg=PANEL)
        form.grid(row=2, column=1, padx=(0, 20), pady=4, sticky="n")

        def _field(label_text):
            tk.Label(form, text=label_text, bg=PANEL, fg=MUTED, font=FONT_SB).pack(anchor="w")
            var = tk.StringVar()
            entry = tk.Entry(form, textvariable=var, font=FONT_MONO, width=26,
                             bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                             highlightthickness=1, highlightbackground=ACCENT,
                             highlightcolor=ACCENT)
            entry.pack(fill="x", pady=(2, 8))
            return var, entry

        self.id_var, id_entry = _field(t("f_id"))
        self.id_var.set(app.pending_id or suggested_id or "")

        self.match_status = tk.StringVar()
        self.match_lbl = tk.Label(form, textvariable=self.match_status, bg=PANEL,
                                  fg=SUCCESS, font=FONT_SB, wraplength=230, justify="left")
        self.match_lbl.pack(anchor="w", pady=(0, 8))

        self.label_var, label_entry = _field(t("f_label"))
        self.label_var.set(app.pending_label or suggested_label or "")
        self.price_var, _ = _field(t("f_price"))
        if suggested_price is not None:
            self.price_var.set(_fmt_price(suggested_price))
        self.category_var, _ = _field(t("f_category"))

        btns = tk.Frame(self, bg=PANEL)
        btns.grid(row=9, column=0, columnspan=2, padx=20, pady=(8, 16), sticky="ew")
        self.save_btn = tk.Button(btns, text=t("save"), command=self._save, bg=ACCENT,
                                  fg=CANVAS_BG, font=FONT_H, relief="flat",
                                  activebackground=ACCENT2, cursor="hand2", width=12, bd=0)
        self.save_btn.pack(side="left", padx=(0, 8))
        tk.Button(btns, text=t("cancel"), command=self.destroy, bg=PANEL2, fg=TEXT,
                  font=FONT, relief="flat", activebackground=PANEL, cursor="hand2",
                  width=10, bd=0, highlightthickness=1,
                  highlightbackground=BORDER).pack(side="left")

        self.id_var.trace_add("write", self._on_id_change)
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())

        # Focus the first empty relevant field.
        (label_entry if self.label_var.get() == "" and self.id_var.get() else id_entry).focus_set()
        self._on_id_change()

    def _on_id_change(self, *_):
        cid = self.id_var.get().strip()
        match = self.app.label_index.get(cid) if cid else None
        existing = self.app.project.crops.get(cid) if cid else None

        if existing:
            self.match_status.set(t("dlg_exists"))
            self.match_lbl.config(fg=DANGER)
        elif match:
            self.match_status.set("✓  " + (match.get("label") or ""))
            self.match_lbl.config(fg=SUCCESS)
            if not self.label_var.get() and match.get("label"):
                self.label_var.set(match["label"])
            if not self.category_var.get() and match.get("category"):
                self.category_var.set(match["category"])
        elif cid and self.app.label_index:
            self.match_status.set(t("dlg_not_in_list"))
            self.match_lbl.config(fg=MUTED)
        else:
            self.match_status.set("")

    def _save(self):
        cid = self.id_var.get().strip()
        label = self.label_var.get().strip()
        category = self.category_var.get().strip()
        price_txt = self.price_var.get().strip()

        if not label:
            messagebox.showerror(t("err_nolabel_t"), t("err_nolabel_m"), parent=self)
            return
        price = None
        if price_txt:
            price = _parse_price_field(price_txt)
            if price is None:
                messagebox.showerror(t("err_price_t"), t("err_price_m"), parent=self)
                return

        key = self.app.project.next_key(preferred=cid or None)
        ix0, iy0, ix1, iy1 = self.bbox_px
        img_w, img_h = self.app.img_w, self.app.img_h
        bbox_norm = {
            "x0": round(ix0 / img_w, 5),
            "y0": round(iy0 / img_h, 5),
            "x1": round(ix1 / img_w, 5),
            "y1": round(iy1 / img_h, 5),
        }

        out = self.app.project.image_path(key)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            self.crop_img.save(out)
        except OSError as e:
            messagebox.showerror(t("err_img_t"), str(e), parent=self)
            return

        record = {
            "key": key,
            "id": cid or None,
            "label": label,
            "category": category or None,
            "price": price,
            "page": self.page,
            "bbox_norm": bbox_norm,
            "bbox_px": {"x0": ix0, "y0": iy0, "x1": ix1, "y1": iy1},
            "width": ix1 - ix0,
            "height": iy1 - iy0,
            "file": os.path.relpath(out, self.app.project.output_dir).replace("\\", "/"),
            "source_pdf": os.path.basename(self.app.project.source_pdf or ""),
        }
        self.app.project.add_crop(key, record)
        self.result = key
        self.destroy()


def _fmt_price(value):
    """Show a price without a trailing .0 for whole numbers."""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def _parse_price_field(text):
    """Parse the price the user typed. Returns a float or None if invalid."""
    cleaned = text.strip().lstrip("$€£¥ ").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None
