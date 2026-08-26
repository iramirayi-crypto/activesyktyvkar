from datetime import datetime, timedelta
import logging
from smtplib import SMTPException

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.core.mail import send_mail
from django.core.exceptions import NON_FIELD_ERRORS
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.decorators.http import require_POST

from comments.models import Comment
from initiatives.models import Initiative, Vote

from .forms import (
    AvatarForm,
    DeleteAccountForm,
    EmailChangeRequestForm,
    EmailVerificationForm,
    ProfileForm,
    RegistrationForm,
)
from .models import AuditLog, Notification, Profile
from .services import (
    EmailDeliveryError,
    clear_email_verification,
    issue_email_verification,
    soft_delete_user,
    verification_code_status,
)


logger = logging.getLogger(__name__)
EMAIL_DELIVERY_ERROR_MESSAGE = "Не удалось отправить письмо. Попробуйте ещё раз позже."


class UserPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    success_message = "Пароль успешно изменён."

# Регистрация
def register(request):

    if request.method == "POST":
        form = RegistrationForm(request.POST)
    else:
        form = RegistrationForm()

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.personal_data_consent = True
                profile.personal_data_consent_at = timezone.now()
                profile.save(
                    update_fields=[
                        "personal_data_consent",
                        "personal_data_consent_at",
                    ]
                )
                issue_email_verification(
                    request,
                    user=user,
                    purpose="registration",
                )
        except EmailDeliveryError:
            clear_email_verification(request)
            messages.error(request, EMAIL_DELIVERY_ERROR_MESSAGE)
        else:
            messages.info(request, "Код подтверждения отправлен на указанный Email.")
            return redirect("verify_email")

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )


def verify_email(request):
    user_id = request.session.get("email_verification_user_id")
    if not user_id:
        messages.error(request, "Начните регистрацию заново.")
        return redirect("register")

    user = User.objects.filter(pk=user_id, is_active=False).first()
    if user is None:
        clear_email_verification(request)
        return redirect("login")

    form = EmailVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        status = verification_code_status(
            request,
            form.cleaned_data["code"],
            purpose="registration",
            user=user,
        )
        if status == "valid":
            user.is_active = True
            user.save(update_fields=["is_active"])
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.email_verified_at = timezone.now()
            profile.save(update_fields=["email_verified_at"])
            clear_email_verification(request)
            messages.success(request, "Email подтверждён. Теперь можно войти.")
            return redirect("login")
        elif status == "expired":
            form.add_error(
                "code",
                "Срок действия кода истёк. Запросите новый код.",
            )
        else:
            form.add_error("code", "Неверный код подтверждения.")

    return render(
        request,
        "accounts/verify_email.html",
        {"form": form, "email": user.email},
    )


@require_POST
def resend_email_verification(request):
    user_id = request.session.get("email_verification_user_id")
    purpose = request.session.get("email_verification_purpose", "registration")
    user = User.objects.filter(pk=user_id).first()

    if user is None or purpose not in {"registration", "email_change"}:
        clear_email_verification(request)
        messages.error(request, "Запросите новый код подтверждения заново.")
        return redirect("register")
    if purpose == "email_change" and request.user != user:
        clear_email_verification(request)
        return redirect("login")

    recipient = (
        request.session.get("email_verification_pending_email")
        if purpose == "email_change"
        else user.email
    )
    if not recipient:
        clear_email_verification(request)
        messages.error(request, "Не удалось определить Email для отправки.")
        return redirect("profile" if request.user.is_authenticated else "register")

    try:
        sent = issue_email_verification(
            request,
            user=user,
            purpose=purpose,
            recipient=recipient,
            respect_cooldown=True,
        )
    except EmailDeliveryError:
        messages.error(request, EMAIL_DELIVERY_ERROR_MESSAGE)
        return redirect(
            "verify_email_change" if purpose == "email_change" else "verify_email"
        )
    if sent:
        messages.success(request, "Новый код подтверждения отправлен.")
    else:
        messages.info(request, "Повторную отправку можно запросить через минуту.")
    return redirect(
        "verify_email_change" if purpose == "email_change" else "verify_email"
    )


