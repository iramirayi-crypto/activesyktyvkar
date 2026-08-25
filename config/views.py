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


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)

