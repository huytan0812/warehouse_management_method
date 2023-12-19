from django.urls import path, register_converter
from . import views
from . import reports_views
from . import inventory_data_views
from . converters import DateConverter

register_converter(DateConverter, "date")

urlpatterns = [
     path("", views.index, name="index"),
     path("login", views.login_view, name="login"),
     path("logout", views.logout_view, name="logout"),
     path("register", views.register, name="register"),
     path("user_activities", views.user_activities, name="user_activities"),

     path("date_handling", views.date_handling, name="date_handling"),
     path("apply_warehouse_management", views.apply_warehouse_management, name="apply_warehouse_management"),
     path("keep_current_method", views.keep_current_method, name="keep_current_method"),

     # Categories Section
     path("categories", views.categories, name="categories"),
     path("categories/add_category", views.add_category, name="add_category"),

     # Products Section
     path("products", views.products, name="products"),
     path("products/add_product", views.add_product, name="add_product"),
     path("products/edit_product/product_id=<str:product_id>", views.edit_product, name="edit_product"),

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
     path("export_shipment_details/<str:export_shipment_code>", views.export_shipment_details, name="export_shipment_details"),
     path("export_action", views.export_action, name="export_action"),
     path("export_action_complete/<str:export_shipment_code>", views.export_action_complete, name="export_action_complete"),
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
     
     path("export_action/complete_export_order_by_inventory/<int:export_order_id>",
          views.complete_export_order_by_inventory,
          name="complete_export_order_by_inventory"),

     path("export_action/weighted_average/<int:export_order_id>",
          views.weighted_average,
          name="weighted_average"),

     # Reports section
     path("reports/revenue", reports_views.reports_revenue, name="reports_revenue"),
     path("reports/gross_profits", reports_views.reports_gross_profits, name="reports_gross_profits"),
     path("reports/import_section", reports_views.reports_import_section, name="reports_import_section"),
     path("reports/export_section", reports_views.reports_export_section, name="reports_export_section"),

     # Inventory Data section
     path("inventory_data", inventory_data_views.inventory_data, name="inventory_data"),
     path("inventory_data/export_data_to_excel", inventory_data_views.export_data_to_excel, name="export_data_to_excel"),

     # decorators view
     path("activating_accounting_period", views.activating_accounting_period, name="activating_accounting_period"),
]