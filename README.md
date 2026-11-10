# PDF → Excel: распознавание таблиц

A Django website that recognizes tables in accounting reports (PDF or a scan/photo)
with PaddleOCR and returns them as an Excel file. Built during the production
internship at «Инженерно-технический центр УДП РК» (Astana IT University, IT-2204).

## Features

| Page | URL | What it does |
|---|---|---|
| Главная | `/` | Landing page |
| Регистрация / Вход | `/signup/`, `/login/` | Django's built-in auth |
| Распознавание | `/recognition/` | Upload a PDF/image → tables are found, read, shown and exported to `.xlsx` |
| История | `/history/` | Log of every upload with status, filter, Excel download and delete |
| Профиль | `/profile/` | Name, email, phone, organization + upload statistics |

Users only ever see and download their own files.

## How recognition works

`main/recognition/`

1. **pipeline.py**: PDF pages are rendered to images with PyMuPDF (200 dpi).
2. **engine.py**: PaddleOCR's layout model (PP-Structure) finds the table regions
   on each page, then the OCR model reads the text inside each table.
3. **table.py**: the text boxes are turned into a grid. Each box is stretched into
   a full-width row band and a full-height column band, non-max suppression merges
   overlapping bands into real rows/columns, and every box goes into the cell it
   overlaps most. (This is the algorithm from the original Colab prototype in
   `research/colab_prototype.py`, without the TensorFlow dependency.)
4. **export.py**: one Excel sheet per table; numbers such as `1 234,5` become real numbers.

## Run locally

Requires **Python 3.12** (paddlepaddle 2.6 has no wheels for newer versions).

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000. On the first recognition PaddleOCR downloads its
models (~150 MB) into `~/.paddleocr/`, so the first run takes longer.

Run the tests (they use a fake OCR engine, so they take seconds):

```bash
python manage.py test main
```

### Settings (environment variables)

| Variable | Default | |
|---|---|---|
| `DJANGO_DEBUG` | `true` | set to `false` on a server |
| `DJANGO_SECRET_KEY` | dev key | **required** when debug is off |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated |
| `OCR_MAX_PAGES` | `10` | max PDF pages per upload |
| `OCR_PDF_DPI` | `200` | PDF render resolution |

## Project layout

```
manage.py
practice/            Django project settings + root URLs
main/                the app: models, views, forms, templates, static
  recognition/       OCR pipeline (independent of Django except __init__.py)
  tests.py
research/            original Colab prototype (kept for reference)
samples/             test.pdf and page images for trying the site
```

## Known limitations

- Recognition runs inside the request: about 5–20 s per page on a CPU. Fine for
  a demo; a production deployment should move it to a background worker
  (Celery/RQ) and raise the web server timeout.
- Russian text uses PaddleOCR 2.x's Cyrillic model. Structure and most numbers
  come out right, but some digits are still misread, so check the totals.
  PaddleOCR 3.x (PP-OCRv5) has a much stronger Russian model, but its API is
  different; that's the next upgrade.
- Tables are detected by layout, not by ruling lines, so very dense or rotated
  scans may need a cleaner image.
