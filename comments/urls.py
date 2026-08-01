from django.urls import path
from . import views

urlpatterns = [
    path(
        "<int:pk>/add/",
        views.add_comment,
        name="add_comment"
    ),
]
