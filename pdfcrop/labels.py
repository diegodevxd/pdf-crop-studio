"""Optional CSV label list.

Lets a user load a list of items to tag crops against (e.g. product codes,
figure numbers, SKUs). The CSV is free-form: we look for an id-ish column and
a name/label-ish column, with an optional category column. If there's no
header row, the first column is treated as the id and the second as the label.
"""
import csv


ID_KEYS = ("id", "code", "codigo", "sku", "ref", "key")
LABEL_KEYS = ("label", "name", "nombre", "title", "titulo", "descripcion", "description")
CATEGORY_KEYS = ("category", "categoria", "group", "grupo", "type", "tipo")


def _pick(fieldnames, candidates):
    lowered = {fn.lower().strip(): fn for fn in fieldnames if fn}
    for cand in candidates:
        if cand in lowered:
            return lowered[cand]
    return None


def load_labels(path):
    """Return an ordered list of ``{"id", "label", "category"}`` dicts."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048)
        f.seek(0)
        has_header = csv.Sniffer().has_header(sample) if sample.strip() else False
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        rows = []
        if has_header:
            reader = csv.DictReader(f, dialect=dialect)
            id_col = _pick(reader.fieldnames or [], ID_KEYS)
            label_col = _pick(reader.fieldnames or [], LABEL_KEYS)
            cat_col = _pick(reader.fieldnames or [], CATEGORY_KEYS)
            # Fall back to positional if we couldn't recognise columns.
            cols = reader.fieldnames or []
            if id_col is None and cols:
                id_col = cols[0]
            if label_col is None and len(cols) > 1:
                label_col = cols[1]
            for r in reader:
                rows.append(_row(
                    r.get(id_col, "") if id_col else "",
                    r.get(label_col, "") if label_col else "",
                    r.get(cat_col, "") if cat_col else "",
                ))
        else:
            reader = csv.reader(f, dialect=dialect)
            for r in reader:
                rows.append(_row(
                    r[0] if len(r) > 0 else "",
                    r[1] if len(r) > 1 else "",
                    r[2] if len(r) > 2 else "",
                ))

    return [r for r in rows if r["id"] or r["label"]]


def _row(id_val, label_val, cat_val):
    return {
        "id": (id_val or "").strip(),
        "label": (label_val or "").strip(),
        "category": (cat_val or "").strip() or None,
    }
