from django.shortcuts import render, get_object_or_404
from .models import Initiative, Vote
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


def initiative_detail(request, pk):
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        status="published"
    )

    attachments = Attachment.objects.filter(
        initiative=initiative
    )

    votes_count = Vote.objects.filter(
        initiative=initiative
    ).count()

    return render(
        request,
        "initiatives/detail.html",
        {
            "initiative": initiative,
            "attachments": attachments,
            "votes_count": votes_count,
        },
    )