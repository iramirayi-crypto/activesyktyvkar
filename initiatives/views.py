from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count 
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Initiative, Vote, Category
from .forms import InitiativeForm
from comments.models import Comment
from comments.forms import CommentForm
from attachments.models import Attachment
from accounts.models import AuditLog
from accounts.models import Notification

# Список опубликованных инициатив
def parse_filter_date(value):
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        return None


def initiative_list(request):

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    # Только опубликованные инициативы
    initiatives = Initiative.objects.filter(
        status="published"
    )

    # Поиск
    if query:
        initiatives = initiatives.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(author__username__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query)
        )

    # Фильтр по категории
    if category.isdigit():
        initiatives = initiatives.filter(
            category__id=category
        )
    elif category:
        category = ""

    parsed_date_from = parse_filter_date(date_from)
    parsed_date_to = parse_filter_date(date_to)
    if parsed_date_from:
        initiatives = initiatives.filter(created_at__date__gte=parsed_date_from)
    if parsed_date_to:
        initiatives = initiatives.filter(created_at__date__lte=parsed_date_to)

    sort_options = {
        "newest": "-created_at",
        "oldest": "created_at",
    }
    if sort not in sort_options:
        sort = "newest"

    initiatives = initiatives.order_by(sort_options[sort])
    paginator = Paginator(initiatives, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Изображение, количество голосов и комментариев
    for initiative in page_obj:
        initiative.image = Attachment.objects.filter(
            initiative=initiative
        ).first()

        initiative.votes_count = Vote.objects.filter(
            initiative=initiative
        ).count()

        initiative.comments_count = Comment.objects.filter(
            initiative=initiative
        ).count()

    return render(
        request,
        "initiatives/list.html",
        {
            "initiatives": page_obj,
            "page_obj": page_obj,
            "query": query,
            "category": category,
            "sort": sort,
            "date_from": date_from,
            "date_to": date_to,
            "categories": Category.objects.all(),
        },
    )

# Проверки модератора
def is_moderator(user):
    return (
        user.is_authenticated
        and (
            user.groups.filter(name="Модераторы").exists()
            or user.is_superuser
        )
    )
# Страница одной инициативы
# Страница одной инициативы
def initiative_detail(request, pk):

    initiative = get_object_or_404(
        Initiative,
        pk=pk
    )

    if (
        initiative.status != "published"
        and initiative.author
        and initiative.author.profile.is_deleted
    ):
        return redirect("initiative_list")

    # Неопубликованную инициативу может смотреть
    # только её автор или модератор
    if initiative.status == "draft":
        if not request.user.is_authenticated or initiative.author != request.user:
            return redirect("initiative_list")
    elif initiative.status != "published":

        if not request.user.is_authenticated:
            return redirect("initiative_list")

        if (
            initiative.author != request.user
            and not is_moderator(request.user)
        ):
            return redirect("initiative_list")

    # Изображения доступны всегда
    attachments = Attachment.objects.filter(
        initiative=initiative
    )

    # Голоса и комментарии только для опубликованных
    votes_count = 0
    user_voted = False
    comments = Comment.objects.none()
    comment_form = CommentForm()

    if initiative.status == "published":

        votes_count = Vote.objects.filter(
            initiative=initiative
        ).count()

        if request.user.is_authenticated:

            user_voted = Vote.objects.filter(
                initiative=initiative,
                user=request.user
            ).exists()

        comments = Comment.objects.filter(
            initiative=initiative
        )

    return render(
        request,
        "initiatives/detail.html",
        {
            "initiative": initiative,
            "attachments": attachments,
            "votes_count": votes_count,
            "user_voted": user_voted,
            "comments": comments,
            "comment_form": comment_form,

            # Передаём в шаблон, является ли пользователь модератором
            "is_moderator": (
                request.user.is_authenticated
                and is_moderator(request.user)
            ),
        }
    )

# Голосование за инициативу
@require_POST
def vote_initiative(request, pk):

    # Если пользователь не вошел в систему
    if not request.user.is_authenticated:
        return redirect("login")

    # Получаем инициативу
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        status="published"
    )

    # Проверяем, голосовал ли пользователь
    vote = Vote.objects.filter(
        initiative=initiative,
        user=request.user
    )

    # Если голос уже есть — удаляем его
    if vote.exists():
        vote.delete()
        messages.info(request, "Ваш голос отменён.")

    # Иначе создаем новый голос
    else:
        Vote.objects.create(
            initiative=initiative,
            user=request.user
        )
        messages.success(request, "Спасибо! Ваш голос учтён.")

    # Возвращаемся на страницу инициативы
    return redirect(
        "initiative_detail",
        pk=initiative.pk
    )


