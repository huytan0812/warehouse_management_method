import calendar
import pytz
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from datetime import date, datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db.models import Max
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.views.decorators.cache import cache_control
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from . models import *
from . forms import *
from . decorators import is_activating_accounting_period
from . warehouse_management_methods import *
from . inventory_data_views import *

# Create your views here.
@login_required
def index(request):
    # Create user activity
    # to track the current session of the user
    current_session_key = request.session.session_key
    if not UserActivity.objects.filter(session_key = current_session_key).exists():
        user_activity = UserActivity.objects.create(
            user_id = request.user,
            login_time = vntz_to_utc(),
            session_key = current_session_key
        )

    accounting_periods_count = AccoutingPeriod.objects.all().count()
    if accounting_periods_count == 0:
        return HttpResponseRedirect(reverse('apply_warehouse_management'))    

    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    # Get total products inventory value
    products_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    ).order_by('-ending_inventory')
    total_inventory = products_period_inventory.aggregate(
        total_inventory_value = Sum("ending_inventory"),
        total_revenue_value = Sum("total_revenue")
    )
    # Get top 5 products inventory value
    top_five_products_inventory = products_period_inventory[:5]

    date_picker_form = DatePickerForm()

    # Get session data
    session_key = request.session.session_key
    current_session = Session.objects.get(session_key = session_key)
    current_session_data = current_session.session_data
    decoded_session_data = current_session.get_decoded()

    today = datetime.today().date()

    # Number of Import Shipments today
    today_import_shipments_count = ImportShipment.objects.filter(
        date = today
    ).count()

    # Number of Export Shipments today
    today_export_shipments_count = ExportShipment.objects.filter(
        date = today
    ).count()

    # Total revenue today
    today_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        export_shipment_id__date = today
    )
    today_revenue = today_export_orders.aggregate(
        today_total_revenue = Sum(
            F("quantity_export") * F("unit_price")
        )
    ).get("today_total_revenue")
    if not today_revenue:
        today_revenue = 0

    # Pie chart
    category_revenue_dict = index_category_revenue_pie_chart(current_accounting_period)
    category_revenue = category_revenue_dict['category_revenue']
    category_revenue_pie_chart_arr = category_revenue_dict['category_revenue_pie_chart_arr']

    category_inventory_dict = index_category_inventory_pie_chart(current_accounting_period)
    category_inventory = category_inventory_dict['category_inventory']
    category_inventory_pie_chart_arr = category_inventory_dict['category_inventory_pie_chart_arr']

    context = {
        'products_period_inventory': top_five_products_inventory,
        'total_inventory_value': total_inventory['total_inventory_value'],
        'total_revenue_value': total_inventory['total_revenue_value'],
        'date_picker_form': date_picker_form,
        'session_key': session_key,
        'current_session_data': current_session_data,
        'decoded_session_data': decoded_session_data,
        'today_import_shipments_count': today_import_shipments_count,
        'today_export_shipments_count': today_export_shipments_count,
        'today_revenue': today_revenue,
        'category_revenue': category_revenue,
        'category_inventory': category_inventory,
        'category_revenue_pie_chart_arr': category_revenue_pie_chart_arr,
        'category_inventory_pie_chart_arr': category_inventory_pie_chart_arr
    }

    # Handling if exists warehouse management method
    if  current_accounting_period.warehouse_management_method.is_currently_applied:
        context['method'] = current_accounting_period.warehouse_management_method
        context['accounting_period'] = current_accounting_period

        if current_accounting_period.date_end < today:
            context['alert_message'] = """
            Cảnh báo phương pháp quản lý hàng tồn kho chưa được cập nhật lại hoặc thay đổi sang phương pháp khác.
            Bạn sẽ không thể thực hiện nhập kho hay xuất kho
            """

    return render(request, "major_features/index.html", context)

