from django.db import models
from django.contrib.auth.models import User
from initiatives.models import Initiative


class Comment(models.Model):
    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.CASCADE,
        verbose_name="Инициатива"
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор"
    )

    text = models.TextField("Комментарий")

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author} — {self.initiative}"


class CommentDeletion(models.Model):
    comment_author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="comment_deletions"
    )

    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.CASCADE
    )

    comment_text = models.TextField()

    reason = models.TextField(
        "Причина удаления"
    )

    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="deleted_comments"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Удаление комментария"
        verbose_name_plural = "Удаления комментариев"
        ordering = ["-created_at"]