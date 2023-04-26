from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("date_handling", views.date_handling, name="date_handling"),
    path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
]