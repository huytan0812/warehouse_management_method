from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("date_details", views.date_details, name="date_details"),
    path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
]