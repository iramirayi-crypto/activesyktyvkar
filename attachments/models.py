from django.db import models
from initiatives.models import Initiative


class Attachment(models.Model):
    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.CASCADE,
        verbose_name="Инициатива"
    )

    file = models.FileField(
        "Файл",
        upload_to="attachments/"
    )

    uploaded_at = models.DateTimeField(
        "Дата загрузки",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file.name