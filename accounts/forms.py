from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        required=True,
        error_messages={
            "required": "Укажите Email.",
            "invalid": "Введите корректный Email.",
        }
    )
    personal_data_consent = forms.BooleanField(
        label="Согласие на обработку персональных данных",
        required=True,
        error_messages={
            "required": (
                "Для регистрации необходимо дать согласие "
                "на обработку персональных данных."
            ),
        }
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "personal_data_consent",
        )

    def clean_email(self):
        email = User.objects.normalize_email(
            self.cleaned_data.get("email", "").strip()
        )

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Пользователь с таким Email уже зарегистрирован."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user


class AvatarForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ["avatar"]


class ProfileForm(forms.ModelForm):

    def clean_email(self):
        email = User.objects.normalize_email(
            self.cleaned_data.get("email", "").strip()
        )

        if not email:
            return ""

        email_is_taken = User.objects.filter(
            email__iexact=email
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if email_is_taken:
            raise forms.ValidationError(
                "Пользователь с таким Email уже зарегистрирован."
            )

        return email

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
        ]

        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email",
        }

        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
        }
