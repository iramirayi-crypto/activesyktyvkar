from django.urls import path

from . import views

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
        "profile/avatar/",
        views.edit_avatar,
        name="edit_avatar"
    ),

    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin_dashboard"
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

]
