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
    CHOSEN_METHOD_COUNT = 1
    currently_applied_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)
    date_picker_form = DatePickerForm()

    context = {
        'date_picker_form': date_picker_form
    }

    # Handling if a method was chosen before
    if currently_applied_method.count() == CHOSEN_METHOD_COUNT:
        context['method'] = currently_applied_method[0]

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
                context["warehouse_management_method_form"] = WarehouseManagementMethodForm()
                if WarehouseManagementMethod.objects.filter(is_currently_applied=True).count() == 1:
                    context["keep_method_form"] = KeepMethodForm()

            return render(request, "major_features/apply_warehouse_management.html", context)

def get_date_utc_now():
    datetime_now = datetime.now()
    UTC = pytz.utc
    datetime_utc_now = UTC.localize(datetime_now)
    date_utc_now = datetime_utc_now.date()
    return date_utc_now

def keep_method(request):
    pass

def apply_warehouse_management(request):

    """
    Handling POST request of KeepMethodForm & WarehouseManagementMethodForm from apply_warehouse_management.html
    """
    method_count = WarehouseManagementMethod.objects.filter(is_currently_applied=True).count()
    if method_count == 0 or is_last_day_of_month(get_date_utc_now()):
        warehouse_management_method_form = WarehouseManagementMethodForm()
    else:
        return HttpResponse("Warning: Invalid access", content_type="text/plain")

    if request.method == "POST":
        keep_method_form = KeepMethodForm(request.POST)
        warehouse_management_method_form = WarehouseManagementMethodForm(request.POST)

        if warehouse_management_method_form.is_valid() and keep_method_form.is_valid():
            is_keep = keep_method_form.cleaned_data["is_keep"]

            if is_keep == True:
                renew_previous_method()
            else:
                method_by_POST = request.POST.get("name", "")

                # Bug is here:
                # When no method was chosen
                # method_by_post is a blank string ""
                # therefore new_chosen_method will raise an error

                # Handling POST key
                try:
                    new_chosen_method = WarehouseManagementMethod.objects.get(pk=int(method_by_POST))
                except WarehouseManagementMethod.DoesNotExist:
                    raise Exception("Invalid Method")
                
                # Handle if there are no method was chosen before
                if WarehouseManagementMethod.objects.filter(is_currently_applied=True).count() == 0:
                    # Update the is_currently_applied field of that method
                    new_chosen_method.is_currently_applied = True
                    new_chosen_method_obj = new_chosen_method.save(update_fields=["is_currently_applied"])
                    # Creating a new AccountingPeriod object
                    create_new_accounting_period(new_chosen_method_obj)

                else:
                    inactivating_previous_method()                
                    activating_new_chosen_method(new_chosen_method)
                    create_new_accounting_period_obj(new_chosen_method)
            
            return HttpResponseRedirect(reverse('index'))
        else:
            return HttpResponse("Invalid", content_type="text/plain")


def create_new_accounting_period(method):

    datetime_now = datetime.now()
    UTC = pytz.utc
    datetime_utc_now = UTC.localize(datetime_now)
    date_utc_now = datetime_utc_now.date()

    last_day_of_month = get_lastday_of_month(date_utc_now)

    new_accounting_period_obj = AccoutingPeriod.objects.create(
        warehouse_management_method=method,
        date_applied=date_utc_now,
        date_end=date(date_utc_now.year, date_utc_now.month, last_day_of_month)
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