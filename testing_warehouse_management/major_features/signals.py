from . models import *
from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=ExportOrderDetail)
def return_quantity_for_import_purchase(sender, instance, **kwargs):
    involving_import_purchase = instance.import_purchase_id
    involving_import_purchase_quantity_remain = involving_import_purchase.quantity_remain + instance.quantity_take
    involving_import_purchase.quantity_remain = involving_import_purchase_quantity_remain
    involving_import_purchase.save(update_fields=["quantity_remain"])