# Редактирование комментария
def edit_comment(request, pk):

    # Если пользователь не вошел
    if not request.user.is_authenticated:
        return redirect("login")

    # Получаем комментарий
    comment = get_object_or_404(Comment, pk=pk)

    # Только автор может редактировать комментарий
    if request.user != comment.author:
        return redirect(
            "initiative_detail",
            pk=comment.initiative.id
        )

    # Если отправлена форма
    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Комментарий изменён.")
            return redirect(
                "initiative_detail",
                pk=comment.initiative.id
            )
    else:
        form = CommentForm(instance=comment)

    return render(
        request,
        "initiatives/edit_comment.html",
        {
            "comment": comment,
            "form": form,
        }
    )


# Мои инициативы
@login_required
def hidden_initiatives(request):
    initiatives = Initiative.objects.filter(
        author=request.user,
        is_hidden=True
    ).annotate(
        votes_count=Count("vote", distinct=True),
        comments_count=Count("comment", distinct=True)
    )

    for initiative in initiatives:
        initiative.image = Attachment.objects.filter(
            initiative=initiative
        ).first()

    return render(
        request,
        "initiatives/hidden_initiatives.html",
        {
            "initiatives": initiatives
        }
    )


# Создание инициативы
@login_required
def create_initiative(request):
    if request.method == "POST":
        action = request.POST.get("action", "moderation")
        form = InitiativeForm(
            request.POST,
            request.FILES,
            is_draft=action == "draft",
        )
        if form.is_valid():
            status = "draft" if action == "draft" else "moderation"
            initiative = form.save(commit=False)
            initiative.author = request.user
            initiative.status = status
            initiative.save()

            if form.cleaned_data.get("image"):
                Attachment.objects.create(
                    initiative=initiative,
                    file=form.cleaned_data["image"]
                )

            AuditLog.objects.create(
                user=request.user,
                action=f'Создана инициатива «{initiative.title}»',
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")
            )
            messages.success(
                request,
                "Черновик сохранён."
                if status == "draft"
                else "Инициатива создана и отправлена на модерацию."
            )
            return redirect("my_initiatives")
    else:
        form = InitiativeForm()

    return render(
        request,
        "initiatives/create_initiative.html",
        {
            "form": form,
        }
    )

@login_required
def delete_initiative(request, pk):
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        author=request.user
    )

    if request.method == "POST":
        initiative.delete()
        messages.success(request, "Инициатива удалена.")
        return redirect("my_initiatives")

    return render(
        request,
        "initiatives/delete_initiative.html",
        {"initiative": initiative}
    )


@login_required
def edit_initiative(request, pk):
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        author=request.user
    )

    if initiative.status == "published":
        return redirect("my_initiatives")

    if request.method == "POST":
        was_rejected = initiative.status == "rejected"
        form = InitiativeForm(request.POST, request.FILES, instance=initiative)
        if form.is_valid():
            action = request.POST.get("action", "moderation")
            status = "draft" if action == "draft" else "moderation"
            initiative = form.save(commit=False)
            initiative.status = status
            if was_rejected:
                initiative.moderator_comment = None
            initiative.save()

            if form.cleaned_data.get("image"):
                Attachment.objects.create(
                    initiative=initiative,
                    file=form.cleaned_data["image"]
                )

            AuditLog.objects.create(
                user=request.user,
                action=f'Отредактирована инициатива «{initiative.title}»',
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")
            )
            messages.success(
                request,
                "Черновик сохранён."
                if status == "draft"
                else "Инициатива изменена и отправлена на модерацию."
            )
            return redirect("my_initiatives")
    else:
        form = InitiativeForm(instance=initiative)

    return render(
        request,
        "initiatives/edit_initiative.html",
        {
            "initiative": initiative,
            "form": form,
        }
    )

@login_required
def hide_initiative(request, pk):
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        author=request.user
    )

    if request.method == "POST":
        initiative.is_hidden = not initiative.is_hidden
        initiative.save()
        if initiative.is_hidden:
            messages.info(request, "Инициатива перемещена в скрытые.")
        else:
            messages.success(request, "Инициатива возвращена.")

    if initiative.is_hidden:
        return redirect("my_initiatives")

    return redirect("hidden_initiatives")

