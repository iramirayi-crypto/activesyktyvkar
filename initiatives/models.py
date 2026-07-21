from django.db import models


class Category(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Initiative(models.Model):

    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("moderation", "На модерации"),
        ("published", "Опубликована"),
        ("rejected", "Отклонена"),
    ]

    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание")

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="Категория"
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="moderation"
    )

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Инициатива"
        verbose_name_plural = "Инициативы"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title