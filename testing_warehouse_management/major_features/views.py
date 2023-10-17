from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from datetime import date, datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
import calendar
import pytz
from django.db.models import Max
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.views.decorators.cache import cache_control
from django.core.paginator import Paginator
from . models import *
from . forms import *
from . decorators import is_activating_accounting_period
from . queries_debug import query_debugger
from . warehouse_management_methods import *

# Create your views here.
def index(request):
    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    product_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    date_picker_form = DatePickerForm()

    context = {
        'product_period_inventory': product_period_inventory,
        'date_picker_form': date_picker_form
    }

    # Handling if the current method is currently applied
    if  current_accounting_period.warehouse_management_method.is_currently_applied:
        context['method'] = current_accounting_period.warehouse_management_method
        context['accounting_period'] = current_accounting_period

        today = datetime.today().date()
        if current_accounting_period.date_end < today:
            context['alert_message'] = """
            Cảnh báo phương pháp quản lý hàng tồn kho chưa được cập nhật lại hoặc thay đổi sang phương pháp khác.
            Bạn sẽ không thể thực hiện nhập kho hay xuất kho
            """

    return render(request, "major_features/index.html", context)

def reports(request):

    context = {}

    current_accounting_period_id = AccoutingPeriod.objects.aggregate(Max('id')).get("id__max", 0)

    # Handling inventory at the starting of an accounting period
    accounting_periods_id = AccoutingPeriod.objects.exclude(pk=current_accounting_period_id).values_list('id', flat=True)
    if len(accounting_periods_id) >= 1:
        import_shipments_id = ImportShipment.objects.filter(current_accounting_period__in=accounting_periods_id).values_list('id', flat=True)
        import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id__in=import_shipments_id,
                                                                                                            quantity_remain__gt=0)
        products_inventory = {}
        for purchase in import_purchases:
            if purchase.product_id.name not in products_inventory:
                products_inventory[purchase.product_id.name] = {'quantity_remain': purchase.quantity_remain, 
                                                                'inventory_value': purchase.quantity_remain * purchase.import_cost}
            else:
                products_inventory[purchase.product_id.name]['quantity_remain'] += purchase.quantity_remain
                products_inventory[purchase.product_id.name]['inventory_value'] += purchase.quantity_remain * purchase.import_cost
        context['products_inventory'] = products_inventory
    
    return render(request, "major_features/reports/reports.html", context)

def reports_revenue(request):
    context = {}
    return render(request, "major_features/reports/revenue.html", context)

def reports_import_section(request):
    context = {}
    return render(request, "major_features/reports/import_section.html", context)

def reports_export_section(request):
    context = {}
    return render(request, "major_features/reports/export_section.html", context)

def get_lastday_of_month(date_obj):

    """
    Get the last day of a month
    """

    get_datepicker_month = date_obj.month
    get_datepicker_year = date_obj.year
    last_day_of_month = calendar.monthrange(get_datepicker_year, get_datepicker_month)[1]
    last_day_of_month_obj = date(get_datepicker_year, get_datepicker_month, last_day_of_month)
    return last_day_of_month_obj

def is_last_day_of_month(datepicker):

    """
    Validating if the date_obj is the last day of a month
    """
    return True if datepicker == get_lastday_of_month(datepicker) else False

def date_handling(request):

    """
    Handling POST request of the DatePickerForm from the index.html
    """

    if request.method == "POST":

        datepicker_form = DatePickerForm(request.POST)

        if datepicker_form.is_valid():
            get_datepicker_by_POST = request.POST.get("date_field")
            get_datepicker = datepicker_form.cleaned_data["date_field"]

            datepicker_format_for_url = "%d-%m-%Y"

            context = {
                'datepicker': get_datepicker,
                'datepicker_by_POST': get_datepicker_by_POST,
                'datepicker_to_str': get_datepicker.strftime(datepicker_format_for_url)
            }

            if is_last_day_of_month(get_datepicker):
                chosen_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)
                if chosen_method.count() == 1:
                    context["keep_method_form"] = KeepMethodForm()
                    context["method_name"] = chosen_method[0].name

            return render(request, "major_features/actions_on_date.html", context)

# Import Section

# Import Shipment Section
def import_shipments(request):

    import_shipments = ImportShipment.objects.select_related('supplier_id').all().order_by('-date', '-id')
    import_shipments_paginator = Paginator(import_shipments, 10)

    page_number = request.GET.get("page")
    page_obj = import_shipments_paginator.get_page(page_number)

    results_count = page_obj.end_index() - page_obj.start_index() + 1

    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    
    current_products_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    current_total_import_inventory = current_products_inventory.aggregate(Sum('import_inventory')).get('import_inventory__sum', 0)
    current_total_import_quantity = current_products_inventory.aggregate(Sum('import_quantity')).get('import_quantity__sum', 0)

    context = {
        'current_method': current_accounting_period.warehouse_management_method,
        'current_total_import_inventory': current_total_import_inventory,
        'current_total_import_quantity': current_total_import_quantity,
        'import_shipments': import_shipments,
        'page_obj': page_obj,
        'results_count': results_count
    }
    return render(request, "major_features/import/import_shipments.html", context)

