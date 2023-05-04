from django.urls import path, register_converter
from . import views
from . converters import DateConverter

register_converter(DateConverter, "date")

urlpatterns = [
    path("", views.index, name="index"),
    path("date_handling", views.date_handling, name="date_handling"),
    path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
    path("keep_current_method", views.keep_current_method, name="keep_current_method"),
    path("import_shipments/<date:testing_date>", views.import_shipments, name="import_shipments"),
    path("export_shipments/<date:testing_date>", views.export_shipments, name="export_shipments"),
]