"""Entry point for PDF Crop Studio.

Usage:
    python run.py                # open the app, then pick a PDF from the UI
    python run.py path/to.pdf    # open the app with that PDF already loaded
"""
import sys
import tkinter as tk

from pdfcrop.app import ExtractorApp


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None

    root = tk.Tk()
    root.title("PDF Crop Studio")
    # Crisp rendering on high-DPI Windows displays.
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    ExtractorApp(root, pdf_path=pdf_path)
    root.mainloop()


if __name__ == "__main__":
    main()
