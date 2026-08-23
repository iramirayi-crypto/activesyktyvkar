from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

from initiatives.models import Initiative
from .models import Comment, CommentDeletion


def is_moderator(user):
    return (
        user.is_superuser
        or user.groups.filter(name="Модераторы").exists()
    )


@login_required
def add_comment(request, pk):
    if request.method == "POST":

        initiative = get_object_or_404(
            Initiative,
            pk=pk
        )

        text = request.POST.get("text", "").strip()

        if text:
            Comment.objects.create(
                initiative=initiative,
                author=request.user,
                text=text
            )

    return redirect(
        "initiative_detail",
        pk=pk
    )


@login_required
@user_passes_test(is_moderator)
def moderation_comments(request):
    comments = Comment.objects.select_related(
        "author",
        "initiative"
    ).order_by("-created_at")

    return render(
        request,
        "comments/moderation_comments.html",
        {
            "comments": comments
        }
    )


@login_required
def delete_comment(request, pk):

    comment = get_object_or_404(
        Comment,
        pk=pk
    )

    initiative_id = comment.initiative.id

    if not (
        comment.author == request.user
        or is_moderator(request.user)
    ):
        return redirect(
            "initiative_detail",
            pk=initiative_id
        )

    if request.method == "POST":

        reason = request.POST.get(
            "deletion_reason",
            ""
        ).strip()

        if reason:

            CommentDeletion.objects.create(
                comment_author=comment.author,
                initiative=comment.initiative,
                comment_text=comment.text,
                reason=reason,
                deleted_by=request.user
            )

            comment.delete()

    return redirect(
        "initiative_detail",
        pk=initiative_id
    )