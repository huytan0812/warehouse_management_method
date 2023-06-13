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
    path("import_shipment_details/<str:import_shipment_code>", views.import_shipment_details, name="import_shipment_details"),
    path("import_action", views.import_action, name="import_action"),
    path("export_shipments/<date:testing_date>", views.export_shipments, name="export_shipments"),
    path("import_action/save_and_continue/<str:import_shipment_code>", views.save_and_continue, name="save_and_continue"),
    path("import_action/save_and_complete/<str:import_shipment_code>", views.save_and_complete, name="save_and_complete"),
    path("import_action/import_purchase_update/<int:import_purchase_id>", views.import_purchase_update, name="import_purchase_update"),
    path("import_action/import_purchase_delete/<int:import_purchase_id>", views.import_purchase_delete, name="import_purchase_delete"),

    # decorators view
    path("activating_accounting_period", views.activating_accounting_period, name="activating_accounting_period"),
]