def import_shipment_details(request, import_shipment_code):
    import_shipment_obj = ImportShipment.objects.get(import_shipment_code=import_shipment_code)
    import_shipment_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id=import_shipment_obj).order_by('product_id__name', '-id')

    products_purchase_value = {}

    for purchase in import_shipment_purchases:
        if purchase.product_id.name not in products_purchase_value:
            products_purchase_value[purchase.product_id.name] = {'purchase_value': purchase.quantity_import * purchase.import_cost,
                                                                 'remain_value': purchase.quantity_remain * purchase.import_cost,
                                                                 'current_quantity_remain': purchase.quantity_remain}
        else:
            products_purchase_value[purchase.product_id.name]['purchase_value'] += purchase.quantity_import * purchase.import_cost
            products_purchase_value[purchase.product_id.name]['remain_value'] += purchase.quantity_remain * purchase.import_cost
            products_purchase_value[purchase.product_id.name]['current_quantity_remain'] += purchase.quantity_remain

    context = {
        'import_shipment_obj': import_shipment_obj,
        'import_purchases': import_shipment_purchases,
        'products_purchase_value': products_purchase_value
    }

    return render(request, "major_features/import/import_shipment_details.html", context)

def delete_unfinish_import_shipment(request, import_shipment_code):

    try:
        unfinish_import_shipment_obj = ImportShipment.objects.get(import_shipment_code=import_shipment_code)
    except ImportShipment.DoesNotExist:
        raise Exception("Invalid Import Shipment")
    
    unfinish_import_shipment_obj.delete()

    return HttpResponseRedirect(reverse('import_shipments'))


# Import Action section

@is_activating_accounting_period
def import_action(request):
    latest_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    if request.method == "POST":
        import_shipment_form = ImportShipmentForm(request.POST)
        import_purchase_form = ImportPurchaseForm(request.POST)

        if import_shipment_form.is_valid() and import_purchase_form.is_valid():

            import_shipment_obj = import_shipment_form.save(commit=False)
            import_shipment_obj.current_accounting_period = latest_accounting_period_obj
            import_shipment_obj.save()

            import_purchase_obj = import_purchase_form.save(commit=False)
            import_purchase_obj.import_shipment_id = import_shipment_obj
            import_purchase_obj.quantity_remain = import_purchase_obj.quantity_import

            # ModelForm object saving
            import_purchase_obj.save()

            if "save_and_continue" in request.POST:
                return HttpResponseRedirect(reverse('save_and_continue', kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))
            
            if "save_and_complete" in request.POST:
                return HttpResponseRedirect(reverse('save_and_complete', kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))

        else:
            return HttpResponse("Invalid Form", content_type="text/plain")
            
    context = {
        'import_shipment_form': ImportShipmentForm(),
        'import_purchase_form': ImportPurchaseForm()
    }
    return render(request, "major_features/import/import_action.html", context)

@cache_control(no_cache=True, must_revalidate=True)
def save_and_continue(request, import_shipment_code):
    import_shipment_obj = ImportShipment.objects.select_related('supplier_id').get(import_shipment_code=import_shipment_code)

    # Check if user try to backward
    # after accomplishing the import shipment object
    if import_shipment_obj.total_shipment_value > 0:
        return HttpResponse("Save_and_continue error: You cannot backward after finishing import shipment object", content_type="text/plain")

    if request.method == "POST":
        import_purchase_form = ImportPurchaseForm(request.POST)

        if import_purchase_form.is_valid():
            import_purchase_obj = import_purchase_form.save(commit=False)
            import_purchase_obj.import_shipment_id = import_shipment_obj
            import_purchase_obj.quantity_remain = import_purchase_obj.quantity_import
            import_purchase_obj.value_import = import_purchase_obj.quantity_import * import_purchase_obj.import_cost

            # ModelForm object saving
            import_purchase_obj.save()

            if "save_and_continue" in request.POST:
                return HttpResponseRedirect(reverse("save_and_continue", kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))
            
            if "save_and_complete" in request.POST:
                return HttpResponseRedirect(reverse('save_and_complete', kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))

        else:
            return HttpResponse("Invalid form", content_type="text/plain")

    import_shipment_purchases = ImportPurchase.objects.select_related('product_id').filter(import_shipment_id=import_shipment_obj)

    purchase_additional_information = {}
    for purchase in import_shipment_purchases:
        if purchase.product_id.name not in purchase_additional_information:
            purchase_additional_information[purchase.product_id.name] = {'purchase_quantity_import': purchase.quantity_import, 
                                                                         'purchase_value': purchase.quantity_import * purchase.import_cost}
        else:
            purchase_additional_information[purchase.product_id.name]['purchase_quantity_import'] += purchase.quantity_import
            purchase_additional_information[purchase.product_id.name]['purchase_value'] += purchase.quantity_import * purchase.import_cost

    context = {
        'import_shipment_code': import_shipment_obj.import_shipment_code,
        'import_shipment_supplier': import_shipment_obj.supplier_id,
        'import_shipment_date': import_shipment_obj.date,
        'import_shipment_purchases': import_shipment_purchases,
        'purchase_additional_fields': purchase_additional_information,
        "import_purchase_form": ImportPurchaseForm()
    }
    return render(request, "major_features/import/save_and_continue.html", context)

