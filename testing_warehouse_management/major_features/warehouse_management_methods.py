from . views import *
from . models import *

def computing_export_cost(export_order_id):
    try:
        export_order_obj = ExportOrder.objects.select_related('export_shipment_id').get(pk=export_order_id)
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
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__total_shipment_value__gt=0,
        product_id__name=export_order_obj.product_id.name,
        quantity_remain__gt=0
        ).order_by('import_shipment_id__date', 'id')

    quantity_export_remain = export_order_obj.quantity_export

    for purchase in import_purchases:
        if purchase.quantity_remain >= quantity_export_remain:
            export_order_detail_obj = ExportOrderDetail.objects.create(
                export_order_id=export_order_obj,
                import_purchase_id=purchase,
                quantity_take=quantity_export_remain
            )
            return
        
        quantity_export_remain -= purchase.quantity_remain
        export_order_detail_obj = ExportOrderDetail.objects.create(
            export_order_id=export_order_obj,
            import_purchase_id=purchase,
            quantity_take=purchase.quantity_remain
        )

def LIFO(export_order_obj):
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__total_shipment_value__gt=0,
        product_id__name=export_order_obj.product_id.name,
        quantity_remain__gt=0
        ).order_by('-import_shipment_id__date', '-id')

    quantity_export_remain = export_order_obj.quantity_export

    for purchase in import_purchases:
        if purchase.quantity_remain >= quantity_export_remain:
            export_order_detail_obj = ExportOrderDetail.objects.create(
                export_order_id=export_order_obj,
                import_purchase_id=purchase,
                quantity_take=quantity_export_remain
            )
            return
        
        quantity_export_remain -= purchase.quantity_remain
        export_order_detail_obj = ExportOrderDetail.objects.create(
            export_order_id=export_order_obj,
            import_purchase_id=purchase,
            quantity_take=purchase.quantity_remain
        )

def average_method_constantly(export_order_obj):
    pass


