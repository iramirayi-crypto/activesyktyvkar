from django.contrib import admin
from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "initiative",
        "author",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "text",
        "author__username",
        "initiative__title",
    )

    ordering = ("-created_at",)
