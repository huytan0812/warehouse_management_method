from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("date_details", views.date_details, name="date_details"),
]