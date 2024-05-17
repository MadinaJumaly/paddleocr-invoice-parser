from django import forms
from .models import TableRecognitionFile, TableRecognitionImage






class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def init(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().init(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class UploadFileForm(forms.Form):
    files = MultipleFileField()

class UploadFileForm2(forms.ModelForm):
    class Meta:
        model = TableRecognitionFile
        fields = ('file',)


class UploadImageForm(forms.ModelForm):
    class Meta:
        model = TableRecognitionImage
        fields = ('image',)