@cache_control(no_cache=True, must_revalidate=True)
@transaction.atomic
def save_and_complete(request, import_shipment_code):

    import_shipment_obj = ImportShipment.objects.select_related('supplier_id').select_for_update(of=("self",)).filter(import_shipment_code=import_shipment_code)

    if len(import_shipment_obj) == 0:
        raise Exception("Không tồn tại mã lô hàng nhập kho")

    if import_shipment_obj[0].total_shipment_value > 0:
        return HttpResponse("Save_and_complete_error: You cannot backward after finishing the import shipment object", content_type="text/plain") 

    import_shipment_purchases = ImportPurchase.objects.select_related('import_shipment_id','product_id').filter(import_shipment_id=import_shipment_obj[0])

    total_import_shipment_value = 0

    product_additional_fields = {}

    for import_purchase in import_shipment_purchases:

        # Import Shipment Calculating total_shipment_value handling
        import_purchase_value = import_purchase.quantity_import * import_purchase.import_cost
        total_import_shipment_value += import_purchase_value

        # Product quantity_on_hand handling
        if import_purchase.product_id.name not in product_additional_fields:
            product_additional_fields[import_purchase.product_id.name] = [import_purchase.quantity_import, import_purchase_value]
        else:
            product_additional_fields[import_purchase.product_id.name][0] += import_purchase.quantity_import
            product_additional_fields[import_purchase.product_id.name][1] += import_purchase_value

    current_accounting_period = AccoutingPeriod.objects.latest('id')

    try:
        with transaction.atomic():
            for product, value_container in product_additional_fields.items():
                product_accounting_inventory_obj = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').select_for_update().get(
                    accounting_period_id=current_accounting_period,
                    product_id__name=product
                )
                product_accounting_inventory_obj.import_inventory += value_container[1]
                product_accounting_inventory_obj.import_quantity += value_container[0]
                product_accounting_inventory_obj.ending_inventory += value_container[1]
                product_accounting_inventory_obj.ending_quantity += value_container[0]
                product_accounting_inventory_obj.save(update_fields=["import_inventory", "import_quantity", "ending_inventory", "ending_quantity"])

            import_shipment_obj.update(total_shipment_value=total_import_shipment_value)
            
    except IntegrityError:
        raise Exception("Integrity Bug")

    context = {
        'import_shipment_code': import_shipment_obj[0].import_shipment_code,
        'import_shipment_supplier': import_shipment_obj[0].supplier_id,
        'import_shipment_date': import_shipment_obj[0].date,
        'import_shipment_purchases': import_shipment_purchases,
        'import_shipment_value': import_shipment_obj[0].total_shipment_value,
        "import_purchase_form": ImportPurchaseForm()
    }
    return render(request, "major_features/import/save_and_complete.html", context)

def import_purchase_update(request, import_purchase_id):
    
    try:
        import_purchase_obj = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').get(pk=import_purchase_id)
    except ImportPurchase.DoesNotExist:
        raise Exception("Invalid import purchase")
    
    import_shipment_code = import_purchase_obj.import_shipment_id.import_shipment_code
    import_purchase_form = ImportPurchaseForm(instance=import_purchase_obj)

    if request.method == "POST":
        import_purchase_form = ImportPurchaseForm(request.POST, instance=import_purchase_obj)
        
        if import_purchase_form.is_valid():
            import_purchase_obj = import_purchase_form.save(commit=False)
            import_purchase_obj.quantity_remain = import_purchase_obj.quantity_import
            import_purchase_obj.value_import = import_purchase_obj.quantity_import * import_purchase_obj.import_cost
            import_purchase_obj.save()

            return HttpResponseRedirect(reverse('save_and_continue', kwargs={'import_shipment_code': import_shipment_code}))
        else:
            return HttpResponse("Invalid form", content_type="text/plain")

    context = {
        'import_purchase_form': import_purchase_form,
        'import_purchase_obj': import_purchase_obj
    }

    return render(request, "major_features/import/edit_import_purchase.html", context)

