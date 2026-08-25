from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from comments.models import Comment
from initiatives.models import Initiative, Vote

from .forms import AvatarForm, ProfileForm, RegistrationForm
from .models import AuditLog, Notification, Profile


class UserPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    success_message = "Пароль успешно изменён."

# Регистрация
def register(request):

    if request.method == "POST":
        form = RegistrationForm(request.POST)
    else:
        form = RegistrationForm()

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            login(request, user)
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.personal_data_consent = True
            profile.personal_data_consent_at = timezone.now()
            profile.save(
                update_fields=[
                    "personal_data_consent",
                    "personal_data_consent_at",
                ]
            )

        messages.success(request, "Регистрация успешно завершена.")
        return redirect("home")

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
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
        "accounts/profile.html"
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

    date_from = parse_date(date_from_value)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)

    date_to = parse_date(date_to_value)
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
