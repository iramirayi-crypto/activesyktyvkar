from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from .models import Initiative, Vote, Category
from comments.models import Comment
from attachments.models import Attachment

# Список опубликованных инициатив
def initiative_list(request):

    # Получаем текст поиска
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")

    # Показываем только опубликованные инициативы
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
    if category:
        initiatives = initiatives.filter(
            category__id=category
        )

    # Получаем первое изображение
    for initiative in initiatives:
        initiative.image = Attachment.objects.filter(
            initiative=initiative
        ).first()

    return render(
        request,
        "initiatives/list.html",
        {
            "initiatives": initiatives,
            "query": query,
            "category": category,
            "categories": Category.objects.all(),
        },
    )

# Страница одной инициативы
def initiative_detail(request, pk):

    initiative = get_object_or_404(
        Initiative,
        pk=pk
    )

    # Неопубликованную инициативу может смотреть
    # только её автор
    if initiative.status != "published":
        if not request.user.is_authenticated or initiative.author != request.user:
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


# Удаление комментария
def delete_comment(request, pk):

    # Если пользователь не вошел
    if not request.user.is_authenticated:
        return redirect("login")

    # Получаем комментарий
    comment = get_object_or_404(Comment, pk=pk)

    # Проверяем права
    if request.user == comment.author or request.user.is_superuser:

        initiative_id = comment.initiative.id
        comment.delete()

        return redirect(
            "initiative_detail",
            pk=initiative_id
        )

    return redirect(
        "initiative_detail",
        pk=comment.initiative.id
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

        comment.text = request.POST.get("text")
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
def my_initiatives(request):
    initiatives = Initiative.objects.filter(
        author=request.user
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