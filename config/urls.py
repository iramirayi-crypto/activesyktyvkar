from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "Администрирование"
admin.site.site_title = "Активный Сыктывкар"
admin.site.index_title = "Панель управления"
admin.site.site_url = "/" 

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("initiatives/", include("initiatives.urls")),
    path("accounts/", include("accounts.urls")),
    path("comments/", include("comments.urls")),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)