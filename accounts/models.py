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