"""PDF Crop Studio — main Tkinter application."""
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from .dialog import CropDialog
from .labels import load_labels
from .pdfdoc import PdfDocument
from .store import Project
from .theme import (
    ACCENT, ACCENT2, BG, BORDER, CANVAS_BG, DANGER, FONT, FONT_H, FONT_MONO,
    FONT_SB, FONT_TITLE, MUTED, PANEL, PANEL2, SUCCESS, TEXT,
)

RENDER_ZOOM = 3.0  # page render scale; higher = crisper crops, more memory


def natural_sort_key(name):
    nums = re.findall(r"\d+", name)
    return int(nums[0]) if nums else 0


class ExtractorApp:
    def __init__(self, root, pdf_path=None):
        self.root = root

        self.doc = None
        self.project = None
        self.labels = []
        self.label_index = {}  # id -> label entry

        self.current_idx = 0
        self.zoom = 1.0
        self.orig = None
        self.img_w = self.img_h = 1
        self.tk_img = None

        self.start_cx = self.start_cy = None
        self.cur_cx = self.cur_cy = None
        self.rect_item = self.dim_item = self.dim_bg_item = None

        self.pending_id = None
        self.pending_label = None
        self.list_rows = []  # parallel to listbox entries

        self.filter_pending_only = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()

        self._build_ui()

        if pdf_path and os.path.exists(pdf_path):
            self._open_pdf(pdf_path)
        else:
            self._show_empty_state()

        self.root.after(50, self._focus_canvas)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _btn(self, parent, text, command, primary=False):
        if primary:
            b = tk.Button(parent, text=text, command=command, bg=ACCENT, fg=CANVAS_BG,
                          font=FONT, relief="flat", activebackground=ACCENT2,
                          cursor="hand2", bd=0, padx=12, pady=5)
        else:
            b = tk.Button(parent, text=text, command=command, bg=PANEL2, fg=TEXT,
                          font=FONT, relief="flat", activebackground=PANEL,
                          cursor="hand2", bd=0, padx=12, pady=5, highlightthickness=1,
                          highlightbackground=BORDER)
        b.bind("<Enter>", lambda e: b.config(bg=ACCENT2 if primary else BORDER))
        b.bind("<Leave>", lambda e: b.config(bg=ACCENT if primary else PANEL2))
        return b

    def _build_ui(self):
        self.root.configure(bg=BG)
        self.root.geometry("1320x860")
        self.root.minsize(1000, 640)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)

        self._build_sidebar(main)
        self._build_canvas_area(main)
        self._build_statusbar(self.root)

        self.root.bind("<Prior>", lambda e: self.goto_page(self.current_idx - 1))
        self.root.bind("<Next>", lambda e: self.goto_page(self.current_idx + 1))
        self.root.bind("<Control-equal>", lambda e: self._zoom(1.25))
        self.root.bind("<Control-minus>", lambda e: self._zoom(0.8))
        self.root.bind("<Control-o>", lambda e: self._pick_pdf())
        self.root.bind("<Escape>", self._cancel_sel)
        self.root.bind("<Control-f>", self._focus_search)
        self.root.bind("<Control-F>", self._focus_search)

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=PANEL, width=330, bd=0, highlightthickness=0)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)

        header = tk.Frame(side, bg=PANEL)
        header.pack(fill="x", padx=18, pady=(18, 10))
        tk.Label(header, text="PDF Crop Studio", bg=PANEL, fg=ACCENT,
                 font=FONT_TITLE).pack(anchor="w")
        tk.Label(header, text="Crop images out of any PDF by hand", bg=PANEL, fg=MUTED,
                 font=FONT_SB).pack(anchor="w")

        openrow = tk.Frame(side, bg=PANEL)
        openrow.pack(fill="x", padx=18, pady=(0, 8))
        self._btn(openrow, "Open PDF  (Ctrl+O)", self._pick_pdf, primary=True).pack(
            fill="x", pady=(0, 6))
        self._btn(openrow, "Load label list (CSV)", self._pick_csv).pack(fill="x")

        nav = tk.Frame(side, bg=PANEL)
        nav.pack(fill="x", padx=18, pady=(6, 6))
        self._btn(nav, "«", lambda: self.goto_page(0)).pack(side="left")
        self._btn(nav, "‹", lambda: self.goto_page(self.current_idx - 1)).pack(
            side="left", padx=(6, 0))
        self.page_lbl = tk.Label(nav, text="—", bg=PANEL, fg=TEXT, font=FONT, width=12)
        self.page_lbl.pack(side="left", fill="x", expand=True)
        self._btn(nav, "›", lambda: self.goto_page(self.current_idx + 1)).pack(side="right")
        self._btn(nav, "»", lambda: self.goto_page(self._page_count() - 1)).pack(
            side="right", padx=(0, 6))

        pgframe = tk.Frame(side, bg=PANEL)
        pgframe.pack(fill="x", padx=18, pady=(0, 12))
        tk.Label(pgframe, text="Go to page:", bg=PANEL, fg=MUTED, font=FONT_SB).pack(side="left")
        self.goto_entry = tk.Entry(pgframe, width=5, font=FONT_MONO, bg=PANEL2, fg=TEXT,
                                   insertbackground=TEXT, relief="flat", highlightthickness=1,
                                   highlightbackground=BORDER, justify="center")
        self.goto_entry.pack(side="left", padx=6)
        self.goto_entry.bind("<Return>", self._goto_entry)
        self._btn(pgframe, "Go", self._goto_entry).pack(side="left", padx=4)

        zoom_frame = tk.Frame(side, bg=PANEL)
        zoom_frame.pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(zoom_frame, text="Zoom", bg=PANEL, fg=MUTED, font=FONT_SB).pack(side="left")
        self._btn(zoom_frame, "－", lambda: self._zoom(0.8)).pack(side="right")
        self.zoom_lbl = tk.Label(zoom_frame, text="100%", bg=PANEL, fg=TEXT, font=FONT, width=8)
        self.zoom_lbl.pack(side="right", padx=6)
        self._btn(zoom_frame, "＋", lambda: self._zoom(1.25)).pack(side="right")

        tk.Label(side, text="Search (Ctrl+F)", bg=PANEL, fg=MUTED, font=FONT_SB).pack(
            anchor="w", padx=18, pady=(0, 2))
        search_frame = tk.Frame(side, bg=PANEL)
        search_frame.pack(fill="x", padx=18, pady=(0, 6))
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=FONT,
                                     bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                                     highlightthickness=1, highlightbackground=ACCENT)
        self.search_entry.pack(fill="x", side="left", expand=True, ipady=3)
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.search_entry.bind("<Return>", self._jump_to_row_page)
        self.search_entry.bind("<Down>", lambda e: (self._move_selection(1), "break")[1])
        self.search_entry.bind("<Up>", lambda e: (self._move_selection(-1), "break")[1])
        self.search_entry.bind("<Escape>", self._clear_search)

        filt = tk.Frame(side, bg=PANEL)
        filt.pack(fill="x", padx=18, pady=(0, 2))
        tk.Checkbutton(filt, text="Only pending", variable=self.filter_pending_only, bg=PANEL,
                       fg=MUTED, selectcolor=PANEL2, activebackground=PANEL,
                       activeforeground=TEXT, font=FONT_SB, bd=0, command=self._refresh_list,
                       highlightthickness=0).pack(side="left")

        count_row = tk.Frame(side, bg=PANEL)
        count_row.pack(fill="x", padx=18, pady=(0, 8))
        self.count_lbl = tk.Label(count_row, text="", bg=PANEL, fg=ACCENT, font=FONT_SB,
                                  justify="left")
        self.count_lbl.pack(side="left")

        # Bottom-anchored blocks (packed before the list so the list shrinks
        # instead of covering them).
        bottom = tk.Frame(side, bg=PANEL)
        bottom.pack(side="bottom", fill="x", padx=18, pady=(8, 18))
        self._btn(bottom, "Open output folder", self._open_output_folder).pack(fill="x")
        self._btn(bottom, "Delete selected crop", self._delete_selected).pack(
            fill="x", pady=(6, 0))

        self.preview_thumb = tk.Label(side, bg=PANEL, bd=0)
        self.preview_thumb.pack(side="bottom", fill="x", padx=18, pady=(0, 12))

        tk.Label(side, text="Drag over the page to crop. With a CSV loaded, pick an\n"
                            "item first to pre-fill its label. Ctrl+F searches; Enter\n"
                            "jumps to that page. ✓ = done · · = pending.",
                 bg=PANEL, fg=MUTED, font=FONT_SB, justify="left").pack(
            side="bottom", fill="x", padx=18, pady=(0, 12))

        list_wrap = tk.Frame(side, bg=PANEL)
        list_wrap.pack(side="top", fill="both", expand=True, padx=18, pady=(0, 8))
        sb = tk.Scrollbar(list_wrap, bg=PANEL, troughcolor=PANEL, bd=0, highlightthickness=0)
        sb.pack(side="right", fill="y")
        self.plist = tk.Listbox(list_wrap, bg=PANEL, fg=TEXT, selectbackground=ACCENT,
                                selectforeground=CANVAS_BG, font=FONT_SB, bd=0,
                                highlightthickness=0, activestyle="none", yscrollcommand=sb.set)
        self.plist.pack(side="left", fill="both", expand=True)
        sb.config(command=self.plist.yview, bg=PANEL)
        self.plist.bind("<<ListboxSelect>>", self._on_list_select)
        self.plist.bind("<Double-Button-1>", self._jump_to_row_page)
        self.plist.bind("<Delete>", lambda e: self._delete_selected())

    def _build_canvas_area(self, parent):
        wrap = tk.Frame(parent, bg=CANVAS_BG)
        wrap.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(wrap, bg=CANVAS_BG, bd=0, highlightthickness=0, cursor="cross")
        self.canvas.pack(side="left", fill="both", expand=True)

        xsb = tk.Scrollbar(wrap, orient="horizontal", bg=PANEL, troughcolor=PANEL, bd=0,
                           highlightthickness=0)
        ysb = tk.Scrollbar(wrap, orient="vertical", bg=PANEL, troughcolor=PANEL, bd=0,
                           highlightthickness=0)
        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        self.canvas.config(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
        xsb.config(command=self.canvas.xview, bg=PANEL)
        ysb.config(command=self.canvas.yview, bg=PANEL)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_wheel_h)
        self.canvas.bind("<Configure>", lambda e: self._update_scroll())

    def _build_statusbar(self, parent):
        bar = tk.Frame(parent, bg=PANEL2, height=26, bd=0)
        bar.pack(side="bottom", fill="x")
        self.status_lbl = tk.Label(bar, text="Open a PDF to begin.", bg=PANEL2, fg=MUTED,
                                   font=FONT_SB, anchor="w")
        self.status_lbl.pack(side="left", padx=12, pady=3)
        self.sel_lbl = tk.Label(bar, text="", bg=PANEL2, fg=ACCENT, font=FONT_SB)
        self.sel_lbl.pack(side="right", padx=12, pady=3)

    def _focus_canvas(self):
        self.canvas.focus_set()

    # ------------------------------------------------------------------
    # Opening PDFs and label lists
    # ------------------------------------------------------------------

    def _pick_pdf(self, _=None):
        path = filedialog.askopenfilename(
            title="Open a PDF", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if path:
            self._open_pdf(path)

    def _open_pdf(self, path):
        try:
            doc = PdfDocument(path, render_zoom=RENDER_ZOOM)
        except Exception as e:
            messagebox.showerror("Could not open PDF", str(e))
            return
        if self.doc:
            self.doc.close()
        self.doc = doc

        stem = os.path.splitext(os.path.basename(path))[0]
        output_dir = os.path.join(os.path.dirname(os.path.abspath(path)), f"{stem}_crops")
        project = Project.load(output_dir)
        if project is None:
            project = Project(output_dir, source_pdf=path, render_zoom=RENDER_ZOOM)
        else:
            project.source_pdf = path
        self.project = project

        self.current_idx = 0
        self.root.title(f"PDF Crop Studio — {os.path.basename(path)}")
        self._refresh_list()
        self.load_image()

    def _pick_csv(self):
        path = filedialog.askopenfilename(
            title="Load a label list (CSV)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.labels = load_labels(path)
        except Exception as e:
            messagebox.showerror("Could not read CSV", str(e))
            return
        self.label_index = {row["id"]: row for row in self.labels if row["id"]}
        self._set_status(f"Loaded {len(self.labels)} labels from {os.path.basename(path)}")
        self._refresh_list()

    def _page_count(self):
        return self.doc.page_count if self.doc else 0

    # ------------------------------------------------------------------
    # Sidebar list
    # ------------------------------------------------------------------

    def _refresh_list(self):
        self.plist.delete(0, "end")
        self.list_rows = []
        q = self.search_var.get().strip().lower()

        if self.labels:
            self._populate_from_labels(q)
        else:
            self._populate_from_crops(q)

        if q and self.plist.size() > 0:
            self.plist.selection_clear(0, "end")
            self.plist.selection_set(0)
            self.plist.see(0)
            self._on_list_select(move_focus_to_canvas=False)

    def _populate_from_labels(self, q):
        done_ids = {r.get("id") for r in self.project.crops.values() if r.get("id")} if self.project else set()
        done = pending = 0
        for row in self.labels:
            rid, label = row["id"], row["label"]
            is_done = rid in done_ids
            done += is_done
            pending += not is_done
            if is_done and self.filter_pending_only.get():
                continue
            if q and q not in (rid or "").lower() and q not in (label or "").lower():
                continue
            icon = "✓" if is_done else "·"
            self.plist.insert("end", f"{icon} {rid}  {label}")
            self.plist.itemconfig("end", {"foreground": MUTED if is_done else TEXT})
            self.list_rows.append({"kind": "label", "id": rid, "label": label,
                                   "category": row.get("category")})
        self.count_lbl.config(text=f"{done} done · {pending} pending of {len(self.labels)}")

    def _populate_from_crops(self, q):
        crops = sorted(self.project.crops.values(), key=lambda r: (r.get("page") or 0, r["key"])) if self.project else []
        shown = 0
        for r in crops:
            label = r.get("label") or r["key"]
            if q and q not in label.lower() and q not in (r.get("id") or "").lower():
                continue
            self.plist.insert("end", f"✓ p{r.get('page')}  {label}")
            self.plist.itemconfig("end", {"foreground": TEXT})
            self.list_rows.append({"kind": "crop", "key": r["key"], "label": label,
                                   "page": r.get("page")})
            shown += 1
        total = len(crops)
        self.count_lbl.config(text=f"{total} crops saved" + (f" · {shown} shown" if q else ""))

    def _current_row(self):
        sel = self.plist.curselection()
        if not sel or sel[0] >= len(self.list_rows):
            return None
        return self.list_rows[sel[0]]

    def _on_list_select(self, _=None, move_focus_to_canvas=True):
        row = self._current_row()
        if not row:
            return
        if row["kind"] == "label":
            self.pending_id = row["id"]
            self.pending_label = row["label"]
            self.sel_lbl.config(text=f"Next crop: {row['id']} — {row['label']}")
            if move_focus_to_canvas:
                self.canvas.focus_set()
        else:
            self._show_thumb(row["key"])

    def _move_selection(self, delta):
        total = self.plist.size()
        if not total:
            return
        sel = self.plist.curselection()
        idx = sel[0] if sel else -1
        idx = max(0, min(total - 1, idx + delta))
        self.plist.selection_clear(0, "end")
        self.plist.selection_set(idx)
        self.plist.see(idx)
        self._on_list_select(move_focus_to_canvas=False)

    def _jump_to_row_page(self, _=None):
        row = self._current_row()
        if not row:
            return
        pg = None
        if row["kind"] == "crop":
            pg = row.get("page")
        elif self.project:
            for r in self.project.crops.values():
                if r.get("id") == row.get("id"):
                    pg = r.get("page")
                    break
        if not pg:
            self._set_status("No page recorded for this item yet.")
            return
        self.goto_page(pg - 1)

    def _delete_selected(self):
        row = self._current_row()
        if not row or not self.project:
            return
        key = row.get("key")
        if not key and row.get("id"):
            for r in self.project.crops.values():
                if r.get("id") == row["id"]:
                    key = r["key"]
                    break
        if not key:
            self._set_status("Nothing to delete for this item.")
            return
        label = self.project.crops.get(key, {}).get("label", key)
        if not messagebox.askyesno("Delete crop", f"Delete crop '{label}'? The PNG is removed too."):
            return
        self.project.remove_crop(key)
        self.preview_thumb.config(image="", text="")
        self._refresh_list()
        self._set_status(f"Deleted crop {label}.")

    def _focus_search(self, _=None):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        return "break"

    def _clear_search(self, _=None):
        self.search_var.set("")
        self.canvas.focus_set()

    # ------------------------------------------------------------------
    # Page rendering / navigation
    # ------------------------------------------------------------------

    def _show_empty_state(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_reqwidth() // 2 or 400, 300, fill=MUTED, font=FONT_H,
            text="Open a PDF (Ctrl+O) to start cropping", anchor="center")

    def load_image(self):
        if not self.doc:
            return
        try:
            self.orig = self.doc.render(self.current_idx)
        except Exception as e:
            messagebox.showerror("Render error", f"Could not render page {self.current_idx + 1}\n{e}")
            return
        self.img_w, self.img_h = self.orig.size
        self._fit_zoom()
        self._render()
        n, total = self.current_idx + 1, self._page_count()
        self.page_lbl.config(text=f" {n} / {total} ")
        self._set_status(f"Page {n} of {total}  ·  drag over the page to crop an image")

    def _fit_zoom(self):
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        z = min(cw / self.img_w, ch / self.img_h)
        self.zoom = max(0.05, min(z, 1.0))

    def _render(self):
        if self.orig is None:
            return
        dw = max(1, int(self.img_w * self.zoom))
        dh = max(1, int(self.img_h * self.zoom))
        disp = self.orig.resize((dw, dh), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, dw, dh))
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.zoom_lbl.config(text=f"{int(self.zoom * 100)}%")
        self._cancel_sel()

    def goto_page(self, idx):
        if not (0 <= idx < self._page_count()):
            return
        self.current_idx = idx
        self.load_image()

    def _goto_entry(self, _=None):
        try:
            n = int(self.goto_entry.get())
        except ValueError:
            self._set_status("Invalid page number")
            return
        self.goto_page(n - 1)
        self.goto_entry.delete(0, "end")

    def _zoom(self, factor):
        self.zoom = max(0.05, min(self.zoom * factor, 8.0))
        self._render()

    def _on_wheel(self, e):
        if e.state & 0x4:
            self._on_wheel_h(e)
            return
        self.zoom = min(self.zoom * 1.1, 8.0) if e.delta > 0 else max(self.zoom / 1.1, 0.05)
        self._zoom_at(e.x, e.y)

    def _on_wheel_h(self, e):
        self.canvas.xview_scroll(int(-e.delta / 120), "units")

    def _zoom_at(self, cx, cy):
        if self.orig is None:
            return
        img_x = self.canvas.canvasx(cx) / self.zoom
        img_y = self.canvas.canvasy(cy) / self.zoom
        self._render()
        dw = self.img_w * self.zoom
        dh = self.img_h * self.zoom
        frac_x = max(0, min(1, (img_x * self.zoom - cx) / dw)) if dw else 0
        frac_y = max(0, min(1, (img_y * self.zoom - cy) / dh)) if dh else 0
        self.canvas.xview_moveto(frac_x)
        self.canvas.yview_moveto(frac_y)

    def _update_scroll(self):
        if self.orig is not None:
            self.canvas.config(scrollregion=(0, 0, int(self.img_w * self.zoom),
                                             int(self.img_h * self.zoom)))

    # ------------------------------------------------------------------
    # Drag-to-crop
    # ------------------------------------------------------------------

    def _on_press(self, e):
        if self.orig is None:
            return
        self.start_cx = self.canvas.canvasx(e.x)
        self.start_cy = self.canvas.canvasy(e.y)
        self.cur_cx, self.cur_cy = self.start_cx, self.start_cy
        self._draw_rect()

    def _on_drag(self, e):
        if self.start_cx is None:
            return
        self.cur_cx = self.canvas.canvasx(e.x)
        self.cur_cy = self.canvas.canvasy(e.y)
        self._draw_rect()

    def _draw_rect(self):
        x0, y0 = self.start_cx, self.start_cy
        x1, y1 = self.cur_cx, self.cur_cy
        if self.rect_item is None:
            self.rect_item = self.canvas.create_rectangle(x0, y0, x1, y1, outline=ACCENT,
                                                          width=2, dash=(6, 4))
            self.dim_bg_item = self.canvas.create_rectangle(x0, y0, x0 + 140, y0 + 22,
                                                            fill=CANVAS_BG, outline=ACCENT)
            self.dim_item = self.canvas.create_text(x0 + 6, y0 + 11, anchor="w", fill=TEXT,
                                                    font=FONT_SB, text="")
        else:
            self.canvas.coords(self.rect_item, x0, y0, x1, y1)
        ix = int(abs(x1 - x0) / self.zoom)
        iy = int(abs(y1 - y0) / self.zoom)
        top, left = min(y0, y1), min(x0, x1)
        self.canvas.coords(self.dim_bg_item, left, top, left + 140, top + 22)
        self.canvas.coords(self.dim_item, left + 6, top + 11)
        self.canvas.itemconfig(self.dim_item, text=f"{ix} x {iy} px")
        for item in (self.rect_item, self.dim_bg_item, self.dim_item):
            self.canvas.tag_raise(item)

    def _cancel_sel(self, _=None):
        self.start_cx = self.start_cy = self.cur_cx = self.cur_cy = None
        for item in (self.rect_item, self.dim_item, self.dim_bg_item):
            if item is not None:
                self.canvas.delete(item)
        self.rect_item = self.dim_item = self.dim_bg_item = None

    def _on_release(self, e):
        if self.start_cx is None or self.orig is None:
            return
        x0 = min(self.start_cx, self.cur_cx) / self.zoom
        y0 = min(self.start_cy, self.cur_cy) / self.zoom
        x1 = max(self.start_cx, self.cur_cx) / self.zoom
        y1 = max(self.start_cy, self.cur_cy) / self.zoom
        ix0, iy0 = max(0, int(x0)), max(0, int(y0))
        ix1, iy1 = min(self.img_w, int(x1)), min(self.img_h, int(y1))
        self._cancel_sel()
        if ix1 - ix0 < 20 or iy1 - iy0 < 20:
            self._set_status("Selection too small — ignored")
            return
        crop = self.orig.crop((ix0, iy0, ix1, iy1))
        page = self.current_idx + 1
        dlg = CropDialog(self.root, crop, self, page, (ix0, iy0, ix1, iy1))
        self.root.wait_window(dlg)
        if dlg.result:
            key = dlg.result
            self._refresh_list()
            rec = self.project.crops[key]
            self._set_status(f"Saved: {rec['label']}  ·  page {page}")
            self._show_thumb(key)
            self.pending_id = self.pending_label = None
            self.sel_lbl.config(text="")

    def _show_thumb(self, key):
        try:
            im = Image.open(self.project.image_path(key))
            im.thumbnail((294, 200))
            self._thumb = ImageTk.PhotoImage(im)
            self.preview_thumb.config(image=self._thumb, text="")
        except Exception:
            pass

    # ------------------------------------------------------------------

    def _open_output_folder(self):
        if not self.project:
            return
        folder = self.project.output_dir
        os.makedirs(folder, exist_ok=True)
        try:
            os.startfile(folder)  # Windows
        except AttributeError:
            import subprocess
            import sys
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", folder])

    def _set_status(self, text):
        self.status_lbl.config(text=text)
