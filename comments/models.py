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