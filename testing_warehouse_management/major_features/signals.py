from . models import *
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Product)
def create_product_inventory_obj(sender, instance, created, **kwargs):
    if created:
        current_accounting_period = AccoutingPeriod.objects.latest('id')
        AccountingPeriodInventory.objects.create(
            accounting_period_id = current_accounting_period,
            product_id = instance
        )

@receiver(post_save, sender=ExportOrderDetail)
def after_processing_export_order_details(sender, instance, created, **kwargs):
    if created:

        # ImportPurchase section
        involving_import_purchase = instance.import_purchase_id
        involving_import_purchase.quantity_remain = involving_import_purchase.quantity_remain - instance.quantity_take
        involving_import_purchase.save(update_fields=["quantity_remain"])

        # ImportShipment section
        involving_import_shipment = ImportShipment.objects.get(pk=involving_import_purchase.import_shipment_id.id)
        subtract_value = instance.quantity_take * involving_import_purchase.import_cost
        involving_import_shipment.total_shipment_value -= subtract_value
        involving_import_shipment.save(update_fields=["total_shipment_value"])

@receiver(post_delete, sender=ExportOrderDetail)
def return_quantity_for_import_purchase(sender, instance, **kwargs):
    # ImportPurchase section
    involving_import_purchase = instance.import_purchase_id
    involving_import_purchase.quantity_remain = involving_import_purchase.quantity_remain + instance.quantity_take
    involving_import_purchase.save(update_fields=["quantity_remain"])

    # ImportShipment section
    involving_import_shipment = ImportShipment.objects.get(pk=involving_import_purchase.import_shipment_id.id)
    return_value = instance.quantity_take * involving_import_purchase.import_cost
    involving_import_shipment.total_shipment_value += return_value
    involving_import_shipment.save(update_fields=["total_shipment_value"])
