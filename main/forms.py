from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile, Recognition

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


class BootstrapMixin:
    """Adds Bootstrap's form-control class to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class LoginForm(BootstrapMixin, AuthenticationForm):
    pass


class SignUpForm(BootstrapMixin, UserCreationForm):
    email = forms.EmailField(label="Email", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class UserForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class ProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone", "organization")


class RecognitionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Recognition
        fields = ("source", "language")
        widgets = {"source": forms.ClearableFileInput(attrs={"accept": ",".join(sorted(ALLOWED_EXTENSIONS))})}

    def clean_source(self):
        f = self.cleaned_data["source"]
        ext = Path(f.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Поддерживаются PDF и изображения (PNG, JPG, BMP, TIFF).")
        if f.size > settings.FILE_UPLOAD_MAX_BYTES:
            limit_mb = settings.FILE_UPLOAD_MAX_BYTES // (1024 * 1024)
            raise forms.ValidationError(f"Файл больше {limit_mb} МБ.")
        return f
