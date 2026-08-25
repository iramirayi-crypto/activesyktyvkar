from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST

from initiatives.models import Initiative
from initiatives.views import is_moderator
from accounts.models import AuditLog
from .models import Comment
from .forms import CommentForm


@login_required
@require_POST
def add_comment(request, pk):
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        status="published"
    )

    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(
            request,
            next(iter(form.errors.values()))[0]
        )
        return redirect("initiative_detail", pk=pk)

    comment = form.save(commit=False)
    comment.initiative = initiative
    comment.author = request.user
    comment.save()
    messages.success(request, "Комментарий добавлен.")

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
@require_POST
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

    if is_moderator(request.user):
        AuditLog.objects.create(
            user=request.user,
            action=(
                f'Удалён комментарий к инициативе '
                f'«{comment.initiative.title}»'
            ),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

    comment.delete()
    messages.success(request, "Комментарий удалён.")

    return redirect(
        "initiative_detail",
        pk=initiative_id
    )
