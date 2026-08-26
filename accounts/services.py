from datetime import datetime, timedelta
import logging
import secrets
from smtplib import SMTPException

from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from initiatives.models import Initiative

from .models import AuditLog, Profile


logger = logging.getLogger(__name__)

VERIFICATION_TTL = timedelta(minutes=10)
VERIFICATION_RESEND_COOLDOWN = timedelta(seconds=60)
VERIFICATION_SESSION_KEYS = (
    "email_verification_user_id",
    "email_verification_code_hash",
    "email_verification_expires_at",
    "email_verification_issued_at",
    "email_verification_purpose",
    "email_verification_pending_email",
)


class EmailDeliveryError(Exception):
    """A user-facing email could not be delivered by the configured backend."""


def clear_email_verification(request):
    for key in VERIFICATION_SESSION_KEYS:
        request.session.pop(key, None)


def issue_email_verification(
    request,
    *,
    user,
    purpose,
    recipient=None,
    respect_cooldown=False,
):
    now = timezone.now()
    issued_at = request.session.get("email_verification_issued_at")
    if respect_cooldown and issued_at:
        next_allowed_at = datetime.fromtimestamp(
            issued_at,
            tz=timezone.get_current_timezone(),
        ) + VERIFICATION_RESEND_COOLDOWN
        if now < next_allowed_at:
            return False

    recipient = recipient or user.email
    code = f"{secrets.randbelow(1_000_000):06d}"
    if purpose == "email_change":
        subject = "Подтверждение нового адреса — Активный Сыктывкар"
        message = (
            "Для подтверждения нового Email в проекте «Активный Сыктывкар» "
            f"введите код: {code}\n\nКод действует 10 минут."
        )
    else:
        subject = "Код подтверждения — Активный Сыктывкар"
        message = (
            "Для подтверждения Email в проекте «Активный Сыктывкар» "
            f"введите код: {code}\n\nКод действует 10 минут."
        )

    try:
        send_mail(subject, message, None, [recipient])
    except (SMTPException, OSError) as error:
        logger.exception("Не удалось отправить письмо подтверждения Email.")
        raise EmailDeliveryError from error

    request.session["email_verification_user_id"] = user.pk
    request.session["email_verification_code_hash"] = make_password(code)
    request.session["email_verification_expires_at"] = int(
        (now + VERIFICATION_TTL).timestamp()
    )
    request.session["email_verification_issued_at"] = int(now.timestamp())
    request.session["email_verification_purpose"] = purpose
    if purpose == "email_change":
        request.session["email_verification_pending_email"] = recipient
    else:
        request.session.pop("email_verification_pending_email", None)

    return True


def verification_code_status(request, code, *, purpose, user):
    if request.session.get("email_verification_user_id") != user.pk:
        return "missing"
    if request.session.get("email_verification_purpose", "registration") != purpose:
        return "missing"

    code_hash = request.session.get("email_verification_code_hash")
    expires_at = request.session.get("email_verification_expires_at")
    if not code_hash or expires_at is None:
        return "missing"
    if timezone.now().timestamp() > expires_at:
        return "expired"
    if not check_password(code, code_hash):
        return "invalid"
    return "valid"


def audit_action(*, actor, action, request=None):
    return AuditLog.objects.create(
        user=actor,
        action=action,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )


@transaction.atomic
def block_user(*, target, actor, reason, duration, request=None):
    profile = Profile.objects.select_for_update().get(user=target)
    now = timezone.now()
    profile.block_reason = reason.strip()
    profile.is_permanently_blocked = duration == "permanent"
    profile.blocked_until = (
        None
        if profile.is_permanently_blocked
        else now + timedelta(days=int(duration))
    )
    target.is_active = False
    target.save(update_fields=["is_active"])
    profile.save(
        update_fields=[
            "block_reason",
            "is_permanently_blocked",
            "blocked_until",
        ]
    )
    period = (
        "бессрочно"
        if profile.is_permanently_blocked
        else f"до {timezone.localtime(profile.blocked_until):%d.%m.%Y %H:%M}"
    )
    audit_action(
        actor=actor,
        action=(
            f"Пользователь {target.username} заблокирован {period}. "
            f"Причина: {profile.block_reason}"
        ),
        request=request,
    )


@transaction.atomic
def unblock_user(*, target, actor, request=None, automatic=False):
    profile = Profile.objects.select_for_update().get(user=target)
    profile.blocked_until = None
    profile.block_reason = ""
    profile.is_permanently_blocked = False
    if not profile.is_deleted:
        target.is_active = True
        target.save(update_fields=["is_active"])
    profile.save(
        update_fields=[
            "blocked_until",
            "block_reason",
            "is_permanently_blocked",
        ]
    )
    action = (
        f"Автоматически завершена блокировка пользователя {target.username}"
        if automatic
        else f"Досрочно разблокирован пользователь {target.username}"
    )
    audit_action(actor=actor, action=action, request=request)


def release_expired_block(user):
    profile = user.profile
    if (
        not profile.is_deleted
        and not profile.is_permanently_blocked
        and profile.blocked_until is not None
        and profile.blocked_until <= timezone.now()
    ):
        unblock_user(target=user, actor=user, automatic=True)
        return True
    return False


@transaction.atomic
def soft_delete_user(*, target, actor, request=None, administratively=False):
    profile = Profile.objects.select_for_update().get(user=target)
    if profile.is_deleted:
        return

    original_username = target.username
    Initiative.objects.filter(author=target).exclude(
        status="published"
    ).update(is_hidden=True)

    if profile.avatar:
        profile.avatar.delete(save=False)
    profile.avatar = None
    profile.is_deleted = True
    profile.deleted_at = timezone.now()
    profile.blocked_until = None
    profile.block_reason = ""
    profile.is_permanently_blocked = False
    target.username = f"deleted_user_{target.pk}_{secrets.token_hex(4)}"
    target.email = ""
    target.first_name = ""
    target.last_name = ""
    target.is_active = False
    target.is_staff = False
    target.set_unusable_password()
    target.save(
        update_fields=[
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "password",
        ]
    )
    profile.save(
        update_fields=[
            "avatar",
            "is_deleted",
            "deleted_at",
            "blocked_until",
            "block_reason",
            "is_permanently_blocked",
        ]
    )
    target.groups.clear()
    target.user_permissions.clear()

    source = "Администратором удалён" if administratively else "Удалён"
    audit_action(
        actor=actor,
        action=f"{source} аккаунт пользователя {original_username}; опубликованные инициативы сохранены",
        request=request,
    )
