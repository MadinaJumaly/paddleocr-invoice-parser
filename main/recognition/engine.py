"""
PaddleOCR wrapper.

Two models are used, as in the prototype:
  * a layout model that finds where the tables are on a page
    (prototype: layoutparser + PubLayNet; here: PaddleOCR's built-in PP-Structure layout model),
  * the OCR model that reads the text inside each table.

Models are heavy, so they are imported lazily and created once per process.
"""

import logging
import os
import re
import threading

from .table import TextBox

logger = logging.getLogger(__name__)

TABLE_SCORE_THRESHOLD = 0.5  # same threshold the prototype used for layout detection
TABLE_PADDING = 10           # px added around a detected table so edge text is not cut


class OCRUnavailable(RuntimeError):
    pass


class PaddleEngine:
    _lock = threading.Lock()
    _ocr = {}
    _layout = None

    def _import(self):
        try:
            import paddleocr  # noqa: F401
        except ImportError as exc:
            raise OCRUnavailable(
                "PaddleOCR не установлен. Выполните: pip install -r requirements.txt"
            ) from exc
        return paddleocr

    def _get_layout(self):
        with self._lock:
            if PaddleEngine._layout is None:
                paddleocr = self._import()
                logger.info("Loading PaddleOCR layout model")
                PaddleEngine._layout = paddleocr.PPStructure(
                    layout=True, table=False, ocr=False, show_log=False
                )
            return PaddleEngine._layout

    def _get_ocr(self, lang):
        with self._lock:
            if lang not in PaddleEngine._ocr:
                paddleocr = self._import()
                logger.info("Loading PaddleOCR text model (lang=%s)", lang)
                kwargs = {}
                if lang not in ("en", "ch"):
                    # The default multilingual detector splits every word into its own box,
                    # which breaks the column detection. PP-OCRv4's detector finds whole cells.
                    kwargs["det_model_dir"] = self._v4_detector_dir()
                PaddleEngine._ocr[lang] = paddleocr.PaddleOCR(
                    use_angle_cls=False, lang=lang, show_log=False, **kwargs
                )
            return PaddleEngine._ocr[lang]

    @staticmethod
    def _v4_detector_dir():
        from paddleocr.paddleocr import BASE_DIR, MODEL_URLS
        from paddleocr.ppocr.utils.network import maybe_download

        path = os.path.join(BASE_DIR, "whl", "det", "ch", "ch_PP-OCRv4_det_infer")
        maybe_download(path, MODEL_URLS["OCR"]["PP-OCRv4"]["det"]["ch"]["url"])
        return path

    def find_tables(self, image):
        """Return table rectangles (x1, y1, x2, y2) on the page, top to bottom."""
        h, w = image.shape[:2]
        regions = self._get_layout()(image)
        rects = []
        for region in regions:
            if region.get("type", "").lower() != "table":
                continue
            if region.get("score", 1.0) < TABLE_SCORE_THRESHOLD:
                continue
            x1, y1, x2, y2 = (int(v) for v in region["bbox"])
            rects.append((
                max(0, x1 - TABLE_PADDING), max(0, y1 - TABLE_PADDING),
                min(w, x2 + TABLE_PADDING), min(h, y2 + TABLE_PADDING),
            ))
        return sorted(rects, key=lambda r: (r[1], r[0]))

    def read_text(self, image, lang):
        """Return every text line found in the image as TextBox objects."""
        result = self._get_ocr(lang).ocr(image, cls=False)
        lines = result[0] if result else None  # one entry per input image; None when nothing found
        return [TextBox.from_polygon(poly, fix_digits(text), score) for poly, (text, score) in (lines or [])]


# Letters the OCR confuses with zero (Latin O/o, Cyrillic О/о).
_ZERO_LOOKALIKES = str.maketrans({"O": "0", "o": "0", "О": "0", "о": "0"})
_NUMERIC_LIKE = re.compile(r"[\d\s.,:;()%+\-–OoОо]+")


def fix_digits(text):
    """'12543оо' -> '1254300', 'O16' -> '016'; words are left untouched."""
    if any(ch.isdigit() for ch in text) and _NUMERIC_LIKE.fullmatch(text):
        return text.translate(_ZERO_LOOKALIKES)
    return text
