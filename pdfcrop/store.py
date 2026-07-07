"""Session persistence and manifest export.

A "project" is one PDF plus the crops made from it. It's saved next to the
output folder as ``project.json`` so you can close the app and resume later.
Every save also (re)writes ``manifest.json`` — a plain list of crops meant for
downstream tools to consume.
"""
import json
import os


class Project:
    def __init__(self, output_dir, source_pdf=None, render_zoom=3.0):
        self.output_dir = output_dir
        self.source_pdf = source_pdf
        self.render_zoom = render_zoom
        self.crops = {}  # key -> crop record
        os.makedirs(self.output_dir, exist_ok=True)

    @property
    def project_path(self):
        return os.path.join(self.output_dir, "project.json")

    @property
    def manifest_path(self):
        return os.path.join(self.output_dir, "manifest.json")

    @property
    def images_dir(self):
        return os.path.join(self.output_dir, "crops")

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, output_dir):
        """Load an existing project from ``output_dir`` if present, else None."""
        path = os.path.join(output_dir, "project.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        proj = cls(
            output_dir,
            source_pdf=data.get("source_pdf"),
            render_zoom=data.get("render_zoom", 3.0),
        )
        proj.crops = data.get("crops", {})
        return proj

    def save(self):
        os.makedirs(self.images_dir, exist_ok=True)
        data = {
            "source_pdf": self.source_pdf,
            "render_zoom": self.render_zoom,
            "crops": self.crops,
        }
        _atomic_write_json(self.project_path, data)
        # Manifest: a flat list, most useful for external consumers.
        _atomic_write_json(self.manifest_path, list(self.crops.values()))

    # ------------------------------------------------------------------

    def next_key(self, preferred=None):
        """A unique crop key. Uses the user id if free, else auto-numbers."""
        if preferred and preferred not in self.crops:
            return preferred
        i = 1
        while True:
            key = f"crop_{i:04d}"
            if key not in self.crops:
                return key
            i += 1

    def image_path(self, key):
        return os.path.join(self.images_dir, f"{key}.png")

    def add_crop(self, key, record):
        self.crops[key] = record
        self.save()

    def remove_crop(self, key):
        self.crops.pop(key, None)
        img = self.image_path(key)
        try:
            if os.path.exists(img):
                os.remove(img)
        except OSError:
            pass
        self.save()


def _atomic_write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)
