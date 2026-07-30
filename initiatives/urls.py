from django.urls import path
from . import views

urlpatterns = [
    path("", views.initiative_list, name="initiative_list"),
    path("<int:pk>/", views.initiative_detail, name="initiative_detail"),
    path("<int:pk>/vote/", views.vote_initiative, name="vote_initiative"),
]