def import_purchase_delete(request, import_purchase_id):
    try:
        import_purchase_obj = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').get(pk=import_purchase_id)
    except ImportPurchase.DoesNotExist:
        raise Exception("Invalid import purchase")
    import_shipment_code = import_purchase_obj.import_shipment_id.import_shipment_code

    import_purchase_obj.delete()

    return HttpResponseRedirect(reverse('save_and_continue', kwargs={'import_shipment_code': import_shipment_code}))

# Export Section

# Export Shipment Section

def export_shipments(request):
    """
    Rendering all export shipments paginately
    """

    export_shipments = ExportShipment.objects.select_related('agency_id').all().order_by('-date', '-id')
    export_shipments_paginator = Paginator(export_shipments, 10)
    page_number = request.GET.get("page")
    page_obj = export_shipments_paginator.get_page(page_number)

    results_count = page_obj.end_index() - page_obj.start_index() + 1

    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    current_products_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    current_total_cogs = current_products_inventory.aggregate(Sum('total_cogs')).get('total_cogs__sum', 0)
    current_total_quantity_export = current_products_inventory.aggregate(Sum('total_quantity_export')).get('total_quantity_export__sum', 0)

    context = {
        'current_method': current_accounting_period.warehouse_management_method,
        'current_total_cogs': current_total_cogs,
        'current_total_quantity_export': current_total_quantity_export,
        'page_obj': page_obj,
        'results_count': results_count
    }
    return render(request, "major_features/export/export_shipments.html", context)

def export_shipment_details(request, export_shipment_code):
    try:
        export_shipment_obj = ExportShipment.objects.select_related('current_accounting_period', 'agency_id').get(export_shipment_code=export_shipment_code)
    except ExportShipment.DoesNotExist:
        raise Exception("Không tồn tại mã lô hàng xuất kho")
    
    export_shipment_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(export_shipment_id=export_shipment_obj).order_by(
        'product_id__name', 
        '-id')

    export_shipment_accounting_period = export_shipment_obj.current_accounting_period

    context = {
        'export_shipment_obj': export_shipment_obj,
        'export_shipment_code': export_shipment_obj.export_shipment_code,
        'agency': export_shipment_obj.agency_id.name,
        'export_shipment_date': export_shipment_obj.date,
        'export_shipment_orders': export_shipment_orders,
        'export_shipment_value': export_shipment_obj.total_shipment_value,
        'export_shipment_accounting_period': export_shipment_accounting_period
    }

    return render(request, "major_features/export/export_action_complete.html", context)

# Export Action Section

@is_activating_accounting_period
def export_action(request):
    """
    Creating & saving new export shipment object to the database
    """

    latest_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    export_shipment_form = ExportShipmentForm()

    if request.method == "POST":
        export_shipment_form = ExportShipmentForm(request.POST)

        if export_shipment_form.is_valid():
           
            # Export Shipment    
            export_shipment_form_obj = export_shipment_form.save(commit=False)
            export_shipment_code = export_shipment_form_obj.export_shipment_code
            export_shipment_form_obj.current_accounting_period=latest_accounting_period_obj
            export_shipment_form_obj.save()

            return HttpResponseRedirect(reverse('export_order_action', kwargs={'export_shipment_code': export_shipment_code}))

        else:
            return HttpResponse('Invalid Form', content_type="text/plain")

    context = {
        'export_shipment_form': export_shipment_form,
        'latest_accounting_period_obj': latest_accounting_period_obj
    }

    return render(request, "major_features/export/export_action.html", context)

@cache_control(no_cache=True, must_revalidate=True)
@transaction.atomic()
def export_action_complete(request, export_shipment_code):
    export_shipment_obj = ExportShipment.objects.select_related('current_accounting_period', 'agency_id').select_for_update(of=("self",)).filter(
        export_shipment_code = export_shipment_code
    )

    if len(export_shipment_obj) == 0:
        raise Exception("Không tồn tại mã lô hàng xuất kho")
    
    if export_shipment_obj[0].total_shipment_value > 0:
        return HttpResponse(f"Bạn đã xác nhận hoàn tất lô hàng xuất kho {export_shipment_obj[0].export_shipment_code} này trước đó", content_type="text/plain")

    export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        export_shipment_id = export_shipment_obj[0]
    ).order_by('product_id__name', '-id')

    product_export_containers = {}
    total_shipment_value = 0

    for export_order in export_orders:
        if export_order.product_id.name not in product_export_containers:
            product_export_containers[export_order.product_id.name] = {
                'total_quantity_take': export_order.quantity_export,
                'total_order_value': export_order.total_order_value
            }
        else:
            product_export_container = product_export_containers[export_order.product_id.name]
            product_export_container['total_quantity_take'] += export_order.quantity_export
            product_export_container['total_order_value'] += export_order.total_order_value
        total_shipment_value += export_order.total_order_value
    
    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    try:
        with transaction.atomic():
            for product, value_container in product_export_containers.items():
                accounting_inventory_obj = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').select_for_update(of=("self",)).get(
                    accounting_period_id = current_accounting_period,
                    product_id__name = product
                )
                accounting_inventory_obj.total_cogs += value_container["total_order_value"]
                accounting_inventory_obj.total_quantity_export += value_container["total_quantity_take"]
                accounting_inventory_obj.ending_inventory -= value_container["total_order_value"]
                accounting_inventory_obj.ending_quantity -= value_container["total_quantity_take"]
                accounting_inventory_obj.save(update_fields=["total_cogs", "total_quantity_export", "ending_inventory", "ending_quantity"])

            export_shipment_obj.update(total_shipment_value=total_shipment_value)

    except IntegrityError:
        raise Exception("Integrity Bug")
    
    context = {
        'export_shipment_code': export_shipment_obj[0].export_shipment_code,
        'agency': export_shipment_obj[0].agency_id.name,
        'export_shipment_date': export_shipment_obj[0].date,
        'export_shipment_orders': export_orders,
        'export_shipment_value': total_shipment_value,
        'export_shipment_accounting_period': current_accounting_period
    }

    return render(request, "major_features/export/export_action_complete.html", context)

