from django.shortcuts import render, get_object_or_404, redirect

from .models import Initiative, Vote
from comments.models import Comment
from attachments.models import Attachment


# Список опубликованных инициатив
def initiative_list(request):

    # Получаем текст поиска
    query = request.GET.get("q", "")

    # Показываем только опубликованные инициативы
    initiatives = Initiative.objects.filter(
        status="published"
    )

    # Если пользователь ввел запрос
    if query:
        initiatives = initiatives.filter(
            title__icontains=query
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
        },
    )


# Страница одной инициативы
def initiative_detail(request, pk):

    # Получаем опубликованную инициативу
    initiative = get_object_or_404(
        Initiative,
        pk=pk,
        status="published"
    )

    # Получаем изображения инициативы
    attachments = Attachment.objects.filter(
        initiative=initiative
    )

    # Подсчитываем количество голосов
    votes_count = Vote.objects.filter(
        initiative=initiative
    ).count()

    # Проверяем, голосовал ли пользователь
    user_voted = False

    if request.user.is_authenticated:
        user_voted = Vote.objects.filter(
            initiative=initiative,
            user=request.user
        ).exists()

    # Получаем комментарии к инициативе
    comments = Comment.objects.filter(
        initiative=initiative
    )

    # Передаем данные в шаблон
    return render(
        request,
        "initiatives/detail.html",
        {
            "initiative": initiative,
            "attachments": attachments,
            "votes_count": votes_count,
            "user_voted": user_voted,
            "comments": comments,
        },
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