@login_required
def unhide_initiative(request, pk):
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        author=request.user
    )

    if request.method == "POST":
        initiative.is_hidden = False
        initiative.save()
        messages.success(request, "Инициатива возвращена.")

    return redirect("hidden_initiatives")


@login_required
def my_initiatives(request):
    initiatives = Initiative.objects.filter(
        author=request.user,
        is_hidden=False
    ).annotate(
        votes_count=Count("vote", distinct=True),
        comments_count=Count("comment", distinct=True)
    )

    for initiative in initiatives:
        initiative.image = Attachment.objects.filter(
            initiative=initiative
        ).first()

    return render(
        request,
        "initiatives/my_initiatives.html",
        {
            "initiatives": initiatives
        }
    )

@login_required
@user_passes_test(is_moderator)
def moderation(request):
    moderation_query = request.GET.get("moderation_q", "").strip()
    published_query = request.GET.get("published_q", "").strip()

    initiatives = Initiative.objects.filter(
        status="moderation",
        is_hidden=False,
    ).order_by("-created_at")

    published_initiatives = Initiative.objects.filter(
        status="published"
    ).order_by("-created_at")

    if moderation_query:
        initiatives = initiatives.filter(
            Q(title__icontains=moderation_query) |
            Q(description__icontains=moderation_query) |
            Q(author__username__icontains=moderation_query) |
            Q(location__icontains=moderation_query) |
            Q(category__name__icontains=moderation_query)
        )

    if published_query:
        published_initiatives = published_initiatives.filter(
            Q(title__icontains=published_query) |
            Q(description__icontains=published_query) |
            Q(author__username__icontains=published_query) |
            Q(location__icontains=published_query) |
            Q(category__name__icontains=published_query)
        )

    for initiative in list(initiatives) + list(published_initiatives):
        initiative.image = Attachment.objects.filter(
            initiative=initiative
        ).first()

        initiative.votes_count = Vote.objects.filter(
            initiative=initiative
        ).count()

        initiative.comments_count = Comment.objects.filter(
            initiative=initiative
        ).count()

    return render(
        request,
        "initiatives/moderation.html",
        {
            "initiatives": initiatives,
            "published_initiatives": published_initiatives,
            "moderation_query": moderation_query,
            "published_query": published_query,
            "moderation_count": initiatives.count(),
            "published_count": published_initiatives.count(),
            "comments_count": Comment.objects.count(),
        },
    )


@login_required
@user_passes_test(is_moderator)
@require_POST
def publish_initiative(request, initiative_id):

    initiative = get_object_or_404(
        Initiative,
        id=initiative_id,
        status="moderation",
        is_hidden=False,
    )

    initiative.status = "published"
    initiative.moderator_comment = ""
    initiative.save()

    Notification.objects.create(
        user=initiative.author,
        message=(
            f'Ваша инициатива «{initiative.title}» опубликована.'
        )
    )

    AuditLog.objects.create(
        user=request.user,
        action=f'Опубликована инициатива «{initiative.title}»',
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")
    )
    messages.success(request, "Инициатива опубликована.")

    return redirect("moderation")

@login_required
@user_passes_test(is_moderator)
@require_POST
def reject_initiative(request, initiative_id):

    initiative = get_object_or_404(
        Initiative,
        id=initiative_id,
        status="moderation"
    )

    moderator_comment = request.POST.get(
        "moderator_comment",
        ""
    ).strip()

    if not moderator_comment:
        messages.error(request, "Укажите причину отклонения.")
        return redirect("moderation")

    initiative.status = "rejected"
    initiative.moderator_comment = moderator_comment
    initiative.save()

    Notification.objects.create(
        user=initiative.author,
        message=(
            f'Ваша инициатива «{initiative.title}» '
            f'отклонена. Причина: {moderator_comment}'
        )
    )

    AuditLog.objects.create(
        user=request.user,
        action=f'Отклонена инициатива «{initiative.title}»',
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")
    )
    messages.warning(request, "Инициатива отклонена.")

    return redirect("moderation")


@login_required
@user_passes_test(is_moderator)
@require_POST
def return_to_moderation(request, initiative_id):
    initiative = get_object_or_404(
        Initiative,
        id=initiative_id,
        status="published"
    )

    initiative.status = "moderation"
    initiative.save()

    AuditLog.objects.create(
        user=request.user,
        action=f'Инициатива «{initiative.title}» возвращена на модерацию',
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")
    )
    messages.info(request, "Инициатива возвращена на модерацию.")

    return redirect("moderation")
