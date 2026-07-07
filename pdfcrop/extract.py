"""Extract the PDF's text layer with positions, so crops can be auto-labelled.

Everything here is format-agnostic: we read the text lines PyMuPDF already knows
about, normalize their bounding boxes to 0..1 (the same space crops use), and
flag lines that look like a price. No assumptions about product codes, columns
or a specific catalog layout — it works on any PDF that has a text layer.
"""
import re

# Currency-ish tokens: a symbol/code next to a number, or a number next to one.
_CUR = r"[$€£¥₹]|USD|EUR|MXN|GBP|BRL|ARS|COP|CLP|PEN|pesos?|d(?:ó|o)lares?"
_NUM = r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
PRICE_RE = re.compile(
    rf"(?:(?:{_CUR})\s*(?P<a>{_NUM}))|(?:(?P<b>{_NUM})\s*(?:{_CUR}))",
    re.IGNORECASE,
)

MIN_LABEL_LEN = 2


def _clean(text):
    return re.sub(r"\s+", " ", text).strip()


def parse_price(text):
    """Return a float price if ``text`` contains a currency amount, else None."""
    m = PRICE_RE.search(text)
    if not m:
        return None
    raw = m.group("a") or m.group("b") or ""
    raw = raw.strip()
    if not raw:
        return None
    # Normalize thousands/decimal separators to a plain float.
    if "," in raw and "." in raw:
        # Whichever comes last is the decimal separator.
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        # A single comma with 1-2 trailing digits is a decimal, else thousands.
        raw = raw.replace(",", ".") if re.search(r",\d{1,2}$", raw) else raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def extract_page_text(doc, progress_cb=None):
    """Return ``{page(1-based): [ {text, bbox_norm, is_price, price} ]}``."""
    result = {}
    total = doc.page_count
    for pno in range(total):
        page = doc._doc.load_page(pno) if hasattr(doc, "_doc") else doc.load_page(pno)
        rect = page.rect
        pw = rect.width or 1
        ph = rect.height or 1
        items = []
        data = page.get_text("dict")
        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                text = _clean("".join(span.get("text", "") for span in line.get("spans", [])))
                if not text:
                    continue
                x0, y0, x1, y1 = line["bbox"]
                price = parse_price(text)
                items.append({
                    "text": text,
                    "bbox_norm": {
                        "x0": round(x0 / pw, 5),
                        "y0": round(y0 / ph, 5),
                        "x1": round(x1 / pw, 5),
                        "y1": round(y1 / ph, 5),
                    },
                    "is_price": price is not None,
                    "price": price,
                })
        result[pno + 1] = items
        if progress_cb:
            progress_cb(pno + 1, total)
    return result


def build_label_list(page_text):
    """Flatten extracted text into a deduped label list for the sidebar."""
    seen = set()
    labels = []
    for page in sorted(page_text):
        for item in page_text[page]:
            text = item["text"]
            # Drop noise: too short, or a bare number that isn't a price.
            if len(text) < MIN_LABEL_LEN:
                continue
            if not item["is_price"] and re.fullmatch(r"[\d.,\-\s]+", text):
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            labels.append({
                "id": "",
                "label": text,
                "category": None,
                "page": page,
                "price": item["price"],
            })
    return labels


def _overlap(a, b):
    """Area of intersection of two normalized bboxes (0 if disjoint)."""
    ix0 = max(a["x0"], b["x0"])
    iy0 = max(a["y0"], b["y0"])
    ix1 = min(a["x1"], b["x1"])
    iy1 = min(a["y1"], b["y1"])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def _x_overlaps(a, b):
    return min(a["x1"], b["x1"]) > max(a["x0"], b["x0"])


def find_label_for_crop(page_items, crop, below_gap=0.06):
    """Suggest a label + price for a crop rectangle (normalized coords).

    Prefers text lines that fall *inside* the crop; if none, looks at lines
    immediately *below* it (a caption under a photo). Returns
    ``{"label": str|None, "price": float|None, "candidates": [str, ...]}``.
    """
    if not page_items:
        return {"label": None, "price": None, "candidates": []}

    inside = [it for it in page_items if _overlap(it["bbox_norm"], crop) > 0]
    chosen = inside
    if not chosen:
        below = []
        for it in page_items:
            b = it["bbox_norm"]
            if b["y0"] >= crop["y1"] - 0.005 and b["y0"] <= crop["y1"] + below_gap \
                    and _x_overlaps(b, crop):
                below.append(it)
        below.sort(key=lambda it: it["bbox_norm"]["y0"])
        chosen = below

    if not chosen:
        return {"label": None, "price": None, "candidates": []}

    names = [it for it in chosen if not it["is_price"]]
    price = next((it["price"] for it in chosen if it["is_price"]), None)
    # Best name = longest non-price line (usually the product/figure title).
    label = max(names, key=lambda it: len(it["text"]))["text"] if names else None
    candidates = [it["text"] for it in chosen]
    return {"label": label, "price": price, "candidates": candidates}
