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

@receiver(post_save, sender=AccoutingPeriod)
def create_product_inventory(sender, instance, created, **kwargs):
    if created:
        new_accounting_period = instance
        prev_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').filter(
            pk__lt = new_accounting_period.pk
        ).order_by('-pk').first()
        prev_products_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').select_for_update(of=("self",)).filter(
            accounting_period_id = prev_accounting_period
        )

        with transaction.atomic():
            for prev_product_inventory in prev_products_inventory:
                new_product_inventory = AccountingPeriodInventory.objects.create(
                    accounting_period_id = new_accounting_period,
                    product_id = prev_product_inventory.product_id,
                    starting_inventory = prev_product_inventory.ending_inventory,
                    starting_quantity = prev_product_inventory.ending_quantity,
                    import_inventory = 0,
                    import_quantity = 0,
                    total_cogs = 0,
                    total_quantity_export = 0,
                    ending_inventory = prev_product_inventory.ending_inventory,
                    ending_quantity = prev_product_inventory.ending_quantity
                )

@receiver(post_delete, sender=ExportOrder)
def return_inventory(sender, instance, **kwargs):
    """
    Return 'total_cogs', 'total_quantity_export',
    'ending_inventory', 'ending_quantity',
    'total_revenue' fields
    for the product's AccountingPeriodInventory object
    """

    print("Signal is call")

    if instance.export_shipment_id.total_shipment_value == 0:
        # do nothing
        return

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
        product_accounting_inventory_obj.total_revenue -= instance.quantity_export * instance.unit_price
        product_accounting_inventory_obj.save(update_fields=["total_cogs", "total_quantity_export", "ending_inventory", "ending_quantity", "total_revenue"])

@receiver(post_delete, sender=ExportOrderDetail)
def return_quantity_for_import_purchase(sender, instance, **kwargs):
    """
    Return the quantity for the import purchase
    after deleting an ExportOrderDetail object
    """

    print("Post delete ExportOrderDetail object's Signal is call")

    with transaction.atomic():
        # ImportPurchase section
        involving_import_purchase = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id")).get(
            pk=instance.import_purchase_id.pk
        )
        involving_import_purchase.quantity_remain = involving_import_purchase.quantity_remain + instance.quantity_take
        involving_import_purchase.save(update_fields=["quantity_remain"])