# Index support function
def index_category_revenue_pie_chart(current_accounting_period):
    """
    Return category revenue dictionary for index
    which contains two keys:
    category_revenue & 'category_revenue_pie_chart_arr
    """
    category_revenue_pie_chart_arr = [
        ["Danh mục", "Doanh thu"]
    ]
    products_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    category_revenue = products_period_inventory.values('product_id__category_name__name').annotate(
        category_revenue = Sum("total_revenue")
    )
    for category in category_revenue:
        category_revenue_pie_chart_arr.append([category['product_id__category_name__name'], category['category_revenue']])

    category_revenue_dict = {
        'category_revenue': category_revenue,
        'category_revenue_pie_chart_arr': category_revenue_pie_chart_arr
    }

    return category_revenue_dict

# Index support function
def index_category_inventory_pie_chart(current_accounting_period):
    """
    Return category inventory dictionary for index
    which contains two keys:
    category_inventory & 'category_inventory_pie_chart_arr
    """
    category_inventory_pie_chart_arr = [
        ["Danh mục", "Giá trị HTK"]
    ]
    products_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    category_inventory = products_period_inventory.values('product_id__category_name__name').annotate(
        category_inventory = Sum("ending_inventory")
    )
    for category in category_inventory:
        category_inventory_pie_chart_arr.append([category['product_id__category_name__name'], category['category_inventory']])
    
    category_inventory_dict = {
        'category_inventory': category_inventory,
        'category_inventory_pie_chart_arr': category_inventory_pie_chart_arr

    }

    return category_inventory_dict

@login_required
def categories(request):
    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    category_containers = {}
    categories = Category.objects.all()

    for category in categories:
        c_inventory_products = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id = current_accounting_period,
            product_id__category_name = category.pk
        ).order_by('product_id__name')
        c_inventory_summarizing = c_inventory_products.aggregate(
            total_category_inventory = Sum("ending_inventory"),
            total_category_revenue = Sum("total_revenue"),
            total_category_cogs = Sum("total_cogs")
        )
        category_gross_profits = 0
        if c_inventory_summarizing["total_category_revenue"] and c_inventory_summarizing["total_category_cogs"]:
            category_gross_profits = c_inventory_summarizing["total_category_revenue"] - c_inventory_summarizing["total_category_cogs"]

        category_containers[category.name] = {
            'category_inventory_value': c_inventory_summarizing['total_category_inventory'],
            'category_revenue': c_inventory_summarizing['total_category_revenue'],
            'category_gross_profits': category_gross_profits
        }
        c = category_containers[category.name] 
        c['category_products'] = c_inventory_products

    context = {
        'categories': category_containers
    }
    return render(request, "major_features/categories/categories.html", context)

@login_required
def add_category(request):
    add_category_form = AddCategoryForm()

    if request.method == "POST":
        add_category_form = AddCategoryForm(request.POST)
        if add_category_form.is_valid():
            add_category_form.save()
            return HttpResponseRedirect(reverse('categories'))
        
        return HttpResponse("Invalid Form", content_type="text/plain")
    
    context = {
        'add_category_form': add_category_form
    }
    return render(request, "major_features/categories/add_category.html", context)

def vntz_to_utc():
    """
    Converting current local time to UTC
    """
    current_time = datetime.now()
    UTC = pytz.utc
    current_time_utc = UTC.localize(current_time)
    return current_time_utc

# ~~~~~~~~~~~~~~~~~~~~~
# Registration section

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        
        return render(request, "major_features/registration/login.html", {
            "message": "Tên đăng nhập hoặc tài khoản sai"
        })
    
    return render(request, "major_features/registration/login.html")


