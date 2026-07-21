from django.shortcuts import render


def initiative_list(request):
    return render(request, 'initiatives/list.html')