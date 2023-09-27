from . models import *
from django.db import transaction, IntegrityError
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

@receiver(post_delete, sender=ExportOrder)
def return_inventory(sender, instance, **kwargs):
    current_accounting_period = AccoutingPeriod.objects.latest('id')
    with transaction.atomic():
        product_accounting_inventory_obj = AccountingPeriodInventory.objects.select_related("accounting_period_id", "product_id").select_for_update(of=("self", )).get(
            accounting_period_id = current_accounting_period,
            product_id = instance.product_id
        )
        product_accounting_inventory_obj.total_cogs -= instance.total_order_value
        product_accounting_inventory_obj.total_quantity_export -= instance.quantity_export
        product_accounting_inventory_obj.ending_inventory += instance.total_order_value
        product_accounting_inventory_obj.ending_quantity += instance.quantity_export
        product_accounting_inventory_obj.save(update_fields=["total_cogs", "total_quantity_export", "ending_inventory", "ending_quantity"])

@receiver(post_delete, sender=ExportOrderDetail)
def return_quantity_for_import_purchase(sender, instance, **kwargs):
    with transaction.atomic():
        # ImportPurchase section
        involving_import_purchase = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id")).get(
            pk=instance.import_purchase_id.pk
        )
        involving_import_purchase.quantity_remain = involving_import_purchase.quantity_remain + instance.quantity_take
        involving_import_purchase.save(update_fields=["quantity_remain"])

        # ImportShipment section
        involving_import_shipment = involving_import_purchase.import_shipment_id
        return_value = instance.quantity_take * involving_import_purchase.import_cost
        involving_import_shipment.total_shipment_remain += return_value
        involving_import_shipment.save(update_fields=["total_shipment_remain"])
