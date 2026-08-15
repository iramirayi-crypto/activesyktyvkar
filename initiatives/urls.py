from django.urls import path
from . import views

urlpatterns = [
    path("", views.initiative_list, name="initiative_list"),
    path("<int:pk>/", views.initiative_detail, name="initiative_detail"),
    path("<int:pk>/vote/", views.vote_initiative, name="vote_initiative"),
    path("comment/<int:pk>/delete/", views.delete_comment, name="delete_comment"),
    path("comment/<int:pk>/edit/", views.edit_comment, name="edit_comment"),
    path("my-initiatives/", views.my_initiatives, name="my_initiatives"),
    path("create/", views.create_initiative, name="create_initiative"),
    path(
    "delete/<int:pk>/",
    views.delete_initiative,
    name="delete_initiative"
),
]