# Building a standalone Windows `.exe`

This lets non-technical users run PDF Crop Studio by double-clicking, with no
Python install required.

## 1. Set up a clean environment

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

## 2. Build

```bash
pyinstaller --onefile --windowed --name "PDF Crop Studio" ^
    --collect-all fitz ^
    run.py
```

Notes:

- `--windowed` hides the console window (it's a GUI app).
- `--collect-all fitz` bundles the PyMuPDF binaries; without it the `.exe` may
  fail to open PDFs on a machine that doesn't have the DLLs.
- On macOS/Linux use `--collect-all fitz` too, and drop the `^` line-continuation
  (use `\` on bash).

The finished executable is at `dist/PDF Crop Studio.exe`.

## 3. Distribute

Don't commit `build/`, `dist/`, or the generated `.spec` file — they're in
`.gitignore`. Instead, attach `PDF Crop Studio.exe` to a **GitHub Release**:

1. Push your code and tag a version: `git tag v0.1.0 && git push --tags`
2. On GitHub → Releases → Draft a new release → pick the tag.
3. Drag `dist/PDF Crop Studio.exe` into the release assets.

## Optional: custom icon

Add `--icon app.ico` to the build command with a `.ico` file to brand the
executable and its taskbar entry.
```
