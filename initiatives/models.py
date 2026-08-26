from django.db import models
from django.contrib.auth.models import User

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

    description = models.TextField(
    "Описание",
    blank=True
)

    location = models.TextField(
        "Место реализации",
        max_length=500,
        blank=True,
        null=True
    )

    latitude = models.DecimalField(
        "Широта",
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )

    longitude = models.DecimalField(
        "Долгота",
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )

    category = models.ForeignKey(
    Category,
    on_delete=models.CASCADE,
    verbose_name="Категория",
    blank=True,
    null=True
)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор",
        null=True,
        blank=True,
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="moderation"
    )

    moderator_comment = models.TextField(
    "Комментарий модератора",
    blank=True,
    null=True
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    is_hidden = models.BooleanField(
    default=False,
    verbose_name="Скрыта"
    )

    class Meta:
        verbose_name = "Инициатива"
        verbose_name_plural = "Инициативы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status"],
                name="initiative_status_idx"
            ),
            models.Index(
                fields=["created_at"],
                name="initiative_created_idx"
            ),
        ]

    def __str__(self):
        return self.title

class Vote(models.Model):
    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.CASCADE,
        verbose_name="Инициатива"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )

    created_at = models.DateTimeField(
        "Дата голосования",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Голос"
        verbose_name_plural = "Голоса"
        ordering = ["-created_at"]
        unique_together = ("initiative", "user")

    def __str__(self):
        return f"{self.user.username} → {self.initiative.title}"
