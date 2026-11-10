import io
import shutil
import tempfile
from unittest import mock

import cv2
import numpy as np
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from .models import Recognition
from .recognition.export import tables_to_xlsx
from .recognition.pipeline import extract_tables
from .recognition.table import TextBox, build_grid, iou, non_max_suppression


def box(x1, y1, x2, y2, text, score=0.9):
    return TextBox(x1, y1, x2, y2, text, score)


# A 3x3 table:   Name   | 1984 | 2019
#                Water  | 20   | 38
#                Fat    | 11   | 15
SAMPLE_BOXES = [
    box(10, 10, 80, 30, "Name"), box(200, 10, 250, 30, "1984"), box(400, 12, 450, 30, "2019"),
    box(10, 50, 70, 70, "Water"), box(205, 50, 230, 70, "20"), box(405, 51, 430, 69, "38"),
    box(10, 90, 50, 110, "Fat"), box(205, 90, 230, 110, "11"), box(405, 90, 430, 110, "15"),
]


class FakeEngine:
    """Stands in for PaddleOCR: one table covering the page, fixed text boxes."""

    def __init__(self, boxes=SAMPLE_BOXES, find=True):
        self.boxes, self.find = boxes, find

    def find_tables(self, image):
        h, w = image.shape[:2]
        return [(0, 0, w, h)] if self.find else []

    def read_text(self, image, lang):
        return list(self.boxes)


def png_bytes(w=500, h=130):
    ok, buf = cv2.imencode(".png", np.full((h, w, 3), 255, np.uint8))
    return buf.tobytes()


class TableAlgorithmTests(TestCase):
    def test_iou(self):
        self.assertEqual(iou((0, 0, 10, 10), (20, 20, 30, 30)), 0)
        self.assertAlmostEqual(iou((0, 0, 10, 10), (0, 0, 10, 10)), 1)
        self.assertAlmostEqual(iou((0, 0, 10, 10), (5, 0, 15, 10)), 1 / 3)

    def test_nms_keeps_best_of_overlapping(self):
        keep = non_max_suppression([(0, 0, 10, 10), (1, 0, 11, 10), (50, 0, 60, 10)], [0.5, 0.9, 0.7], 0.1)
        self.assertEqual(sorted(keep), [1, 2])

    def test_build_grid(self):
        grid = build_grid(SAMPLE_BOXES, width=500, height=130)
        self.assertEqual(grid, [["Name", "1984", "2019"], ["Water", "20", "38"], ["Fat", "11", "15"]])

    def test_build_grid_is_order_independent(self):
        shuffled = list(reversed(SAMPLE_BOXES))
        self.assertEqual(build_grid(shuffled, 500, 130), build_grid(SAMPLE_BOXES, 500, 130))

    def test_empty_cells_are_kept(self):
        boxes = [b for b in SAMPLE_BOXES if b.text != "11"]
        self.assertEqual(build_grid(boxes, 500, 130)[2], ["Fat", "", "15"])

    def test_no_boxes(self):
        self.assertEqual(build_grid([], 100, 100), [])

    def test_from_polygon(self):
        b = TextBox.from_polygon([[1, 2], [9, 2], [9, 8], [1, 8]], "x", 0.5)
        self.assertEqual(b.rect, (1, 2, 9, 8))


class FixDigitsTests(TestCase):
    def test_zero_lookalikes_in_numbers(self):
        from .recognition.engine import fix_digits

        self.assertEqual(fix_digits("12543оо"), "1254300")   # Cyrillic о
        self.assertEqual(fix_digits("O16"), "016")           # Latin O
        self.assertEqual(fix_digits("64 90O"), "64 900")
        self.assertEqual(fix_digits("Oil 10"), "Oil 10")     # a word stays a word
        self.assertEqual(fix_digits("Отчёт"), "Отчёт")


class ExportTests(TestCase):
    def test_xlsx_numbers_and_sheets(self):
        data = tables_to_xlsx([
            {"page": 1, "rows": [["Name", "Sum"], ["A", "1 234,5"], ["B", "59.7"]]},
            {"page": 2, "rows": [["x"]]},
        ])
        wb = load_workbook(io.BytesIO(data))
        self.assertEqual(len(wb.sheetnames), 2)
        ws = wb.worksheets[0]
        self.assertEqual(ws["B2"].value, 1234.5)
        self.assertEqual(ws["B3"].value, 59.7)
        self.assertEqual(ws["A1"].value, "Name")


class PipelineTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_image(self):
        path = f"{self.tmp}/t.png"
        with open(path, "wb") as f:
            f.write(png_bytes())
        tables = extract_tables(path, FakeEngine(), "en", max_pages=5, dpi=72)
        self.assertEqual(tables[0]["rows"][1], ["Water", "20", "38"])

    def test_single_image_without_detected_table_uses_whole_image(self):
        path = f"{self.tmp}/t.png"
        with open(path, "wb") as f:
            f.write(png_bytes())
        self.assertEqual(len(extract_tables(path, FakeEngine(find=False), "en", 5, 72)), 1)

    def test_single_column_region_is_not_a_table(self):
        path = f"{self.tmp}/t.png"
        with open(path, "wb") as f:
            f.write(png_bytes())
        lines = [box(10, 10 + 30 * i, 400, 30 + 30 * i, f"line {i}") for i in range(4)]
        self.assertEqual(extract_tables(path, FakeEngine(boxes=lines), "en", 5, 72), [])

    def test_pdf_pages_and_limit(self):
        import fitz

        path = f"{self.tmp}/t.pdf"
        doc = fitz.open()
        for _ in range(3):
            doc.new_page()
        doc.save(path)
        tables = extract_tables(path, FakeEngine(), "en", max_pages=2, dpi=72)
        self.assertEqual([t["page"] for t in tables], [1, 2])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="S3cret-pass!")
        self.other = User.objects.create_user("bob", password="S3cret-pass!")
        patcher = mock.patch("main.recognition.get_engine", return_value=FakeEngine())
        patcher.start()
        self.addCleanup(patcher.stop)

    def upload(self, name="report.png", content=None):
        f = SimpleUploadedFile(name, content or png_bytes(), content_type="image/png")
        return self.client.post(reverse("recognition"), {"source": f, "language": "en"})

    def test_public_pages(self):
        for name in ("home", "login", "signup"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_private_pages_require_login(self):
        for name in ("recognition", "history", "profile"):
            resp = self.client.get(reverse(name))
            self.assertRedirects(resp, f"{reverse('login')}?next={reverse(name)}")

    def test_signup_logs_in(self):
        resp = self.client.post(reverse("signup"), {
            "username": "newuser", "email": "", "password1": "Very-long-pass-123", "password2": "Very-long-pass-123",
        })
        self.assertRedirects(resp, reverse("recognition"))
        self.assertTrue(User.objects.get(username="newuser").profile)

    def test_login_logout(self):
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "S3cret-pass!"})
        self.assertRedirects(resp, reverse("recognition"))
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("home"))

    def test_recognition_flow(self):
        self.client.force_login(self.user)
        resp = self.upload()
        item = Recognition.objects.get()
        self.assertRedirects(resp, reverse("recognition_detail", args=[item.pk]))
        self.assertEqual(item.status, Recognition.Status.DONE)
        self.assertEqual(item.original_name, "report.png")

        page = self.client.get(reverse("recognition_detail", args=[item.pk]))
        self.assertContains(page, "Water")

        xlsx = self.client.get(reverse("download_result", args=[item.pk]))
        self.assertEqual(xlsx.status_code, 200)
        self.assertIn("report.xlsx", xlsx["Content-Disposition"])

        self.assertContains(self.client.get(reverse("history")), "report.png")

    def test_rejects_wrong_file_type(self):
        self.client.force_login(self.user)
        resp = self.upload(name="virus.exe", content=b"MZ")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Recognition.objects.count(), 0)

    def test_ocr_failure_is_recorded(self):
        self.client.force_login(self.user)
        with mock.patch("main.recognition.get_engine", side_effect=None) as g:
            g.return_value.find_tables.side_effect = RuntimeError("boom")
            self.upload()
        item = Recognition.objects.get()
        self.assertEqual(item.status, Recognition.Status.FAILED)
        self.assertIn("boom", item.error)

    def test_users_cannot_see_each_others_files(self):
        self.client.force_login(self.user)
        self.upload()
        item = Recognition.objects.get()
        self.client.force_login(self.other)
        for name in ("recognition_detail", "download_result", "download_source"):
            self.assertEqual(self.client.get(reverse(name, args=[item.pk])).status_code, 404, name)
        self.assertEqual(self.client.post(reverse("recognition_delete", args=[item.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("history")), "report.png")

    def test_delete(self):
        self.client.force_login(self.user)
        self.upload()
        item = Recognition.objects.get()
        self.assertRedirects(self.client.post(reverse("recognition_delete", args=[item.pk])), reverse("history"))
        self.assertFalse(Recognition.objects.exists())

    def test_profile_update(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("profile"), {
            "first_name": "Alice", "last_name": "A", "email": "a@example.com", "phone": "+7 700", "organization": "ИТЦ",
        })
        self.assertRedirects(resp, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alice")
        self.assertEqual(self.user.profile.organization, "ИТЦ")
