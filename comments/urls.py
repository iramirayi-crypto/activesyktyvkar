from django.urls import path
from . import views

urlpatterns = [

    # Добавление комментария
    path(
        "<int:pk>/add/",
        views.add_comment,
        name="add_comment"
    ),

    # Модерация комментариев
    path(
        "moderation/",
        views.moderation_comments,
        name="moderation_comments"
    ),

    # Удаление комментария
    path(
        "<int:pk>/delete/",
        views.delete_comment,
        name="delete_comment"
    ),
]