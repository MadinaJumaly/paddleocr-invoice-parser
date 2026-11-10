"""Document (PDF or image) -> list of tables."""

from pathlib import Path

import cv2
import numpy as np

from .table import build_grid

PDF_EXTENSIONS = {".pdf"}
MIN_COLUMNS = 2


def load_pages(path, max_pages, dpi):
    """Return the document's pages as BGR numpy images (the format OpenCV/Paddle expect)."""
    path = Path(path)
    if path.suffix.lower() in PDF_EXTENSIONS:
        import fitz  # PyMuPDF

        pages = []
        with fitz.open(path) as doc:
            for page in list(doc)[:max_pages]:
                pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
                rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                pages.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        return pages

    # np.fromfile + imdecode also works with non-ASCII paths (cv2.imread does not on Windows).
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Не удалось открыть изображение.")
    return [image]


def extract_tables(path, engine, lang, max_pages, dpi):
    """
    Find and read every table in the document.

    If the layout model finds no table on a single uploaded image, the whole
    image is treated as one table (users often upload a photo/scan of just the table).
    """
    pages = load_pages(path, max_pages=max_pages, dpi=dpi)
    tables = []
    for page_no, image in enumerate(pages, start=1):
        rects = engine.find_tables(image)
        if not rects and len(pages) == 1:
            h, w = image.shape[:2]
            rects = [(0, 0, w, h)]
        for x1, y1, x2, y2 in rects:
            crop = image[y1:y2, x1:x2]
            boxes = engine.read_text(crop, lang)
            rows = build_grid(boxes, width=crop.shape[1], height=crop.shape[0])
            # A single column is a text block the layout model mistook for a table
            # (e.g. a reference list), not a table.
            if rows and len(rows[0]) >= MIN_COLUMNS:
                tables.append({"page": page_no, "rows": rows})
    return tables
