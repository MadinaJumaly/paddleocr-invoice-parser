import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def _user_path(folder, instance, filename):
    # Random names: users' original file names never touch the filesystem.
    ext = Path(filename).suffix.lower()
    return f"{folder}/{instance.user_id}/{uuid.uuid4().hex}{ext}"


def source_upload_to(instance, filename):
    return _user_path("uploads", instance, filename)


def result_upload_to(instance, filename):
    return _user_path("results", instance, filename)


class Profile(models.Model):
    """Extra data for Django's built-in User (страница «Пользователь»)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Телефон", max_length=32, blank=True)
    organization = models.CharField("Организация", max_length=200, blank=True)

    def __str__(self):
        return f"Профиль {self.user.username}"


class Recognition(models.Model):
    """One uploaded document and its recognition result. The list of these is the «История»."""

    class Status(models.TextChoices):
        PENDING = "pending", "В обработке"
        DONE = "done", "Готово"
        EMPTY = "empty", "Таблицы не найдены"
        FAILED = "failed", "Ошибка"

    class Language(models.TextChoices):
        RU = "ru", "Русский"
        EN = "en", "English"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recognitions")
    source = models.FileField("Документ", upload_to=source_upload_to)
    original_name = models.CharField(max_length=255)
    language = models.CharField("Язык документа", max_length=8, choices=Language.choices, default=Language.RU)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    # Recognized tables: [{"page": 1, "rows": [["a", "b"], ...]}, ...]
    tables = models.JSONField(default=list, blank=True)
    result = models.FileField("Excel", upload_to=result_upload_to, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_name} ({self.get_status_display()})"

    @property
    def result_name(self):
        return f"{Path(self.original_name).stem}.xlsx"

    @property
    def duration(self):
        if self.finished_at:
            return self.finished_at - self.created_at
        return None

    def delete_files(self):
        for f in (self.source, self.result):
            if f:
                f.delete(save=False)
