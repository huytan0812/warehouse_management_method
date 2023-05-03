from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("date_handling", views.date_handling, name="date_handling"),
    path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
    path("keep_current_method", views.keep_current_method, name="keep_current_method"),
    path("import_shipments", views.import_shipments, name="import_shipments"),
    path("export_shipments", views.export_shipments, name="export_shipments"),
]