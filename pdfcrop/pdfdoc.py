"""Render PDF pages to PIL images with PyMuPDF (fitz).

Pages are rendered on demand at a configurable zoom and cached, so navigating
back and forth stays instant without pre-exporting every page to disk.
"""
from collections import OrderedDict

try:
    import fitz  # PyMuPDF
except ImportError as e:  # pragma: no cover - handled at startup
    raise ImportError(
        "PyMuPDF is required. Install it with:  pip install pymupdf"
    ) from e

from PIL import Image


class PdfDocument:
    """A single open PDF, rendering pages to RGB PIL images on demand."""

    def __init__(self, path, render_zoom=3.0, cache_size=6):
        self.path = path
        self.render_zoom = render_zoom
        self._doc = fitz.open(path)
        self._cache = OrderedDict()  # page_index -> (zoom, PIL.Image)
        self._cache_size = cache_size

    @property
    def page_count(self):
        return self._doc.page_count

    def render(self, index, zoom=None):
        """Return the page at ``index`` (0-based) as an RGB PIL image."""
        zoom = self.render_zoom if zoom is None else zoom
        cached = self._cache.get(index)
        if cached and cached[0] == zoom:
            self._cache.move_to_end(index)
            return cached[1]

        page = self._doc.load_page(index)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        self._cache[index] = (zoom, img)
        self._cache.move_to_end(index)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return img

    def close(self):
        try:
            self._doc.close()
        except Exception:
            pass
