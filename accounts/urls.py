from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from . import views
from .forms import SafePasswordResetForm

urlpatterns = [

    path(
        "login/",
        views.user_login,
        name="login"
    ),

    path(
        "register/",
        views.register,
        name="register"
    ),

    path(
        "verify-email/",
        views.verify_email,
        name="verify_email"
    ),

    path(
        "verify-email/resend/",
        views.resend_email_verification,
        name="resend_email_verification"
    ),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=SafePasswordResetForm,
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset"
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),

    path(
        "password-change/",
        views.UserPasswordChangeView.as_view(
            template_name="accounts/password_change_form.html",
            success_url=reverse_lazy("password_change_done"),
        ),
        name="password_change"
    ),

    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html"
        ),
        name="password_change_done"
    ),

    path(
        "personal-data-consent/",
        views.personal_data_consent,
        name="personal_data_consent"
    ),

    path(
        "privacy-policy/",
        views.privacy_policy,
        name="privacy_policy"
    ),

    path(
        "logout/",
        views.user_logout,
        name="logout"
    ),

    path(
        "profile/",
        views.profile,
        name="profile"
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile"
    ),

    path(
        "profile/email/change/",
        views.change_email,
        name="change_email"
    ),

    path(
        "profile/email/verify/",
        views.verify_email_change,
        name="verify_email_change"
    ),

    path(
        "profile/delete/",
        views.delete_account,
        name="delete_account"
    ),

    path(
        "profile/avatar/",
        views.edit_avatar,
        name="edit_avatar"
    ),

    path(
        "profile/avatar/delete/",
        views.delete_avatar,
        name="delete_avatar"
    ),

    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin_dashboard"
    ),
    path(
        "admin-dashboard/backup/",
        views.create_database_backup,
        name="create_database_backup"
    ),
    path(
        "audit-log/",
        views.audit_log,
        name="audit_log"
    ),
    path(
    "notifications/",
    views.notifications,
    name="notifications"
    ),
    path(
    "comment-rules/",
    views.comment_rules,
    name="comment_rules"
    ),
]
