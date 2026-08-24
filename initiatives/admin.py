from django.contrib import admin
from .models import Category, Initiative, Vote

from django.contrib import admin
from .models import Category, Initiative, Vote


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "category",
        "status",
        "created_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = ("title", "description", "author__username")
    ordering = ("-created_at",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "initiative",
        "user",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("initiative__title", "user__username")
    ordering = ("-created_at",)