# Вход
def user_login(request):

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            data=request.POST
        )
    else:
        form = AuthenticationForm()

    form.fields["username"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Имя пользователя"
    })

    form.fields["password"].widget.attrs.update({
        "class": "form-control",
        "placeholder": "Пароль"
    })

    if request.method == "POST" and form.is_valid():
        login(
            request,
            form.get_user()
        )
        return redirect("home")

    if request.method == "POST" and not form.is_valid():
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        candidate = User.objects.filter(username=username).first()
        if candidate and candidate.check_password(password):
            profile = candidate.profile
            if profile.is_blocked:
                form.errors.pop(NON_FIELD_ERRORS, None)
                if profile.is_permanently_blocked:
                    error = (
                        "Ваш аккаунт заблокирован. "
                        f"Причина: {profile.block_reason} "
                        "По вопросам блокировки обратитесь: "
                        "active.syktyvkar@mail.ru"
                    )
                else:
                    blocked_until = timezone.localtime(
                        profile.blocked_until
                    ).strftime("%d.%m.%Y")
                    error = (
                        f"Ваш аккаунт временно заблокирован до {blocked_until}. "
                        f"Причина: {profile.block_reason}"
                    )
                form.add_error(None, error)

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )


# Выход
def user_logout(request):
    logout(request)
    return redirect("home")


# Профиль пользователя
@login_required
def profile(request):

    return render(
        request,
        "accounts/profile.html",
        {"delete_form": DeleteAccountForm(user=request.user)},
    )


# Редактирование профиля
@login_required
def edit_profile(request):

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Профиль сохранён.")
            return redirect("profile")

    else:

        form = ProfileForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "form": form
        }
    )


@login_required
def change_email(request):
    form = EmailChangeRequestForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            issue_email_verification(
                request,
                user=request.user,
                purpose="email_change",
                recipient=form.cleaned_data["new_email"],
            )
        except EmailDeliveryError:
            messages.error(request, EMAIL_DELIVERY_ERROR_MESSAGE)
        else:
            messages.info(request, "Код подтверждения отправлен на новый Email.")
            return redirect("verify_email_change")
    return render(request, "accounts/change_email.html", {"form": form})


@login_required
def verify_email_change(request):
    pending_email = request.session.get("email_verification_pending_email")
    purpose = request.session.get("email_verification_purpose")
    user_id = request.session.get("email_verification_user_id")
    if purpose != "email_change" or user_id != request.user.pk or not pending_email:
        messages.error(request, "Сначала укажите новый Email.")
        return redirect("change_email")

    form = EmailVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        status = verification_code_status(
            request,
            form.cleaned_data["code"],
            purpose="email_change",
            user=request.user,
        )
        if status == "valid":
            email_is_taken = User.objects.filter(
                email__iexact=pending_email
            ).exclude(pk=request.user.pk).exists()
            if email_is_taken:
                clear_email_verification(request)
                messages.error(
                    request,
                    "Этот Email уже занят. Укажите другой адрес.",
                )
                return redirect("change_email")

            old_email = request.user.email
            request.user.email = pending_email
            request.user.save(update_fields=["email"])
            profile = request.user.profile
            profile.email_verified_at = timezone.now()
            profile.save(update_fields=["email_verified_at"])
            clear_email_verification(request)
            old_email_notification_failed = False
            if old_email:
                try:
                    send_mail(
                        "Email аккаунта изменён — Активный Сыктывкар",
                        (
                            "Адрес электронной почты вашего аккаунта в проекте "
                            "«Активный Сыктывкар» был изменён."
                        ),
                        None,
                        [old_email],
                    )
                except (SMTPException, OSError):
                    old_email_notification_failed = True
                    logger.exception(
                        "Не удалось отправить уведомление об изменении Email."
                    )
            messages.success(
                request,
                "Адрес электронной почты успешно изменён.",
            )
            if old_email_notification_failed:
                messages.error(request, EMAIL_DELIVERY_ERROR_MESSAGE)
            return redirect("profile")
        if status == "expired":
            form.add_error(
                "code",
                "Срок действия кода истёк. Запросите новый код.",
            )
        else:
            form.add_error("code", "Неверный код подтверждения.")

    return render(
        request,
        "accounts/verify_email.html",
        {
            "form": form,
            "email": pending_email,
            "email_change": True,
        },
    )


@login_required
@require_POST
def delete_account(request):
    if request.user.is_superuser:
        messages.error(request, "Superuser нельзя удалить через профиль.")
        return redirect("profile")

    form = DeleteAccountForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(
            request,
            "accounts/profile.html",
            {"delete_form": form, "show_delete_modal": True},
            status=400,
        )

    user = request.user
    soft_delete_user(target=user, actor=user, request=request)
    logout(request)
    messages.success(request, "Ваш аккаунт удалён.")
    return redirect("home")

   # Редактирование фотографии