def export_order_action(request, export_shipment_code):
    """
    Creating & saving new export order object to the database.
    Checking if new saving export order object is 'actual_method_by_name' or the others method
    """
    
    export_shipment_obj = ExportShipment.objects.select_related('current_accounting_period').get(export_shipment_code=export_shipment_code)
    current_warehouse_management_method = export_shipment_obj.current_accounting_period.warehouse_management_method
    
    FIFO_PK = 1
    LIFO_PK = 2
    WEIGHTED_AVERAGE_PK = 4
    SPECIFIC_IDENTICATION_PK = 5

    export_order_form = ExportOrderForm()

    if request.method == "POST":
        export_order_form = ExportOrderForm(request.POST)

        if export_order_form.is_valid():

            export_order_form_obj = export_order_form.save(commit=False)
            export_order_form_obj.export_shipment_id = export_shipment_obj
            export_order_form_obj.save()

            if current_warehouse_management_method.pk == SPECIFIC_IDENTICATION_PK:
                return HttpResponseRedirect(reverse('choose_type_of_inventory', kwargs={'export_order_id': export_order_form_obj.id}))
            
            if current_warehouse_management_method.pk == WEIGHTED_AVERAGE_PK:
                return HttpResponseRedirect(reverse('weighted_average', kwargs={'export_order_id': export_order_form_obj.id}))
            
            export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_form_obj.id)

            if current_warehouse_management_method.pk == LIFO_PK:
                LIFO(export_order_obj)

            if current_warehouse_management_method.pk == FIFO_PK:
                FIFO(export_order_obj)
                
            return HttpResponseRedirect(reverse('complete_export_order_by_inventory', kwargs={'export_order_id': export_order_form_obj.id}))

        return HttpResponse("Invalid Form", content_type="text/plain")

    context = {
        'export_shipment_code': export_shipment_code,
        'current_method': current_warehouse_management_method,
        'export_order_form': export_order_form,
    }

    return render(request, "major_features/export/export_order_action.html", context)

def choose_type_of_inventory(request, export_order_id):
    """
    Only for 'actual_method_by_name'.
    Prompt type of inventory for user to choose
    """

    export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    product = Product.objects.get(name=export_order_obj.product_id.name)
    current_accounting_period = AccoutingPeriod.objects.latest('id')
    starting_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__date__lt = current_accounting_period.date_applied,
        product_id = product,
        quantity_remain__gt=0
    )
    starting_purchases_count = starting_purchases.count()

    context = {
        'export_order_id': export_order_id,
        'product': product,
        'starting_purchases_count': starting_purchases_count,
    }

    if request.method == "POST":
        if "starting_inventory" in request.POST:
            return HttpResponseRedirect(reverse('export_by_starting_inventory', kwargs={'export_order_id': export_order_id, 'product': product.name}))
        if "current_accounting_period_inventory" in request.POST:
            return HttpResponseRedirect(reverse('export_by_current_accounting_period_inventory', kwargs={'export_order_id': export_order_id, 'product': product.name}))

    return render(request, "major_features/export/choose_type_of_inventory.html", context)

def export_by_starting_inventory(request, export_order_id, product):
    """
    Only for 'actual_method_by_name'.
    Starting inventory type
    """

    TYPE_OF_INVENTORY = "starting_inventory"
    export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    filtering_starting_inventory_form = FilteringInventory(product=product, type=TYPE_OF_INVENTORY)
    starting_inventory_form = ActualMethodInventory(product=product, type=TYPE_OF_INVENTORY, quantity_export_remain=export_order_obj.quantity_export)

    quantity_take_context = {
            'quantity_export': export_order_obj.quantity_export
        }

    context = {
        'export_order_id': export_order_id,
        'product': product,
        'type': TYPE_OF_INVENTORY,
        'filtering_starting_inventory_form': filtering_starting_inventory_form,
        'starting_inventory_form': starting_inventory_form,
        'quantity_take_context': quantity_take_context
    }

    return render(request, "major_features/export/export_by_inventory.html", context)

