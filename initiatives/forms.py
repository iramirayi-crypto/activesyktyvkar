from django import forms

from .models import Initiative


class InitiativeForm(forms.ModelForm):
    latitude = forms.DecimalField(
        required=False,
        min_value=-90,
        max_value=90,
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(),
        error_messages={
            "invalid": "Координаты места указаны неверно.",
            "min_value": "Широта должна быть не меньше -90.",
            "max_value": "Широта должна быть не больше 90.",
        },
    )
    longitude = forms.DecimalField(
        required=False,
        min_value=-180,
        max_value=180,
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(),
        error_messages={
            "invalid": "Координаты места указаны неверно.",
            "min_value": "Долгота должна быть не меньше -180.",
            "max_value": "Долгота должна быть не больше 180.",
        },
    )
    image = forms.ImageField(
        label="Фотография",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": "image/*"}
        ),
    )

    class Meta:
        model = Initiative
        fields = [
            "title",
            "category",
            "description",
            "location",
            "latitude",
            "longitude",
        ]
        labels = {
            "title": "Название инициативы",
            "category": "Категория",
            "description": "Описание инициативы",
            "location": "Место реализации",
        }
        error_messages = {
            "title": {
                "required": "Укажите название инициативы.",
                "max_length": "Название не должно превышать 200 символов.",
            },
            "category": {"required": "Выберите категорию."},
            "description": {"required": "Добавьте описание инициативы."},
            "location": {
                "required": "Укажите место реализации.",
                "max_length": "Место реализации не должно превышать 500 символов.",
            },
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: Установить освещение в парке",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 7,
                    "placeholder": "Опишите проблему, решение и ожидаемый результат",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: район Орбита, ул. Лыткина, 31",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].required = True

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_description(self):
        return self.cleaned_data["description"].strip()

    def clean_location(self):
        return self.cleaned_data["location"].strip()

    def clean(self):
        cleaned_data = super().clean()
        latitude = str(self.data.get("latitude") or "").strip()
        longitude = str(self.data.get("longitude") or "").strip()
        if not latitude or not longitude:
            self.add_error(
                "latitude",
                "Отметьте место реализации на карте.",
            )
        return cleaned_data
