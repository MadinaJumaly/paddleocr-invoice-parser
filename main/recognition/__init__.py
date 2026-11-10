"""Table recognition: PDF/image -> PaddleOCR -> table grid -> Excel."""

import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .engine import OCRUnavailable, PaddleEngine
from .export import tables_to_xlsx
from .pipeline import extract_tables

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = PaddleEngine()
    return _engine


def run_recognition(recognition, engine=None):
    """Process one Recognition record in place and save it."""
    from ..models import Recognition

    engine = engine or get_engine()
    try:
        tables = extract_tables(
            recognition.source.path,
            engine=engine,
            lang=recognition.language,
            max_pages=settings.OCR_MAX_PAGES,
            dpi=settings.OCR_PDF_DPI,
        )
    except OCRUnavailable as exc:
        recognition.status, recognition.error = Recognition.Status.FAILED, str(exc)
    except Exception as exc:  # keep the user-facing app alive; details go to the log
        logger.exception("Recognition %s failed", recognition.pk)
        recognition.status, recognition.error = Recognition.Status.FAILED, f"Ошибка распознавания: {exc}"
    else:
        recognition.tables = tables
        if tables:
            recognition.result.save(recognition.result_name, ContentFile(tables_to_xlsx(tables)), save=False)
            recognition.status = Recognition.Status.DONE
        else:
            recognition.status = Recognition.Status.EMPTY
    recognition.finished_at = timezone.now()
    recognition.save()
    return recognition