def logout_view(request):
    current_session_key = request.session.session_key
    try:
        user_activity = UserActivity.objects.get(session_key=current_session_key)
        # Update the user_activity object
        # with logout_time field by now
        user_activity.logout_time = vntz_to_utc()
        user_activity.save(update_fields=["logout_time"])
    except UserActivity.DoesNotExist:
        pass

    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.user.is_superuser == False:
        return render(request, "major_features/alerts/permissions_alert.html", {})
    
    if request.method == "POST":
        username = request.POST["username"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "major_features/registration/register.html", {
                "message": "Mật khẩu không trùng khớp"
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username=username, password=password)
            user.save()
        except IntegrityError:
            return render(request, "major_features/registration/register.html", {
                "message": "Tên đăng nhập đã tồn tại"
            })
        
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    
    return render(request, "major_features/registration/register.html")

def user_activities(request):
    if request.user.is_superuser == False:
        return render(request, "major_features/alerts/permissions_alert.html", {})

    user_activities = UserActivity.objects.select_related('user_id').order_by('-login_time')
    user_activities_paginator = Paginator(user_activities, 10)

    page_number = request.GET.get('page')
    page_obj = user_activities_paginator.get_page(page_number)

    results_count = page_obj.end_index() - page_obj.start_index() + 1

    context = {
        'page_obj': page_obj,
        'results_count': results_count
    }
    return render(request, "major_features/registration/user_activities.html", context)

def staffs(request):
    if request.user.is_superuser == False:
        return render(request, "major_features/alerts/permissions_alert.html", {})

    staffs = User.objects.all()
    context = {
        'staffs': staffs
    }
    return render(request, "major_features/registration/staffs.html", context)

def staff_information(request, staff_id):
    if request.user.is_superuser == False:
        return render(request, "major_features/alerts/permissions_alert.html", {})
    try:
        staff = User.objects.get(pk=staff_id)
    except User.DoesNotExist:
        raise Exception("Không tồn tại nhân viên")
    
    context = {
        'staff': staff
    }

    return render(request, "major_features/registration/staff_information.html", context)

def edit_staff_information(request, staff_id):
    if request.user.is_superuser == False:
        return render(request, "major_features/alerts/permissions_alert.html", {})

    try:
        staff = User.objects.get(pk=staff_id)
    except User.DoesNotExist:
        raise Exception("Không tồn tại nhân viên")
    
    edit_staff_info_form = EditUserInfoForm(instance=staff)

    if request.method == "POST":
        edit_bound_staff_info_form = EditUserInfoForm(request.POST, instance=staff)

        if edit_bound_staff_info_form.is_valid():
            edit_bound_staff_info_form.save()
            success_msg = f"Chỉnh sửa thông tin cho nhân viên {staff.username}"
            messages.success(request, success_msg)
            return HttpResponseRedirect(reverse('staff_information', kwargs={'staff_id': staff_id}))
        
        messages.error(request, edit_bound_staff_info_form.errors)
        return render(request, "major_features/registration/edit_staff_information.html", {
            'edit_staff_info_form': edit_staff_info_form
        })
    
    context = {
        'staff': staff,
        'edit_staff_info_form': edit_staff_info_form
    }
    return render(request, "major_features/registration/edit_staff_information.html", context)

# ~~~~~~~~~~~~~~~~~~~
# End Registration section

def products(request):
    current_accounting_period = AccoutingPeriod.objects.latest('id')
    products_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    ).order_by('product_id__category_name__name')
    context = {
        'products_inventory': products_inventory
    }
    return render(request, "major_features/products/products.html", context)

def add_product(request):
    add_product_form = AddProductForm()

    if request.method == "POST":
        add_product_form = AddProductForm(request.POST)
        if add_product_form.is_valid():
            add_product_form.save()
            return HttpResponseRedirect(reverse('products'))
        messages.error(request, "Đã tồn tại sản phẩm")
        return HttpResponseRedirect(reverse('add_product'))
    
    context = {
        'add_product_form': add_product_form
    }
    return render(request, "major_features/products/add_product.html", context)

