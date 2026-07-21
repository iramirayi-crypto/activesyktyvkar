from django.contrib import admin
from .models import Category, Initiative


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title",)