from django.shortcuts import render
from .models import Initiative
from attachments.models import Attachment


def initiative_list(request):
    initiatives = Initiative.objects.filter(status="published")

    for initiative in initiatives:
        initiative.image = Attachment.objects.filter(
            initiative=initiative
        ).first()

    return render(
        request,
        "initiatives/list.html",
        {"initiatives": initiatives},
    )