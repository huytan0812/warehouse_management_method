from . views import *
from . models import *
from django.db.models import *

def handling_exporting_action(export_order_id):
    try:
        export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    except ExportOrder.DoesNotExist:
        raise Exception("Không tồn tại mã đơn hàng xuất kho")
    
    current_accounting_period = export_order_obj.export_shipment_id.current_accounting_period
    current_warehouse_management_method = current_accounting_period.warehouse_management_method
    if current_warehouse_management_method.pk == 1:
        FIFO(export_order_obj)
    elif current_warehouse_management_method.pk == 2:
        LIFO(export_order_obj)
    else:
        average_method_constantly(export_order_obj)

def FIFO(export_order_obj):
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update().filter(
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
                    export_total_order_value += quantity_export_remain * purchase.import_cost
                    break
                
                quantity_export_remain -= purchase.quantity_remain
                export_order_detail_obj = ExportOrderDetail.objects.create(
                    export_order_id = export_order_obj,
                    import_purchase_id = purchase,
                    quantity_take = purchase.quantity_remain,
                    export_price = purchase.import_cost
                )
                export_total_order_value += purchase.quantity_remain * purchase.import_cost

            export_order_obj.total_order_value = export_total_order_value
            export_order_obj.save(update_fields=["total_order_value"])
            
    except IntegrityError:
        raise Exception("Integrity Bug")

def LIFO(export_order_obj):
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update().filter(
            import_shipment_id__total_shipment_value__gt=0,
            product_id__name=export_order_obj.product_id.name,
            quantity_remain__gt=0
        ).order_by('-import_shipment_id__date', '-id')

    quantity_export_remain = export_order_obj.quantity_export

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
                    export_total_order_value += quantity_export_remain * purchase.import_cost
                    break
                
                quantity_export_remain -= purchase.quantity_remain
                export_order_detail_obj = ExportOrderDetail.objects.create(
                    export_order_id = export_order_obj,
                    import_purchase_id = purchase,
                    quantity_take = purchase.quantity_remain,
                    export_price = purchase.import_cost
                )
                export_total_order_value += purchase.quantity_remain * purchase.import_cost

            export_order_obj.total_order_value = export_total_order_value
            export_order_obj.save(update_fields=["total_order_value"])

    except IntegrityError:
        raise Exception("Integrity Bug")

def average_method_constantly(export_order_obj):
    product = export_order_obj.product_id
    accounting_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        product_id=product
    )
    product_starting_inventory = accounting_period_inventory.starting_inventory
    product_starting_quantity = accounting_period_inventory.starting_quantity

    product_current_import_inventory = accounting_period_inventory.import_inventory
    product_current_import_quantity = accounting_period_inventory.import_quantity
    
    product_current_cogs = accounting_period_inventory.total_cogs
    product_current_quantity_export = accounting_period_inventory.total_quantity_export

    total_inventory_before_export_order = product_starting_inventory + product_current_import_inventory - product_current_cogs
    total_quantity_before_export_order = product_starting_quantity + product_current_import_quantity - product_current_quantity_export

    export_price = total_inventory_before_export_order / total_quantity_before_export_order
    quantity_export = export_order_obj.quantity_export

    export_order_value = export_price * quantity_export

    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update().filter(
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
                    return
                
                quantity_export_remain -= purchase.quantity_remain
                export_order_detail_obj = ExportOrderDetail.objects.create(
                    export_order_id = export_order_obj,
                    import_purchase_id = purchase,
                    quantity_take = purchase.quantity_remain,
                    export_price = export_price
                )

            export_order_obj.total_order_value = export_order_value
            export_order_obj.save(update_fields=["total_order_value"])

    except IntegrityError:
        raise Exception("Integrity Bug")








