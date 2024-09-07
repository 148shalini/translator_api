from django import forms


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Select File")
    target_language = forms.ChoiceField(
        choices=[
            ("en", "English"),
            ("hi", "Hindi"),
            ("te", "Telugu"),
            ("mr", "Marathi"),
            ("pa", "Punjabi"),
            ("tulu", "Tulu"),  # Note: Tulu is unsupported in Google Translate.
        ],
        label="Select Target Language",
    )