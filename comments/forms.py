from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        labels = {"text": "Комментарий"}
        error_messages = {
            "text": {
                "required": "Комментарий не может быть пустым.",
                "max_length": "Комментарий не должен превышать 1000 символов.",
            }
        }
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "maxlength": 1000,
                    "placeholder": "Напишите конструктивный комментарий",
                    "data-submit-shortcut": "true",
                }
            )
        }

    def clean_text(self):
        return self.cleaned_data["text"].strip()
