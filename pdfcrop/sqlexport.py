"""Export the saved crops to a portable .sql file.

One row per crop: id, label, price, category, page and the image path (the PNG
that lives in the ``crops/`` folder next to the .sql). Plain INSERT statements
that load into SQLite, Postgres or MySQL alike.
"""


def _q(value):
    """Quote a value as a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


COLUMNS = ("id", "label", "price", "category", "page", "image")


def build_sql(crops, table="products"):
    """Return the full SQL text for the given crop records."""
    rows = sorted(crops.values(), key=lambda r: (r.get("page") or 0, r.get("key") or ""))

    lines = [
        f"-- Exported by PDF Crop Studio ({len(rows)} crops).",
        f"CREATE TABLE IF NOT EXISTS {table} (",
        "  id TEXT,",
        "  label TEXT,",
        "  price REAL,",
        "  category TEXT,",
        "  page INTEGER,",
        "  image TEXT",
        ");",
        "",
    ]
    if not rows:
        return "\n".join(lines)

    collist = ", ".join(COLUMNS)
    lines.append(f"INSERT INTO {table} ({collist}) VALUES")
    values = []
    for r in rows:
        values.append(
            "  (" + ", ".join([
                _q(r.get("id") or r.get("key")),
                _q(r.get("label")),
                _q(r.get("price")),
                _q(r.get("category")),
                _q(r.get("page")),
                _q(r.get("file")),
            ]) + ")"
        )
    lines.append(",\n".join(values) + ";")
    return "\n".join(lines) + "\n"


def export_sql(crops, path, table="products"):
    """Write the crops to ``path`` as SQL. Returns the number of rows."""
    text = build_sql(crops, table=table)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(crops)