def export_by_current_accounting_period_inventory(request, export_order_id, product):
    """
    Only for 'actual_method_by_name'.
    Current accounting period object type
    """

    TYPE_OF_INVENTORY = "current_accounting_period"
    export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    filtering_current_accounting_period_inventory_form = FilteringInventory(product=product, type=TYPE_OF_INVENTORY)
    current_accounting_period_inventory_form = ActualMethodInventory(product=product, type=TYPE_OF_INVENTORY, quantity_export_remain=export_order_obj.quantity_export)

    quantity_take_context = {
            'quantity_export': export_order_obj.quantity_export
        }

    context = {
        'export_order_id': export_order_id,
        'product': product,
        'type': TYPE_OF_INVENTORY,
        'filtering_current_accounting_period_inventory_form': filtering_current_accounting_period_inventory_form,
        'current_accounting_period_inventory_form': current_accounting_period_inventory_form,
        'quantity_take_context': quantity_take_context
    }

    return render(request, "major_features/export/export_by_inventory.html", context)

def actual_method_by_name_export_action(request, export_order_id, product, type):
    """
    Only for 'actual_method_by_name'.
    Prompting Filtering inventory for user to choose according to type of inventory.
    Handling logic for each export order object detail creation by actual method by name.
    """

    export_order_obj = None
    try:
        export_order_obj = ExportOrder.objects.select_related('export_shipment_id').get(pk=int(export_order_id))
    except ExportOrder.DoesNotExist:
        raise Exception("Mã đơn hàng xuất kho không tồn tại")

    export_order_details = ExportOrderDetail.objects.select_related('export_order_id', 'import_purchase_id').filter(export_order_id=export_order_obj)
    total_quantity_take = export_order_details.aggregate(Sum('quantity_take')).get("quantity_take__sum", 0)

    if total_quantity_take == None:
        total_quantity_take = 0

    quantity_remain = export_order_obj.quantity_export - total_quantity_take

    quantity_take_context = {
        'quantity_export': export_order_obj.quantity_export,
        'total_quantity_take': total_quantity_take,
        'quantity_remain': quantity_remain
    }

    # Immediately return to complete_export_order_by_inventory route
    if quantity_take_context["quantity_remain"] == 0:
        update_export_order_value_for_actual_method_by_name(export_order_id)
        return HttpResponseRedirect(reverse('complete_export_order_by_inventory', kwargs={'export_order_id': export_order_id}))

    if request.method == "GET":
        # All blank fields in a form with GET request
        # are blank string values

        # Get field values from GET request
        get_import_shipment = request.GET.get("import_shipments", None)
        get_quantity_remain_greater_than = request.GET.get("quantity_remain_greater_than", None)
        get_quantity_remain_less_than = request.GET.get("quantity_remain_less_than", None)
        get_import_cost_greater_than = request.GET.get("import_cost_greater_than", None)
        get_import_cost_less_than = request.GET.get("import_cost_less_than", None)

        # Sanitizing
        import_shipment = get_import_shipment if get_import_shipment != "" else None
        quantity_remain_greater_than = int(get_quantity_remain_greater_than) if get_quantity_remain_greater_than else 0
        quantity_remain_less_than = int(get_quantity_remain_less_than) if get_quantity_remain_less_than else 0
        import_cost_greater_than = int(get_import_cost_greater_than) if get_import_cost_greater_than else 0
        import_cost_less_than = int(get_import_cost_less_than) if get_import_cost_less_than else 0

        import_shipment_obj = None
        if import_shipment != None:
            try:
                import_shipment_obj = ImportShipment.objects.get(pk=import_shipment)
            except ImportShipment.DoesNotExist:
                raise Exception("Mã lô hàng nhập kho không tồn tại")

        filter_context = {
            'import_shipment': import_shipment_obj,
            'quantity_remain_greater_than': quantity_remain_greater_than,
            'quantity_remain_less_than': quantity_remain_less_than,
            'import_cost_greater_than': import_cost_greater_than,
            'import_cost_less_than': import_cost_less_than
        }

        TYPE_OF_INVENTORY = type

        context = {
            'filter_context': filter_context,
            'quantity_take_context': quantity_take_context,
            'export_order_id': export_order_id,
            'product': product,
            'type': TYPE_OF_INVENTORY,
        }

        filtering_inventory_form = FilteringInventory(request.GET, product = product, type = TYPE_OF_INVENTORY)
        actual_method_inventory_form = ActualMethodInventory(product = product, type = TYPE_OF_INVENTORY,
                                        import_shipment_code = import_shipment if import_shipment != "" else None,
                                        quantity_remain_greater_than = quantity_remain_greater_than if quantity_remain_greater_than > 0 else None,
                                        quantity_remain_less_than = quantity_remain_less_than if quantity_remain_less_than > 0 else None,
                                        import_cost_greater_than = import_cost_greater_than if import_cost_greater_than > 0 else None,
                                        import_cost_less_than = import_cost_less_than if import_cost_less_than > 0 else None)

        if TYPE_OF_INVENTORY == "starting_inventory":
            filtering_starting_inventory_form = filtering_inventory_form
            starting_inventory_form = actual_method_inventory_form

            context['filtering_starting_inventory_form'] = filtering_starting_inventory_form
            context['starting_inventory_form'] = starting_inventory_form
        else:
            filtering_current_accounting_period_inventory_form = filtering_inventory_form
            current_accounting_period_inventory_form = actual_method_inventory_form

            context['filtering_current_accounting_period_inventory_form'] = filtering_current_accounting_period_inventory_form
            context['current_accounting_period_inventory_form'] = current_accounting_period_inventory_form

        return render(request, "major_features/export/export_by_inventory.html", context)

    if request.method == "POST":
        actual_method_form = ActualMethodInventory(request.POST, 
                                                   product=product,
                                                   type=type,
                                                   quantity_export_remain=quantity_remain)
        
        if actual_method_form.is_valid():
            chosen_purchase = actual_method_form.get_purchase()
            quantity_take = actual_method_form.get_quantity_take()
            import_cost = actual_method_form.get_import_cost()

            export_order_detail_obj = ExportOrderDetail.objects.create(
                export_order_id=export_order_obj,
                import_purchase_id=chosen_purchase,
                quantity_take=quantity_take,
                export_price = import_cost
            )

            update_import_purchase(export_order_detail_obj.pk)

            return HttpResponseRedirect(reverse('actual_method_by_name_export_action', kwargs={
                'export_order_id': export_order_id,
                'product': product,
                'type': type
            }))
        else:
            return HttpResponse("Invalid Form", content_type="text/plain")

