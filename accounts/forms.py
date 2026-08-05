from django import forms
from django.contrib.auth.models import User
from .models import Profile


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