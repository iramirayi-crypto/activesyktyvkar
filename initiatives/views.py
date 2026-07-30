from django.shortcuts import render, get_object_or_404, redirect
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

    user_voted = False

    if request.user.is_authenticated:
        user_voted = Vote.objects.filter(
            initiative=initiative,
            user=request.user
        ).exists()

    return render(
        request,
        "initiatives/detail.html",
        {
            "initiative": initiative,
            "attachments": attachments,
            "votes_count": votes_count,
            "user_voted": user_voted,
        },
    )


def vote_initiative(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")

    initiative = get_object_or_404(
        Initiative,
        pk=pk
    )

    vote = Vote.objects.filter(
        initiative=initiative,
        user=request.user
    )

    if vote.exists():
        vote.delete()
    else:
        Vote.objects.create(
            initiative=initiative,
            user=request.user
        )

    return redirect(
        "initiative_detail",
        pk=initiative.pk
    )