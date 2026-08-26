from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from . import views


# Обработчики ошибок
handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"


# Настройки админ-панели
admin.site.site_header = "Администрирование"
admin.site.site_title = "Активный Сыктывкар"
admin.site.index_title = "Панель управления"
admin.site.site_url = "/"


urlpatterns = [
    path("", views.home, name="home"),

    path(
        "about/",
        views.about,
        name="about"
    ),

    path(
        "how-to-use/",
        views.how_to_use,
        name="how_to_use"
    ),

    path(
        "contacts/",
        views.contacts,
        name="contacts"
    ),

    path("admin/", admin.site.urls),

    path("initiatives/", include("initiatives.urls")),

    path("accounts/", include("accounts.urls")),

    path("comments/", include("comments.urls")),
]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)