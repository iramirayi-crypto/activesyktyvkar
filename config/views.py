from django.shortcuts import render


def home(request):
    return render(request, "home.html")

def about(request):
    return render(
        request,
        "about.html"
    )

def how_to_use(request):
    return render(
        request,
        "how_to_use.html"
    )

def contacts(request):
    return render(
        request,
        "contacts.html"
    )