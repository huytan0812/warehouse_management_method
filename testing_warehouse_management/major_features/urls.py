from django.urls import path, register_converter
from . import views
from . converters import DateConverter

register_converter(DateConverter, "date")

urlpatterns = [
    path("", views.index, name="index"),
    path("date_handling", views.date_handling, name="date_handling"),
    path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
    path("keep_current_method", views.keep_current_method, name="keep_current_method"),

    # Import Section
    path("import_shipments", views.import_shipments, name="import_shipments"),
    path("import_shipment_details/<str:import_shipment_code>", views.import_shipment_details, name="import_shipment_details"),
    path("import_action", views.import_action, name="import_action"),
    path("import_action/save_and_continue/<str:import_shipment_code>", views.save_and_continue, name="save_and_continue"),
    path("import_action/save_and_complete/<str:import_shipment_code>", views.save_and_complete, name="save_and_complete"),
    path("import_action/import_purchase_update/<int:import_purchase_id>", views.import_purchase_update, name="import_purchase_update"),
    path("import_action/import_purchase_delete/<int:import_purchase_id>", views.import_purchase_delete, name="import_purchase_delete"),
    path("delete_unfinish_import_shipment/<str:import_shipment_code>", views.delete_unfinish_import_shipment, name="delete_unfinish_import_shipment"),

    # Export section
    path("export_shipments", views.export_shipments, name="export_shipments"),
    path("export_action", views.export_action, name="export_action"),
    path("export_action/export_order_action/<str:export_shipment_code>", views.export_order_action, name="export_order_action"),
    path("export_action/type_of_inventory/<int:export_order_id>", views.choose_type_of_inventory, name="choose_type_of_inventory"),

    path("export_action/export_by_starting_inventory/<int:export_order_id>/product=<str:product>", 
         views.export_by_starting_inventory, 
         name="export_by_starting_inventory"),

    path("export_action/export_by_current_accounting_period_inventory/<int:export_order_id>/product=<str:product>", 
         views.export_by_current_accounting_period_inventory, 
         name="export_by_current_accounting_period_inventory"),

    path("export_action/actual_method_by_name/<int:export_order_id>/product=<str:product>/type=<str:type>", 
         views.actual_method_by_name_export_action, 
         name="actual_method_by_name_export_action"),

    # Reports section
    path("reports", views.reports, name="reports"),
    path("reports/revenue", views.reports_revenue, name="reports_revenue"),
    path("reports/import_section", views.reports_import_section, name="reports_import_section"),
    path("reports/export_section", views.reports_export_section, name="reports_export_section"),

    # decorators view
    path("activating_accounting_period", views.activating_accounting_period, name="activating_accounting_period"),
]