@transaction.atomic()
def update_import_purchase(export_order_detail_id):
    try:
        export_order_detail_obj = ExportOrderDetail.objects.get(pk=export_order_detail_id)
    except ExportOrderDetail.DoesNotExist:
        raise Exception("Không tồn tại chi tiết đơn hàng xuất kho")
    
    import_purchase = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id",)).get(
        pk = export_order_detail_obj.import_purchase_id.pk
    )

    # Update import purchase object's quantity_remain field
    import_purchase.quantity_remain -= export_order_detail_obj.quantity_take

    try:
        with transaction.atomic():
            import_purchase.save(update_fields=["quantity_remain"])
    except IntegrityError:
        raise Exception("Integrity Bug")

@transaction.atomic()        
def update_export_order_value_for_actual_method_by_name(export_order_id):
    """
    Only for 'actual_method_by_name'.
    Handling logic for updating 'total_order_value' field for export order object
    """

    export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').select_for_update(of=("self",)).filter(pk=export_order_id)
    export_order_details_obj = ExportOrderDetail.objects.select_related('export_order_id', 'import_purchase_id').filter(export_order_id__pk=export_order_obj[0].pk)

    export_order_additional_fields = {
        'total_order_value': 0
    }

    for obj in export_order_details_obj:
        export_order_additional_fields['total_order_value'] += obj.quantity_take * obj.export_price

    try:
        with transaction.atomic():
            export_order_obj.update(
                total_order_value=export_order_additional_fields['total_order_value'],
            )
    except IntegrityError:
        raise Exception("Integrity Bug")

def weighted_average(request, export_order_id):
    """
    'complete_export_order_by_inventory for displaying export price calculation info
    for weighted average method
    """

    try:
        export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    except ExportOrder.DoesNotExist:
        raise Exception("Không tồn tại mã đơn hàng xuất kho")
    
    weighted_average_cost_info = weighted_average_constantly(export_order_obj)
    completing_weighted_average_constantly_method(export_order_obj, weighted_average_cost_info["export_price"])

    export_order_details_obj = ExportOrderDetail.objects.select_related('export_order_id', 'import_purchase_id').filter(export_order_id__pk=export_order_obj.pk)

    export_shipment_obj = export_order_obj.export_shipment_id
    export_shipment_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        export_shipment_id__export_shipment_code = export_shipment_obj.export_shipment_code
    )


    context = {
        'export_order_obj': export_order_obj,
        'export_shipment_code': export_shipment_obj.export_shipment_code,
        'export_shipment_value': export_shipment_obj.total_shipment_value,
        'export_order_details': export_order_details_obj,
        'weighted_average_cost_info': weighted_average_cost_info,
        'export_shipment_orders': export_shipment_orders
    }

    return render(request, "major_features/export/complete_export_by_inventory.html", context)

