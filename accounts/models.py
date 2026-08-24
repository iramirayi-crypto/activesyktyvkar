from django.db import models
from django.contrib.auth.models import User


# Профиль пользователя
class Profile(models.Model):

    # Пользователь
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    # Аватар
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username


# Журнал аудита
class AuditLog(models.Model):

    # Кто совершил действие
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Пользователь"
    )

    # Описание действия
    action = models.CharField(
        max_length=255,
        verbose_name="Действие"
    )

    ip_address = models.GenericIPAddressField(
        "IP-адрес",
        blank=True,
        null=True
    )

    user_agent = models.TextField(
        "User-Agent",
        blank=True,
        default=""
    )

    # Дата и время действия
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата"
    )

    class Meta:
        verbose_name = "Запись журнала"
        verbose_name_plural = "Журнал аудита"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.action}"


# Уведомления
class Notification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    message = models.TextField(
        "Сообщение"
    )

    is_read = models.BooleanField(
        "Прочитано",
        default=False
    )

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.message}"
