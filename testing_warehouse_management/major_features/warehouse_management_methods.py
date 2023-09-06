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

def LIFO(export_order_obj):
    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__total_shipment_value__gt=0,
        product_id__name=export_order_obj.product_id.name,
        quantity_remain__gt=0
        ).order_by('-import_shipment_id__date', '-id')

def average_method_constantly(export_order_obj):
    pass


