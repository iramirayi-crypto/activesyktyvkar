from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count 
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Initiative, Vote, Category
from comments.models import Comment
from attachments.models import Attachment
from accounts.models import AuditLog
from accounts.models import Notification

# Список опубликованных инициатив
def initiative_list(request):

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")

    # Только опубликованные инициативы
    initiatives = Initiative.objects.filter(
        status="published"
    )

    # Поиск
    if query:
        initiatives = initiatives.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    # Фильтр по категории
    if category.isdigit():
        initiatives = initiatives.filter(
            category__id=category
        )
    elif category:
        category = ""

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

    # Неопубликованную инициативу может смотреть
    # только её автор или модератор
    if initiative.status != "published":

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

            # Передаём в шаблон, является ли пользователь модератором
            "is_moderator": (
                request.user.is_authenticated
                and is_moderator(request.user)
            ),
        }
    )

# Голосование за инициативу
def vote_initiative(request, pk):

    # Если пользователь не вошел в систему
    if not request.user.is_authenticated:
        return redirect("login")

    # Получаем инициативу
    initiative = get_object_or_404(
        Initiative,
        pk=pk
    )

    # Проверяем, голосовал ли пользователь
    vote = Vote.objects.filter(
        initiative=initiative,
        user=request.user
    )

    # Если голос уже есть — удаляем его
    if vote.exists():
        vote.delete()

    # Иначе создаем новый голос
    else:
        Vote.objects.create(
            initiative=initiative,
            user=request.user
        )

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
        text = request.POST.get("text", "").strip()

        if not text:
            messages.error(request, "Комментарий не может быть пустым.")
            return redirect("edit_comment", pk=pk)

        if len(text) > 1000:
            messages.error(
                request,
                "Комментарий не должен превышать 1000 символов."
            )
            return redirect("edit_comment", pk=pk)

        comment.text = text
        comment.save()

        return redirect(
            "initiative_detail",
            pk=comment.initiative.id
        )

    return render(
        request,
        "initiatives/edit_comment.html",
        {
            "comment": comment
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
        title = request.POST.get("title")
        description = request.POST.get("description")
        location = request.POST.get("location")
        category_id = request.POST.get("category")
        uploaded_file = request.FILES.get("file")

        category = get_object_or_404(
            Category,
            id=category_id
        )

        initiative = Initiative.objects.create(
            author=request.user,
            title=title,
            description=description,
            location=location,
            category=category,
            status="moderation"
        )

        # Сохраняем загруженный файл
        if uploaded_file:
            Attachment.objects.create(
                initiative=initiative,
                file=uploaded_file
            )

        AuditLog.objects.create(
            user=request.user,
            action=f'Создана инициатива «{initiative.title}»',
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        return redirect("my_initiatives")

    categories = Category.objects.all()

    return render(
        request,
        "initiatives/create_initiative.html",
        {
            "categories": categories
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

        initiative.title = request.POST.get("title")
        initiative.description = request.POST.get("description")
        initiative.location = request.POST.get("location")

        category_id = request.POST.get("category")
        initiative.category = get_object_or_404(
            Category,
            id=category_id
        )

        initiative.status = "moderation"
        if was_rejected:
            initiative.moderator_comment = None
        initiative.save()

        AuditLog.objects.create(
            user=request.user,
            action=f'Отредактирована инициатива «{initiative.title}»',
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        return redirect("my_initiatives")

    categories = Category.objects.all()

    return render(
        request,
        "initiatives/edit_initiative.html",
        {
            "initiative": initiative,
            "categories": categories
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
        status="moderation"
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
        },
    )


@login_required
@user_passes_test(is_moderator)
@require_POST
def publish_initiative(request, initiative_id):

    initiative = get_object_or_404(
        Initiative,
        id=initiative_id,
        status="moderation"
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

    return redirect("moderation")
