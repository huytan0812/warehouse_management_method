from . views import *
from . models import *
from django.db.models import *
from django.db import transaction, IntegrityError

def update_purchase_quantity_remain(purchase, export_order_detail_obj):
    purchase.quantity_remain -= export_order_detail_obj.quantity_take
    purchase.save(update_fields=["quantity_remain"])
    return

def FIFO(export_order_obj):
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id")).filter(
            import_shipment_id__total_shipment_value__gt=0,
            product_id__name=export_order_obj.product_id.name,
            quantity_remain__gt=0
        ).order_by('import_shipment_id__date', 'id')

    try:
        with transaction.atomic():
            quantity_export_remain = export_order_obj.quantity_export
            export_total_order_value = 0

            for purchase in import_purchases:
                if purchase.quantity_remain >= quantity_export_remain:
                    export_order_detail_obj = ExportOrderDetail.objects.create(
                        export_order_id = export_order_obj,
                        import_purchase_id = purchase,
                        quantity_take = quantity_export_remain,
                        export_price = purchase.import_cost
                    )
                    export_total_order_value += export_order_detail_obj.quantity_take * export_order_detail_obj.export_price

                    update_purchase_quantity_remain(purchase, export_order_detail_obj)
                    
                    break
                
                quantity_export_remain -= purchase.quantity_remain
                export_order_detail_obj = ExportOrderDetail.objects.create(
                    export_order_id = export_order_obj,
                    import_purchase_id = purchase,
                    quantity_take = purchase.quantity_remain,
                    export_price = purchase.import_cost
                )
                export_total_order_value += export_order_detail_obj.quantity_take * export_order_detail_obj.export_price

                update_purchase_quantity_remain(purchase, export_order_detail_obj)

            export_order_obj.total_order_value = export_total_order_value
            export_order_obj.save(update_fields=["total_order_value"])        
    except IntegrityError:
        raise Exception("Integrity Bug")

def LIFO(export_order_obj):
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id")).filter(
            import_shipment_id__total_shipment_value__gt=0,
            product_id__name=export_order_obj.product_id.name,
            quantity_remain__gt=0
        ).order_by('-import_shipment_id__date', '-id')

    try:
        with transaction.atomic():
            quantity_export_remain = export_order_obj.quantity_export
            export_total_order_value = 0

            for purchase in import_purchases:
                if purchase.quantity_remain >= quantity_export_remain:
                    export_order_detail_obj = ExportOrderDetail.objects.create(
                        export_order_id = export_order_obj,
                        import_purchase_id = purchase,
                        quantity_take = quantity_export_remain,
                        export_price = purchase.import_cost
                    )
                    export_total_order_value += export_order_detail_obj.quantity_take * export_order_detail_obj.export_price

                    update_purchase_quantity_remain(purchase, export_order_detail_obj)
                    
                    break
                
                quantity_export_remain -= purchase.quantity_remain
                export_order_detail_obj = ExportOrderDetail.objects.create(
                    export_order_id = export_order_obj,
                    import_purchase_id = purchase,
                    quantity_take = purchase.quantity_remain,
                    export_price = purchase.import_cost
                )
                export_total_order_value += export_order_detail_obj.quantity_take * export_order_detail_obj.export_price

                update_purchase_quantity_remain(purchase, export_order_detail_obj)

            export_order_obj.total_order_value = export_total_order_value
            export_order_obj.save(update_fields=["total_order_value"])        
    except IntegrityError:
        raise Exception("Integrity Bug")


def weighted_average_constantly(export_order_obj):
    current_accounting_period = AccoutingPeriod.objects.latest('id')
    product = export_order_obj.product_id
    accounting_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').get(
        accounting_period_id = current_accounting_period,
        product_id__pk=product.pk
        )
    product_starting_inventory = accounting_period_inventory.starting_inventory
    product_starting_quantity = accounting_period_inventory.starting_quantity

    product_current_import_inventory = accounting_period_inventory.import_inventory
    product_current_import_quantity = accounting_period_inventory.import_quantity
    
    product_current_cogs = accounting_period_inventory.total_cogs
    product_current_quantity_export = accounting_period_inventory.total_quantity_export

    total_inventory_before_export_order = product_starting_inventory + product_current_import_inventory - product_current_cogs
    total_quantity_before_export_order = product_starting_quantity + product_current_import_quantity - product_current_quantity_export

    unround_export_price = total_inventory_before_export_order / total_quantity_before_export_order
    export_price = round(total_inventory_before_export_order / total_quantity_before_export_order)

    product_inventory_container = {
        'starting_inventory': product_starting_inventory,
        'starting_quantity': product_starting_quantity,
        'current_import_inventory': product_current_import_inventory,
        'current_import_quantity': product_current_import_quantity,
        'current_cogs': product_current_cogs,
        'current_quantity_export': product_current_quantity_export,
        'total_inventory_before_export_order': total_inventory_before_export_order,
        'total_quantity_before_export_order': total_quantity_before_export_order,
        'unround_export_price': unround_export_price,
        'export_price': export_price
    }

    return product_inventory_container

def completing_weighted_average_constantly_method(export_order_obj, export_price):

    quantity_export = export_order_obj.quantity_export

    export_order_value = export_price * quantity_export

    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id")).filter(
        import_shipment_id__total_shipment_value__gt=0,
        product_id__name = export_order_obj.product_id.name,
        quantity_remain__gt=0
    ).order_by('import_shipment_id__date', 'id')

    try:
        with transaction.atomic():
            quantity_export_remain = quantity_export
            for purchase in import_purchases:
                if purchase.quantity_remain >= quantity_export_remain:
                    export_order_detail_obj = ExportOrderDetail.objects.create(
                        export_order_id = export_order_obj,
                        import_purchase_id = purchase,
                        quantity_take = quantity_export_remain,
                        export_price = export_price
                    )
                    update_purchase_quantity_remain(purchase, export_order_detail_obj)

                    break
                
                quantity_export_remain -= purchase.quantity_remain
                export_order_detail_obj = ExportOrderDetail.objects.create(
                    export_order_id = export_order_obj,
                    import_purchase_id = purchase,
                    quantity_take = purchase.quantity_remain,
                    export_price = export_price
                )

                update_purchase_quantity_remain(purchase, export_order_detail_obj)

            export_order_obj.total_order_value = export_order_value
            export_order_obj.save(update_fields=["total_order_value"])
    except IntegrityError:
        raise Exception("Integrity Bug")
    







