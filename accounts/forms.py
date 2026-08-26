import logging
from smtplib import SMTPException

from django import forms
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


logger = logging.getLogger(__name__)


class SafePasswordResetForm(PasswordResetForm):
    def send_mail(self, *args, **kwargs):
        try:
            return super().send_mail(*args, **kwargs)
        except (SMTPException, OSError):
            logger.exception("Не удалось отправить письмо восстановления пароля.")
            return None


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        label="Имя",
        required=True,
        max_length=150,
        error_messages={"required": "Укажите имя."},
    )
    last_name = forms.CharField(
        label="Фамилия",
        required=True,
        max_length=150,
        error_messages={"required": "Укажите фамилию."},
    )
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
            "first_name",
            "last_name",
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
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"]
        user.is_active = False

        if commit:
            user.save()

        return user


class EmailVerificationForm(forms.Form):
    code = forms.RegexField(
        label="Код подтверждения",
        regex=r"^\d{6}$",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "000000",
            }
        ),
        error_messages={
            "required": "Введите код подтверждения.",
            "invalid": "Код должен состоять из шести цифр.",
        },
    )


class AvatarForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ["avatar"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
        ]

        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
        }

        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }


class EmailChangeRequestForm(forms.Form):
    new_email = forms.EmailField(
        label="Новый Email",
        required=True,
        error_messages={
            "required": "Укажите новый Email.",
            "invalid": "Введите корректный Email.",
        },
    )
    current_password = forms.CharField(
        label="Текущий пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
        error_messages={"required": "Введите текущий пароль."},
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_new_email(self):
        email = User.objects.normalize_email(
            self.cleaned_data.get("new_email", "").strip()
        )

        if email.casefold() == self.user.email.strip().casefold():
            raise forms.ValidationError(
                "Новый Email должен отличаться от текущего."
            )

        if User.objects.filter(email__iexact=email).exclude(
            pk=self.user.pk
        ).exists():
            raise forms.ValidationError(
                "Пользователь с таким Email уже зарегистрирован."
            )

        return email

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password", "")
        if not self.user.check_password(password):
            raise forms.ValidationError("Неверный текущий пароль.")
        return password


class DeleteAccountForm(forms.Form):
    current_password = forms.CharField(
        label="Текущий пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
        error_messages={"required": "Введите текущий пароль."},
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password", "")
        if not self.user.check_password(password):
            raise forms.ValidationError("Неверный текущий пароль.")
        return password


class BlockUserForm(forms.Form):
    DURATION_CHOICES = (
        ("1", "1 день"),
        ("7", "7 дней"),
        ("30", "30 дней"),
        ("permanent", "Бессрочно"),
    )

    reason = forms.CharField(
        label="Причина",
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4}),
        error_messages={"required": "Укажите причину блокировки."},
    )
    duration = forms.ChoiceField(
        label="Срок",
        choices=DURATION_CHOICES,
    )
