"""Optional OCR fallback using the OCR engine built into Windows 10/11.

Many PDFs (scans, flattened designs, catalog rips) have no text layer at all,
so there is nothing for `extract.py` to read. When the `winocr` package is
installed (Windows only), we render the page/region to an image and let the
system OCR read it instead. No cloud, no extra downloads — it uses the
language packs already installed in Windows.
"""
import re

from PIL import ImageOps

try:
    import winocr
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def available():
    return _AVAILABLE


# OCR often confuses these inside numbers ($ I,839.OO -> $1,839.00,
# $a,099.oo -> $4,099.00). Only applied right after a currency symbol.
_DIGIT_FIX = str.maketrans("OoIl|aASsBZzGg", "00111445588229")
_PRICE_CHUNK = re.compile(r"[$€£¥]\s*[\dOoIl|aASsBZzGg,\. ]{2,}")


def _fix_ocr_digits(text):
    def fix(m):
        return m.group(0).replace(" ", "").translate(_DIGIT_FIX)
    return _PRICE_CHUNK.sub(fix, text)


def _recognize(pil_image, langs):
    for lang in langs:
        try:
            return winocr.recognize_pil_sync(pil_image.convert("RGB"), lang)
        except Exception:
            continue
    return None


def _variants(pil_image):
    """A few preprocessing passes — different ones catch different text on
    low-quality scans, so we OCR each and merge."""
    yield pil_image
    gray = ImageOps.autocontrast(pil_image.convert("L"))
    yield gray.convert("RGB")
    for threshold in (150, 175):
        yield gray.point(lambda p: 0 if p < threshold else 255).convert("RGB")


def _line_to_item(line, W, H):
    from .extract import parse_id, parse_price
    text = re.sub(r"\s+", " ", line.get("text", "")).strip()
    rects = [w["bounding_rect"] for w in line.get("words", []) if w.get("bounding_rect")]
    if not text or not rects:
        return None
    text = _fix_ocr_digits(text)
    x0 = min(r["x"] for r in rects)
    y0 = min(r["y"] for r in rects)
    x1 = max(r["x"] + r["width"] for r in rects)
    y1 = max(r["y"] + r["height"] for r in rects)
    price = parse_price(text)
    return {
        "text": text,
        "bbox_norm": {"x0": round(x0 / W, 5), "y0": round(y0 / H, 5),
                      "x1": round(x1 / W, 5), "y1": round(y1 / H, 5)},
        "is_price": price is not None,
        "price": price,
        "id": parse_id(text),
        "ocr": True,
    }


def ocr_image(pil_image, langs=("es", "en"), multipass=False):
    """OCR an image into extract-style items with normalized bboxes.

    Returns ``[{text, bbox_norm, is_price, price, id}]`` (same shape as
    `extract.extract_page_text` items). Empty list if OCR is unavailable
    or finds nothing.

    A single clean pass gives the most accurate prices/codes. ``multipass``
    OCRs a few preprocessed versions and merges them for a bit more recall on
    faint scans, at the cost of noisier reads — off by default.
    """
    if not _AVAILABLE:
        return []
    W, H = pil_image.size

    if multipass:
        passes = list(_variants(pil_image))
    else:
        result = _recognize(pil_image, langs)
        if not ((result or {}).get("lines")):
            # Faint scan: one contrast-stretched retry before giving up.
            passes = [ImageOps.autocontrast(pil_image.convert("L")).convert("RGB")]
        else:
            passes = [pil_image]

    items, seen = [], set()
    for variant in passes:
        result = _recognize(variant, langs)
        for line in (result or {}).get("lines") or []:
            item = _line_to_item(line, W, H)
            if not item:
                continue
            key = re.sub(r"\W", "", item["text"].lower())
            if key and key not in seen:
                seen.add(key)
                items.append(item)
    items.sort(key=lambda it: (it["bbox_norm"]["y0"], it["bbox_norm"]["x0"]))
    return items
