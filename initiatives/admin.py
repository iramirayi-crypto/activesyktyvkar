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
    list_display = ("id", "title", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "initiative",
        "user",
        "created_at",
    )
    list_filter = ("created_at",)