from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from datetime import date, datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
import calendar
import pytz
from django.db.models import Max
from django.urls import reverse
from . models import *
from . forms import *

# Create your views here.
def index(request):

    date_picker_form = DatePickerForm()

    context = {
        'date_picker_form': date_picker_form
    }

    CHOSEN_METHOD_COUNT = 1
    method_count = WarehouseManagementMethod.objects.filter(is_currently_applied=True).count()

    # Handling if a method was chosen before
    if  method_count == CHOSEN_METHOD_COUNT:
        currently_accounting_period_id = AccoutingPeriod.objects.aggregate(Max("id")).get("id__max", 0)
        currently_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').get(pk=int(currently_accounting_period_id))
        context['method'] = currently_accounting_period_obj.warehouse_management_method
        context['accounting_period'] = currently_accounting_period_obj

    return render(request, "major_features/index.html", context)

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
            context = {
                'datepicker': datepicker_form.cleaned_data["date_field"],
                'datepicker_by_POST': get_datepicker_by_POST
            }

            if is_last_day_of_month(get_datepicker):
                if WarehouseManagementMethod.objects.filter(is_currently_applied=True).count() == 1:
                    context["keep_method_form"] = KeepMethodForm()

            return render(request, "major_features/actions_on_date.html", context)

def get_date_utc_now():
    datetime_now = datetime.now()
    UTC = pytz.utc
    datetime_utc_now = UTC.localize(datetime_now)
    date_utc_now = datetime_utc_now.date()
    return date_utc_now

def keep_current_method(request):
    if request.method == "POST":
        keep_method_form = KeepMethodForm(request.POST)
        if keep_method_form.is_valid():
            is_keep = keep_method_form.cleaned_data["is_keep"]
            choices = keep_method_form.fields["is_keep"].choices
            return HttpResponse(f"is_keep: {is_keep}, choices: {choices}", content_type="text/plain")
        else:
            return HttpResponse("Invalid", content_type="text/plain")

def apply_warehouse_management(request):

    if request.method == "GET":
        # Only setting method_count = 0
        # or datepicker is last day of a month
        # when deploy production
        method_count = WarehouseManagementMethod.objects.filter(is_currently_applied=True).count()

        if method_count == 0 or is_last_day_of_month(get_date_utc_now()):
            warehouse_management_method_form = WarehouseManagementMethodForm()
            context = {
                'warehouse_management_method_form': warehouse_management_method_form
            }
            return render(request, "major_features/apply_warehouse_management.html", context)
        
        else:
            return HttpResponse("Warning: Invalid access", content_type="text/plain")
    
    if request.method == "POST":
        warehouse_management_method_form = WarehouseManagementMethodForm(request.POST)

        if warehouse_management_method_form.is_valid():
            method_id_by_POST = request.POST.get("name", "")
            
            try:
                method = WarehouseManagementMethod.objects.get(pk=int(method_id_by_POST))
            except WarehouseManagementMethod.DoesNotExits:
                raise Exception("Invalid Method")
            
            method.is_currently_applied = True
            method_obj = method.save(update_fields=["is_currently_applied"])

            create_new_accounting_period(method)

            return HttpResponseRedirect(reverse('index'))

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

    


def inactivating_previous_method():
    pass

def activating_new_chosen_method():
    pass

def create_new_accounting_period_obj():
    pass