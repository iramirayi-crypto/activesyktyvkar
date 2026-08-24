from django.contrib import admin
from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "initiative",
        "uploaded_at",
    )

    list_filter = (
        "uploaded_at",
    )

    search_fields = (
        "initiative__title",
        "file",
    )

    ordering = ("-uploaded_at",)
