from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from .forms import BlockUserForm
from .models import AuditLog, Notification, Profile
from .services import block_user, soft_delete_user, unblock_user


admin.site.unregister(User)


class ProfileStatusInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    max_num = 1
    fields = (
        "personal_data_consent",
        "personal_data_consent_at",
        "email_verified_at",
        "is_permanently_blocked",
        "blocked_until",
        "block_reason",
        "is_deleted",
        "deleted_at",
    )
    readonly_fields = fields


@admin.register(User)
class ActiveUserAdmin(UserAdmin):
    change_form_template = "admin/auth/user/change_form.html"
    list_display = UserAdmin.list_display + (
        "account_status",
        "block_ends_at",
        "block_reason_display",
    )
    inlines = (ProfileStatusInline,)
    actions = None

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    @admin.display(description="Статус")
    def account_status(self, obj):
        if obj.profile.is_deleted:
            return "Удалён"
        if obj.profile.is_blocked:
            return "Заблокирован"
        if not obj.is_active:
            return "Неактивен"
        return "Активен"

    @admin.display(description="Блокировка до")
    def block_ends_at(self, obj):
        if obj.profile.is_permanently_blocked:
            return "Бессрочно"
        if obj.profile.blocked_until:
            return timezone.localtime(obj.profile.blocked_until).strftime(
                "%d.%m.%Y %H:%M"
            )
        return "—"

    @admin.display(description="Причина блокировки")
    def block_reason_display(self, obj):
        return obj.profile.block_reason or "—"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/block/",
                self.admin_site.admin_view(self.block_view),
                name="auth_user_block",
            ),
            path(
                "<path:object_id>/unblock/",
                self.admin_site.admin_view(self.unblock_view),
                name="auth_user_unblock",
            ),
            path(
                "<path:object_id>/soft-delete/",
                self.admin_site.admin_view(self.soft_delete_view),
                name="auth_user_soft_delete",
            ),
        ]
        return custom_urls + super().get_urls()

    def _target_or_forbidden(self, request, object_id):
        if not request.user.is_superuser:
            raise PermissionDenied
        target = get_object_or_404(User, pk=object_id)
        if target.is_superuser or target == request.user:
            self.message_user(
                request,
                "Это действие нельзя выполнить для superuser.",
                level=messages.ERROR,
            )
            return None
        return target

    def _change_url(self, target):
        return reverse("admin:auth_user_change", args=[target.pk])

    def block_view(self, request, object_id):
        target = self._target_or_forbidden(request, object_id)
        if target is None:
            return redirect("admin:auth_user_changelist")
        if target.profile.is_deleted:
            self.message_user(request, "Удалённый аккаунт нельзя блокировать.", level=messages.ERROR)
            return redirect(self._change_url(target))

        form = BlockUserForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            block_user(
                target=target,
                actor=request.user,
                reason=form.cleaned_data["reason"],
                duration=form.cleaned_data["duration"],
                request=request,
            )
            self.message_user(request, "Пользователь заблокирован.")
            return redirect(self._change_url(target))
        return TemplateResponse(
            request,
            "admin/accounts/user_action_confirmation.html",
            {
                **self.admin_site.each_context(request),
                "title": "Блокировка пользователя",
                "target": target,
                "form": form,
                "action_label": "Заблокировать",
                "warning": "Пользователь временно не сможет войти. Его данные и публикации сохранятся.",
                "cancel_url": self._change_url(target),
            },
        )

    def unblock_view(self, request, object_id):
        target = self._target_or_forbidden(request, object_id)
        if target is None:
            return redirect("admin:auth_user_changelist")
        if target.profile.is_deleted:
            self.message_user(request, "Удалённый аккаунт нельзя разблокировать.", level=messages.ERROR)
            return redirect(self._change_url(target))
        if request.method == "POST":
            unblock_user(target=target, actor=request.user, request=request)
            self.message_user(request, "Пользователь разблокирован.")
            return redirect(self._change_url(target))
        return TemplateResponse(
            request,
            "admin/accounts/user_action_confirmation.html",
            {
                **self.admin_site.each_context(request),
                "title": "Разблокировка пользователя",
                "target": target,
                "action_label": "Разблокировать",
                "warning": "Пользователь снова сможет войти в аккаунт.",
                "cancel_url": self._change_url(target),
            },
        )

    def soft_delete_view(self, request, object_id):
        target = self._target_or_forbidden(request, object_id)
        if target is None:
            return redirect("admin:auth_user_changelist")
        if request.method == "POST":
            soft_delete_user(
                target=target,
                actor=request.user,
                request=request,
                administratively=True,
            )
            self.message_user(
                request,
                "Аккаунт обезличен и удалён. Опубликованные инициативы сохранены.",
            )
            return redirect("admin:auth_user_changelist")
        return TemplateResponse(
            request,
            "admin/accounts/user_action_confirmation.html",
            {
                **self.admin_site.each_context(request),
                "title": "Удаление пользователя",
                "target": target,
                "action_label": "Удалить пользователя",
                "is_delete": True,
                "warning": "Опубликованные инициативы пользователя будут сохранены. Персональные данные будут обезличены, а вход станет невозможен.",
                "cancel_url": self._change_url(target),
            },
        )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "personal_data_consent",
        "personal_data_consent_at",
        "email_verified_at",
        "is_permanently_blocked",
        "blocked_until",
        "is_deleted",
    )
    list_filter = (
        "personal_data_consent",
        "is_permanently_blocked",
        "is_deleted",
    )
    search_fields = ("user__username", "user__email")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "ip_address", "created_at")
    list_filter = ("user", "created_at")
    search_fields = ("user__username", "action")
    ordering = ("-created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "message")
    ordering = ("-created_at",)