def edit_product(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        raise Exception("Mã sản phẩm không hợp lệ")
    edit_product_form = EditProductForm(instance=product)

    if request.method == "POST":
        edit_product_form = EditProductForm(request.POST, instance=product)
        if edit_product_form.is_valid():
            edit_product_form.save()
            return HttpResponseRedirect(reverse('products'))
        return HttpResponse("Invalid form", content_type="text/plain")
    
    context = {
        'product': product,
        'edit_product_form': edit_product_form
    }
    return render(request, "major_features/products/edit_product.html", context)

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

    import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period', 'by_admin').all().order_by('-date', '-id')
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
    import_shipment_obj = ImportShipment.objects.select_related('current_accounting_period', 'by_admin').get(import_shipment_code=import_shipment_code)
    import_shipment_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id=import_shipment_obj).order_by('product_id__name', '-id')

    products_purchase_value = {}

    total_initial_value = 0
    total_current_value = 0
    total_current_quantity = 0

    for purchase in import_shipment_purchases:
        if purchase.product_id.name not in products_purchase_value:
            products_purchase_value[purchase.product_id.name] = {'purchase_value': purchase.quantity_import * purchase.import_cost,
                                                                 'remain_value': purchase.quantity_remain * purchase.import_cost,
                                                                 'current_quantity_remain': purchase.quantity_remain}
        else:
            products_purchase_value[purchase.product_id.name]['purchase_value'] += purchase.quantity_import * purchase.import_cost
            products_purchase_value[purchase.product_id.name]['remain_value'] += purchase.quantity_remain * purchase.import_cost
            products_purchase_value[purchase.product_id.name]['current_quantity_remain'] += purchase.quantity_remain
        
        total_initial_value += purchase.quantity_import * purchase.import_cost 
        total_current_value += purchase.quantity_remain * purchase.import_cost
        total_current_quantity += purchase.quantity_remain

    context = {
        'import_shipment_obj': import_shipment_obj,
        'import_purchases': import_shipment_purchases,
        'products_purchase_value': products_purchase_value,
        'total_initial_value': total_initial_value,
        'total_current_value': total_current_value,
        'total_current_quantity': total_current_quantity,
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
    # Get the current accounting period obj
    latest_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')

    # Get the authenticated admin
    admin = request.user

    if request.method == "POST":
        import_shipment_form = ImportShipmentForm(request.POST)
        import_purchase_form = ImportPurchaseForm(request.POST)

        if import_shipment_form.is_valid() and import_purchase_form.is_valid():

            import_shipment_obj = import_shipment_form.save(commit=False)
            # Save the import shipment obj's current_accounting_period field
            # with the current accounting period obj
            import_shipment_obj.current_accounting_period = latest_accounting_period_obj
            import_shipment_obj.by_admin = admin
            import_shipment_obj.save()

            # Save fields to import purchase obj
            import_purchase_obj = import_purchase_form.save(commit=False)
            import_purchase_obj.import_shipment_id = import_shipment_obj
            import_purchase_obj.quantity_remain = import_purchase_obj.quantity_import
            import_purchase_obj.value_import = import_purchase_obj.quantity_import * import_purchase_obj.import_cost

            # ModelForm object saving
            import_purchase_obj.save()

            if "save_and_continue" in request.POST:
                return HttpResponseRedirect(reverse('save_and_continue', kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))
            
            if "save_and_complete" in request.POST:
                return HttpResponseRedirect(reverse('save_and_complete', kwargs={'import_shipment_code': import_shipment_obj.import_shipment_code}))

        else:
            error_msg = None

            bound_import_shipment_form = ImportShipmentForm(request.POST)
            if bound_import_shipment_form.errors:
                error_msg = "Mã lô hàng nhập kho đã tồn tại"

            bound_import_purchase_form = ImportPurchaseForm(request.POST)
            if bound_import_purchase_form.errors:
                error_msg = "Đơn hàng không hợp lệ"

            messages.error(request, error_msg)

            context = {
                'import_shipment_form': bound_import_shipment_form,
                'import_purchase_form': bound_import_purchase_form,
            }
            return render(request, "major_features/import/import_action.html", context)
            
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

    import_shipment_purchases = ImportPurchase.objects.select_related('product_id').filter(import_shipment_id=import_shipment_obj).order_by('product_id__name')
    purchases_summarize_on_per_product = import_shipment_purchases.values('product_id__name').annotate(
        total_quantity_import_on_shipment = Sum("quantity_import"),
        total_import_inventory_on_shipment = Sum(
            F("quantity_import") * F("import_cost")
        )
    ).order_by('product_id__name')

    context = {
        'import_shipment_code': import_shipment_obj.import_shipment_code,
        'import_shipment_supplier': import_shipment_obj.supplier_id,
        'import_shipment_date': import_shipment_obj.date,
        'import_shipment_purchases': import_shipment_purchases,
        'purchases_summarize_on_per_product': purchases_summarize_on_per_product,
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

    import_shipment_purchases = ImportPurchase.objects.select_related('import_shipment_id','product_id').filter(
        import_shipment_id=import_shipment_obj[0]
    ).order_by('product_id__name')

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
        'total_import_shipment_value': total_import_shipment_value,
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
        'import_purchase_obj': import_purchase_obj,
        'import_purchase_id': import_purchase_id
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

# ~~~~~~~~~~~~~~~~~~ Ending Import Section

# Export Section

# Export Shipment Section

def export_shipments(request):
    """
    Rendering all export shipments paginately
    """

    export_shipments = ExportShipment.objects.select_related('agency_id', 'current_accounting_period', 'by_admin').all().order_by('-date', '-id')
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
        export_shipment_obj = ExportShipment.objects.select_related('agency_id', 'current_accounting_period', 'by_admin').get(export_shipment_code=export_shipment_code)
    except ExportShipment.DoesNotExist:
        raise Exception("Không tồn tại mã lô hàng xuất kho")
    
    export_shipment_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id=export_shipment_obj
        ).annotate(
            sub_revenue = F("quantity_export") * F("unit_price")
        ).order_by(
            'product_id__name', 
            '-id'
        )

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

# ~~~~~~~~~~~~~~~~ Ending Export Shipment Section

# Export Action Section

@is_activating_accounting_period
def export_action(request):
    """
    Creating & saving new export shipment object to the database
    """

    # Get the current accounting period obj
    latest_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    export_shipment_form = ExportShipmentForm()

    # Get the authenticated admin
    admin = request.user

    if request.method == "POST":
        export_shipment_form = ExportShipmentForm(request.POST)

        if export_shipment_form.is_valid():
           
            # Export Shipment    
            export_shipment_form_obj = export_shipment_form.save(commit=False)
            export_shipment_code = export_shipment_form_obj.export_shipment_code

            # Save the export shipment obj's current_accounting_period field
            # with the current accounting period obj
            export_shipment_form_obj.current_accounting_period = latest_accounting_period_obj
            export_shipment_form_obj.by_admin = admin
            export_shipment_form_obj.save()

            return HttpResponseRedirect(reverse('export_order_action', kwargs={'export_shipment_code': export_shipment_code}))

        else:
            return HttpResponse('Invalid Form', content_type="text/plain")

    context = {
        'export_shipment_form': export_shipment_form,
        'latest_accounting_period_obj': latest_accounting_period_obj
    }

    return render(request, "major_features/export/export_action.html", context)

def delete_unfinish_export_shipment(request, export_shipment_code):
    try:
        export_shipment_obj = ExportShipment.objects.get(export_shipment_code=export_shipment_code)
    except ExportShipment.DoesNotExist:
        raise Exception("Không tồn tại mã lô hàng xuất kho")
    
    export_shipment_obj.delete()
    return HttpResponseRedirect(reverse('export_shipments'))

@cache_control(no_cache=True, must_revalidate=True)
@transaction.atomic()
def export_action_complete(request, export_shipment_code):
    export_shipment_obj = ExportShipment.objects.select_related('agency_id', 'current_accounting_period').select_for_update(of=("self",)).filter(
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
    total_shipment_revenue = 0

    for export_order in export_orders:
        if export_order.product_id.name not in product_export_containers:
            product_export_containers[export_order.product_id.name] = {
                'total_quantity_take': export_order.quantity_export,
                'total_order_value': export_order.total_order_value,
                'revenue': export_order.quantity_export * export_order.unit_price
            }
        else:
            product_export_container = product_export_containers[export_order.product_id.name]
            product_export_container['total_quantity_take'] += export_order.quantity_export
            product_export_container['total_order_value'] += export_order.total_order_value
            product_export_container['revenue'] += export_order.quantity_export * export_order.unit_price

        total_shipment_value += export_order.total_order_value
        total_shipment_revenue += export_order.quantity_export * export_order.unit_price
    
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
                accounting_inventory_obj.total_revenue += value_container["revenue"]
                accounting_inventory_obj.save(update_fields=["total_cogs", "total_quantity_export", "ending_inventory", "ending_quantity", "total_revenue"])

            export_shipment_obj.update(
                total_shipment_value=total_shipment_value,
                shipment_revenue = total_shipment_revenue
            )

    except IntegrityError:
        raise Exception("Integrity Bug")
    
    context = {
        'export_shipment_code': export_shipment_obj[0].export_shipment_code,
        'export_shipment_obj': export_shipment_obj[0],
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

        messages.error(request, "Số lượng xuất kho của sản phẩm vượt quá Số lượng HTK của sản phẩm")
        return HttpResponseRedirect(reverse('export_order_action', kwargs={'export_shipment_code': export_shipment_code}))

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
    """
    Only for 'actual_method_by_name' method
    to update the ImportPurchase object's quantity_remain field
    using ExportOrderDetail object's quantity_take field
    """

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
    'complete_export_order_by_inventory' view for displaying export price calculation info
    for weighted average method
    """

    try:
        export_order_obj = ExportOrder.objects.select_related('export_shipment_id', 'product_id').get(pk=export_order_id)
    except ExportOrder.DoesNotExist:
        raise Exception("Không tồn tại mã đơn hàng xuất kho")
    
    weighted_average_cost_info = weighted_average_constantly(export_order_obj)
    completing_weighted_average_constantly_method(export_order_obj, weighted_average_cost_info["unround_export_price"])

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
    """
    Completing an ExportOrder object view & template
    """
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
    
# ~~~~~~~~~~~~~~~~~~~~~~~~ Ending Export Section

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
                prev_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
                current_warehouse_management_method = prev_accounting_period.warehouse_management_method
                new_accounting_period_obj = renew_previous_method(current_warehouse_management_method)
                return HttpResponseRedirect(reverse('inventory_data', kwargs={'accounting_period_id': prev_accounting_period.pk}))
            
            return HttpResponseRedirect(reverse('apply_warehouse_management'))
        
        return HttpResponse("Invalid", content_type="text/plain")

def apply_warehouse_management(request):

    # Only setting method_count = 0
    # or datepicker is last day of a month
    # when deploy production
    warehouse_management_method_form = WarehouseManagementMethodForm()
    context = {
        'warehouse_management_method_form': warehouse_management_method_form
    }
    
    if request.method == "POST":
        warehouse_management_method_form = WarehouseManagementMethodForm(request.POST)

        if warehouse_management_method_form.is_valid():
            method_id_by_POST = request.POST.get("name", "")
            
            try:
                method = WarehouseManagementMethod.objects.get(pk=int(method_id_by_POST))
            except WarehouseManagementMethod.DoesNotExist:
                raise Exception("Không tồn tại Phương pháp xác định giá trị hàng tồn kho")
            
            prev_accounting_period_pk = None
            if WarehouseManagementMethod.objects.filter(is_currently_applied=True).count() == 1:
                deactivating_previous_method()
                prev_accounting_period_pk = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id').pk
            
            activating_new_chosen_method(method)

            new_accounting_period_obj = create_new_accounting_period(method)
            redirect_accounting_period_pk = new_accounting_period_obj.pk

            if prev_accounting_period_pk:
                redirect_accounting_period_pk = prev_accounting_period_pk

            return HttpResponseRedirect(reverse('inventory_data', kwargs={'accounting_period_id': redirect_accounting_period_pk}))
    
    return render(request, "major_features/apply_warehouse_management.html", context)

def activating_accounting_period(request):
    """
    For decorators view.
    Displaying KeepMethodForm() for user to keep the current method &
    a link for choosing another warehouse management method
    """
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

def renew_previous_method(method):
    new_accounting_period_obj = create_new_accounting_period(method)
    return new_accounting_period_obj

def deactivating_previous_method():
    """
    Deactivating WarehouseManagmentMethod object's
    is_currently_applied to True
    """
    # In the database, only one WarehouseManagementMethod object
    # must have the field 'is_currently_applied' is True
    previous_chosen_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)[0]
    previous_chosen_method.is_currently_applied = False
    previous_chosen_method_save_obj = previous_chosen_method.save(update_fields=["is_currently_applied"])
    return previous_chosen_method_save_obj

def activating_new_chosen_method(method):
    """
    Activating WarehouseManagmentMethod object's
    is_currently_applied to True
    """
    method.is_currently_applied = True
    method_obj = method.save(update_fields=["is_currently_applied"])
    return method_obj