def complete_export_order_by_inventory(request, export_order_id):

    try:
        export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    except ExportOrder.DoesNotExist:
        raise Exception("Mã đơn hàng xuất kho không tồn tại")

    export_order_details_obj = ExportOrderDetail.objects.select_related('export_order_id', 'import_purchase_id').filter(export_order_id__pk=export_order_obj.pk)

    export_shipment_obj = export_order_obj.export_shipment_id
    export_shipment_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        export_shipment_id__export_shipment_code = export_shipment_obj.export_shipment_code
    )
    
    context = {
        'export_order_obj': export_order_obj,
        'export_shipment_code': export_shipment_obj.export_shipment_code,
        'export_shipment_value': export_shipment_obj.total_shipment_value,
        'export_order_details': export_order_details_obj,
        'export_shipment_orders': export_shipment_orders
    }

    return render(request, "major_features/export/complete_export_by_inventory.html", context)
    

def get_date_utc_now():
    datetime_now = datetime.now()
    UTC = pytz.utc
    datetime_utc_now = UTC.localize(datetime_now)
    date_utc_now = datetime_utc_now.date()
    return date_utc_now

# Warehouse Management Method
# Handling section

def keep_current_method(request):
    if request.method == "POST":
        keep_method_form = KeepMethodForm(request.POST)
        if keep_method_form.is_valid():
            is_keep = keep_method_form.cleaned_data["is_keep"]
            if is_keep == True:
                renew_previous_method()
                return HttpResponseRedirect(reverse('index'))
            else:
                return HttpResponseRedirect(reverse('apply_warehouse_management'))
        else:
            return HttpResponse("Invalid", content_type="text/plain")

def apply_warehouse_management(request):

    if request.method == "GET":
        # Only setting method_count = 0
        # or datepicker is last day of a month
        # when deploy production
        warehouse_management_method_form = WarehouseManagementMethodForm()
        context = {
            'warehouse_management_method_form': warehouse_management_method_form
        }
        return render(request, "major_features/apply_warehouse_management.html", context)
    
    if request.method == "POST":
        warehouse_management_method_form = WarehouseManagementMethodForm(request.POST)

        if warehouse_management_method_form.is_valid():
            method_id_by_POST = request.POST.get("name", "")
            
            try:
                method = WarehouseManagementMethod.objects.get(pk=int(method_id_by_POST))
            except WarehouseManagementMethod.DoesNotExits:
                raise Exception("Invalid Method")
            
            if WarehouseManagementMethod.objects.filter(is_currently_applied=True).count() == 1:
                deactivating_previous_method()
            
            activating_new_chosen_method(method)

            create_new_accounting_period(method)

            return HttpResponseRedirect(reverse('index'))

def activating_accounting_period(request):

    context = {}
    chosen_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)
    context["keep_method_form"] = KeepMethodForm()
    context["method_name"] = chosen_method[0].name

    return render(request, "major_features/activate_accounting_period.html", context)

def create_new_accounting_period(method):

    datetime_now = datetime.now()
    UTC = pytz.utc
    datetime_utc_now = UTC.localize(datetime_now)
    date_utc_now = datetime_utc_now.date()

    last_day_of_month = get_lastday_of_month(date_utc_now)

    new_accounting_period_obj = AccoutingPeriod.objects.create(
        warehouse_management_method=method,
        date_applied=date_utc_now,
        date_end=date(date_utc_now.year, date_utc_now.month, last_day_of_month.day)
    )

    return new_accounting_period_obj

def renew_previous_method():
    # Get the latest accounting period
    # Knowing that the latest accounting period is the activating method
    get_latest_accounting_period_id = AccoutingPeriod.objects.aggregate(Max("id")).get("id__max", 0)
    latest_accounting_period = AccoutingPeriod.objects.get(pk=get_latest_accounting_period_id)

    next_day_of_new_month = latest_accounting_period.date_end + timedelta(days=1)

    last_day_of_new_month = calendar.monthrange(next_day_of_new_month.year, next_day_of_new_month.month)[1]
    last_day_of_new_month_obj = date(next_day_of_new_month.year, next_day_of_new_month.month, last_day_of_new_month)

    latest_accounting_period.date_end = last_day_of_new_month_obj

    latest_accounting_period_obj = latest_accounting_period.save(update_fields=["date_end"])
    return latest_accounting_period_obj

def deactivating_previous_method():
    previous_chosen_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)[0]
    previous_chosen_method.is_currently_applied = False
    previous_chosen_method_save_obj = previous_chosen_method.save(update_fields=["is_currently_applied"])
    return previous_chosen_method_save_obj

def activating_new_chosen_method(method):
    method.is_currently_applied = True
    method_obj = method.save(update_fields=["is_currently_applied"])
    return method_obj
