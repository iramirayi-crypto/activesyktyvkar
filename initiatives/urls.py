from django.urls import path
from . import views

urlpatterns = [
    path("", views.initiative_list, name="initiative_list"),
]