from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("ending_accounting_period", views.ending_accounting_period, name="ending_accounting_period"),
    path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
]