@login_required
def edit_avatar(request):

    profile = request.user.profile

    if request.method == "POST":

        form = AvatarForm(
            request.POST,
            request.FILES,
            instance=profile
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Фотография профиля обновлена.")
            return redirect("profile")

    else:

        form = AvatarForm(
            instance=profile
        )

    return render(
        request,
        "accounts/edit_avatar.html",
        {
            "form": form
        }
    )


@login_required
@require_POST
def delete_avatar(request):
    profile = request.user.profile
    if profile.avatar:
        profile.avatar.delete(save=False)
        profile.avatar = None
        profile.save(update_fields=["avatar"])
        messages.success(request, "Фотография профиля удалена.")
    return redirect("edit_avatar")


# Согласие на обработку персональных данных
def personal_data_consent(request):
    return render(
        request,
        "accounts/personal_data_consent.html"
    )


# Политика обработки персональных данных
def privacy_policy(request):
    return render(
        request,
        "accounts/privacy_policy.html"
    )

# Административная страница
@login_required
def admin_dashboard(request):

    # Доступ только для администратора
    if not request.user.is_superuser:
        return redirect("home")

    users_count = User.objects.count()

    initiatives_count = Initiative.objects.count()

    published_count = Initiative.objects.filter(
        status="published"
    ).count()

    moderation_count = Initiative.objects.filter(
        status="moderation"
    ).count()

    rejected_count = Initiative.objects.filter(
        status="rejected"
    ).count()

    votes_count = Vote.objects.count()
    comments_count = Comment.objects.count()

    now = timezone.localtime()
    month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    new_users_month_count = User.objects.filter(
        date_joined__gte=month_start
    ).count()

    new_initiatives_month_count = Initiative.objects.filter(
        created_at__gte=month_start
    ).count()

    today = timezone.localdate()
    first_chart_day = today - timedelta(days=13)
    first_chart_datetime = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    ) - timedelta(days=13)
    chart_days = [
        first_chart_day + timedelta(days=offset)
        for offset in range(14)
    ]

    initiatives_by_day_rows = Initiative.objects.filter(
        created_at__gte=first_chart_datetime
    ).annotate(
        day=TruncDate("created_at")
    ).values(
        "day"
    ).annotate(
        count=Count("id")
    ).order_by("day")

    users_by_day_rows = User.objects.filter(
        date_joined__gte=first_chart_datetime
    ).annotate(
        day=TruncDate("date_joined")
    ).values(
        "day"
    ).annotate(
        count=Count("id")
    ).order_by("day")

    initiatives_by_day = {
        row["day"]: row["count"]
        for row in initiatives_by_day_rows
    }
    users_by_day = {
        row["day"]: row["count"]
        for row in users_by_day_rows
    }

    chart_labels = [day.strftime("%d.%m") for day in chart_days]

    status_chart_data = {
        "labels": ["Опубликовано", "На модерации", "Отклонено"],
        "values": [published_count, moderation_count, rejected_count],
    }
    initiatives_chart_data = {
        "labels": chart_labels,
        "values": [initiatives_by_day.get(day, 0) for day in chart_days],
    }
    users_chart_data = {
        "labels": chart_labels,
        "values": [users_by_day.get(day, 0) for day in chart_days],
    }

    return render(
        request,
        "accounts/admin_dashboard.html",
        {
            "users_count": users_count,
            "initiatives_count": initiatives_count,
            "published_count": published_count,
            "moderation_count": moderation_count,
            "rejected_count": rejected_count,
            "votes_count": votes_count,
            "comments_count": comments_count,
            "new_users_month_count": new_users_month_count,
            "new_initiatives_month_count": new_initiatives_month_count,
            "status_chart_data": status_chart_data,
            "initiatives_chart_data": initiatives_chart_data,
            "users_chart_data": users_chart_data,
        }
    )


# Журнал аудита
def parse_audit_date(value):
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        return None


@login_required
def audit_log(request):
    if not request.user.is_superuser:
        return redirect("home")

    logs = AuditLog.objects.select_related("user").all()

    user_query = request.GET.get("user", "").strip()
    action_query = request.GET.get("action", "").strip()
    date_from_value = request.GET.get("date_from", "").strip()
    date_to_value = request.GET.get("date_to", "").strip()

    if user_query:
        logs = logs.filter(user__username__icontains=user_query)

    if action_query:
        logs = logs.filter(action__icontains=action_query)

    date_from = parse_audit_date(date_from_value)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)

    date_to = parse_audit_date(date_to_value)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    return render(
        request,
        "accounts/audit_log.html",
        {
            "logs": logs,
            "user_query": user_query,
            "action_query": action_query,
            "date_from": date_from_value,
            "date_to": date_to_value,
        }
    )


# Уведомления
@login_required
def notifications(request):

    notifications = Notification.objects.filter(
        user=request.user
    )

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True
    )

    return render(
        request,
        "accounts/notifications.html",
        {
            "notifications": notifications
        }
    )

# Правила публикации комментариев
def comment_rules(request):
    return render(
        request,
        "accounts/comment_rules.html"
    )
