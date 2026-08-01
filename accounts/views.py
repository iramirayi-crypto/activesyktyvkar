from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
    else:
        form = UserCreationForm()

    form.fields["username"].help_text = ""
    form.fields["password1"].help_text = ""
    form.fields["password2"].help_text = ""

    form.fields["username"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Введите имя пользователя"
    })

    form.fields["password1"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Введите пароль"
    })

    form.fields["password2"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Повторите пароль"
    })

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")

    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
    else:
        form = AuthenticationForm()

    form.fields["username"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Имя пользователя"
    })

    form.fields["password"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Пароль"
    })

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("home")

    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("home")