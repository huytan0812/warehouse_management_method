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
from . models import *
from . forms import *
from . warehouse_management_methods import *
from . decorators import is_activating_accounting_period

# Create your views here.
def index(request):

    products = Product.objects.all()
    date_picker_form = DatePickerForm()

    context = {
        'products': products,
        'date_picker_form': date_picker_form
    }

    CHOSEN_METHOD_COUNT = 1
    method_count = WarehouseManagementMethod.objects.filter(is_currently_applied=True).count()

    # Handling if a method was chosen before
    if  method_count == CHOSEN_METHOD_COUNT:

        # Handling validating if an accounting period object exists
        currently_accounting_period_id = AccoutingPeriod.objects.aggregate(Max("id")).get("id__max", 0)
        currently_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').get(pk=int(currently_accounting_period_id))
        context['method'] = currently_accounting_period_obj.warehouse_management_method
        context['accounting_period'] = currently_accounting_period_obj

        # Handling inventory at the starting of an accounting period
        previous_accounting_period_id = currently_accounting_period_id - 1
        is_previous_accounting_period_obj_exists = AccoutingPeriod.objects.filter(id=previous_accounting_period_id).exists()
        if is_previous_accounting_period_obj_exists:
            previous_accounting_period_obj = AccoutingPeriod.objects.get(pk=previous_accounting_period_id)

            # Get all import shipments
            # according to the previous_accounting_period_obj

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id__date__range=[
                previous_accounting_period_obj.date_applied, previous_accounting_period_obj.date_end
            ])

        today = datetime.today().date()
        if currently_accounting_period_obj.date_end < today:
            context['alert_message'] = """
            Cảnh báo phương pháp quản lý hàng tồn kho chưa được cập nhật lại hoặc thay đổi sang phương pháp khác.
            Bạn sẽ không thể thực hiện nhập kho hay xuất kho
            """

    return render(request, "major_features/index.html", context)

def reports(request):
    pass

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
def import_shipments(request, testing_date):
    import_shipments = ImportShipment.objects.select_related('supplier_id').filter(date=testing_date)

    context = {
        'datepicker': testing_date,
        'import_shipments': import_shipments
    }
    return render(request, "major_features/import/import_shipments.html", context)

def import_shipment_details(request, import_shipment_code):
    import_shipment_obj = ImportShipment.objects.get(import_shipment_code=import_shipment_code)
    import_shipment_purchases = ImportPurchase.objects.select_related('product_id').filter(import_shipment_id=import_shipment_obj)

    context = {
        'import_shipment_obj': import_shipment_obj,
        'import_purchases': import_shipment_purchases
    }

    return render(request, "major_features/import/import_shipment_details.html", context)

@is_activating_accounting_period
def import_action(request):
    if request.method == "POST":
        import_shipment_form = ImportShipmentForm(request.POST)
        import_purchase_form = ImportPurchaseForm(request.POST)

        if import_shipment_form.is_valid() and import_purchase_form.is_valid():

            import_shipment_obj = import_shipment_form.save()

            import_purchase_obj = import_purchase_form.save(commit=False)
            import_purchase_obj.import_shipment_id = import_shipment_obj
            import_purchase_obj.quantity_remain = import_purchase_obj.quantity_import

            # ModelForm object saving
            import_purchase_obj.save()

            if "save_and_continue" in request.POST:
                return HttpResponseRedirect(reverse('save_and_continue', kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))

        else:
            return HttpResponse("Invalid Form", content_type="text/plain")
            
    context = {
        'import_shipment_form': ImportShipmentForm(),
        'import_purchase_form': ImportPurchaseForm()
    }
    return render(request, "major_features/import/import_action.html", context)

def save_and_continue(request, import_shipment_code):
    import_shipment_obj = ImportShipment.objects.select_related('supplier_id').get(import_shipment_code=import_shipment_code)

    if request.method == "POST":
        import_purchase_form = ImportPurchaseForm(request.POST)

        if import_purchase_form.is_valid():
            import_purchase_obj = import_purchase_form.save(commit=False)
            import_purchase_obj.import_shipment_id = import_shipment_obj
            import_purchase_obj.quantity_remain = import_purchase_obj.quantity_import

            # ModelForm object saving
            import_purchase_obj.save()

            if "save_and_continue" in request.POST:
                return HttpResponseRedirect(reverse("save_and_continue", kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))

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

    import_shipment_obj = ImportShipment.objects.select_related('supplier_id').select_for_update().filter(import_shipment_code=import_shipment_code)
    if import_shipment_obj[0].total_shipment_value > 0:
        return HttpResponse('You cannot backward', content_type="text/plain") 

    import_shipment_purchases = ImportPurchase.objects.select_related('product_id').select_for_update().filter(import_shipment_id=import_shipment_obj[0])

    total_import_shipment_value = 0

    product_additional_fields = {}

    try:
        with transaction.atomic():
            for import_purchase in import_shipment_purchases:
                # Import Shipment Calculating total_shipmen_value handling
                import_purchase_value = import_purchase.quantity_import * import_purchase.import_cost
                total_import_shipment_value += import_purchase_value

                # Product quantity_on_hand handling
                if import_purchase.product_id.name not in product_additional_fields:
                    product_additional_fields[import_purchase.product_id.name] = [import_purchase.product_id.quantity_on_hand + import_purchase.quantity_import, 
                                                                                  import_purchase.product_id.current_total_value + import_purchase_value]
                else:
                    product_additional_fields[import_purchase.product_id.name][0] += import_purchase.quantity_import
                    product_additional_fields[import_purchase.product_id.name][1] += import_purchase_value
            
            for product, value_container in product_additional_fields.items():
                Product.objects.filter(name=product).update(quantity_on_hand=value_container[0], current_total_value=value_container[1])

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
def export_shipments(request, testing_date):

    current_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)
    context = {
        'current_method': current_method,
        'datepicker': testing_date
    }
    return render(request, "major_features/export/export_shipments.html", context)

@is_activating_accounting_period
def export_action(request):
    current_method_obj = WarehouseManagementMethod.objects.filter(is_currently_applied=True)[0]
    export_shipment_form = ExportShipmentForm()
    export_order_form = ExportOrderForm()

    if request.method == "POST":
        export_shipment_form = ExportShipmentForm(request.POST)
        export_order_form = ExportOrderForm(request.POST)

        if export_shipment_form.is_valid() and export_order_form.is_valid():
           
            # Export Shipment    
            export_shipment_form_obj = export_shipment_form.save(commit=False)
            export_shipment_form_obj.warehouse_management_method=current_method_obj
            export_shipment_form_obj.save()

            # Export order
            export_order_form_obj = export_order_form.save(commit=False)
            export_order_form_obj.export_shipment_id = export_shipment_form_obj

            if current_method_obj == "FIFO":
                # Implement to FIFO accounting
                pass
            
            if current_method_obj == "LIFO":
                # Implement to FIFO accounting
                pass

            if current_method_obj == "Bình quân gia quyền tức thời":
                # Implement to FIFO accounting
                pass

            if current_method_obj == "Bình quân gia quyền cuối kỳ":
                # Implement to FIFO accounting
                pass
           

        else:
            return HttpResponse('Invalid Form', content_type="text/plain")

    context = {
        'export_shipment_form': export_shipment_form,
        'export_order_form': export_order_form,
        'current_method_obj': current_method_obj
    }

    return render(request, "major_features/export/export_action.html", context)

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
