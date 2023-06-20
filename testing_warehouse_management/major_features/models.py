from django.db import models

# Create your models here.
class WarehouseManagementMethod(models.Model):
    name = models.TextField(null=False, blank=False, default="", max_length=1000)
    is_currently_applied = models.BooleanField(null=True, blank=True, default=False)

    def __str__(self):
        return f"{self.name}"
    
class AccoutingPeriod(models.Model):
    """
    The creation of this entity is ensuring the consistency of the Applied Warehouse Management Method that user choose,
    & for the purpose of filtering AccountingPeriod
    """

    warehouse_management_method = models.ForeignKey(WarehouseManagementMethod, on_delete=models.CASCADE, null=False, blank=False, related_name="%(class)s_applied_in_periods")
    date_applied = models.DateField(null=False, blank=False)
    # Explicitly the default value of date_end field is the last day of the month
    # After that month, renew the date_end field to the value of the last day of next month
    # If not, create a new AccountingPeriod object
    date_end = models.DateField(null=False, blank=False)

    def __str__(self):
        return f"Accounting period starts on {self.date_applied} & end on {self.date_end} in the usage of {self.warehouse_management_method.name}"
    
class Supplier(models.Model):
    name = models.CharField(max_length=200, blank=False, null=False, default="")
    address = models.TextField(max_length=1500, blank=True, null=True, default="")

    def __str__(self):
        return f"{self.name}"
    
class Agency(models.Model):
    name = models.CharField(max_length=200, blank=False, null=False, default="")
    address = models.TextField(max_length=1500, blank=True, null=True, default="")

    def __str__(self):
        return f"{self.name}"
    
class Product(models.Model):
    sku = models.CharField(primary_key=True, default="000000", max_length=14)
    name = models.CharField(null=False, blank=False, default="", unique=True, max_length=500)
    quantity_on_hand = models.IntegerField(null=True, blank=True, default=0)
    minimum_quantity = models.IntegerField(null=True, blank=True, default=1)
    current_total_value = models.IntegerField(null=True, blank=True, default=1)

    def __str__(self):
        return f"{self.name}"
    
class ImportShipment(models.Model):
    import_shipment_code = models.CharField(max_length=20, unique=True, null=False, blank=False, default="")
    supplier_id = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=False, blank=False, related_name="%(class)s_sent_import_shipments")
    date = models.DateField(null=False, blank=False)
    total_shipment_value = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return f"Import Shipment Id: {self.id}"
    
class ImportPurchase(models.Model):
    import_shipment_id = models.ForeignKey(ImportShipment, on_delete=models.CASCADE, null=False, blank=False, related_name="%(class)s_import_purchases_package")
    product_id = models.ForeignKey(Product, null=False, blank=False, on_delete=models.CASCADE, related_name="%(class)s_involving_import_purchases")
    quantity_import = models.IntegerField(null=False, blank=False, default=0)
    quantity_remain = models.IntegerField(null=True, blank=True, default=0)
    import_cost = models.IntegerField(null=False, blank=False, default=1)

    def __str__(self):
        return f"Import Purchase of {self.quantity_import} {self.product_id.name} in packaging of Import Shipment Id: {self.import_shipment_id.import_shipment_code}"
    
class ExportShipment(models.Model):
    export_shipment_code = models.CharField(max_length=20, unique=True, null=False, blank=False, default="")
    agency_id = models.ForeignKey(Agency, null=False, blank=False, on_delete=models.CASCADE, related_name="%(class)s_received_export_shipments")
    date = models.DateField(null=False, blank=False)
    total_shipment_value = models.IntegerField(null=True, blank=True, default=0)
    warehouse_management_method = models.ForeignKey(WarehouseManagementMethod, on_delete=models.CASCADE, null=False, blank=False, related_name="%(class)s_following_export_shipments")

    def __str__(self):
        return f"Export Shipment Id: {self.id}"
    
class ExportOrder(models.Model):
    export_shipment_id = models.ForeignKey(ExportShipment, on_delete=models.CASCADE, null=False, blank=False, related_name="%(class)s_export_orders_package")
    product_id = models.ForeignKey(Product, null=False, blank=False, on_delete=models.CASCADE, related_name="%(class)s_involving_export_orders")
    quantity_export = models.IntegerField(null=False, blank=False, default=0)
    unit_price = models.IntegerField(null=False, blank=False, default=1)
    total_order_value = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return f"Export Order of {self.quantity_export} {self.product_id.name} in packaging of Export Shipment Id: {self.export_shipment_id.id}"
    
class ExportOrderDetail(models.Model):
    export_order_id = models.ForeignKey(ExportOrder, null=False, blank=False, on_delete=models.CASCADE, related_name="%(class)s_involving_import_purchases")
    import_purchase_id = models.ForeignKey(ImportPurchase, null=False, blank=False, on_delete=models.CASCADE, related_name="%(class)s_involving_export_orders")
    quantity_take = models.IntegerField(null=False, blank=False, default=0)

    def __str__(self):
        return f"Export Order Id {self.export_order_id.id} takes {self.quantity_take} of Import Shipment Id {self.import_purchase_id.id}"
    