from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from initiatives.models import Initiative
from .models import Comment


@login_required
def add_comment(request, pk):
    if request.method == "POST":

        initiative = get_object_or_404(
            Initiative,
            pk=pk
        )

        text = request.POST.get("text")

        if text.strip():
            Comment.objects.create(
                initiative=initiative,
                author=request.user,
                text=text
            )

    return redirect(
        "initiative_detail",
        pk=pk
    )