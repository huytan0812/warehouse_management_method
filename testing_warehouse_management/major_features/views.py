from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from datetime import datetime, timezone, timedelta
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
    if len(currently_applied_method) == CHOSEN_METHOD_COUNT:
        context['method'] = currently_applied_method[0]

    return render(request, "major_features/index.html", context)

def get_lastday_of_month(date_obj):

    """
    Get the last day of a month
    """

    get_datepicker_month = date_obj.month
    get_datepicker_year = date_obj.year
    last_day_of_month = calendar.monthrange(get_datepicker_year, get_datepicker_month)[1]
    return last_day_of_month

def is_last_day_of_month(date_obj):

    """
    Validating if the date_obj is the last day of a month
    """

    get_datepicker_day = date_obj.day
    return True if get_datepicker_day == get_lastday_of_month(date_obj) else False

def date_details(request):

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
                if len(WarehouseManagementMethod.objects.filter(is_currently_applied=True)) == 1:
                    context["keep_method_form"] = KeepMethodForm()

            return render(request, "major_features/date_details.html", context)
        
def apply_warehouse_management(request):

    """
    Handling POST request of KeepMethodForm & WarehouseManagementMethodForm from date_details.html
    """
    if request.method == "POST":
        keep_method_form = KeepMethodForm(request.POST)
        warehouse_management_method_form = WarehouseManagementMethodForm(request.POST)

        if warehouse_management_method_form.is_valid() and keep_method_form.is_valid():
            is_keep = keep_method_form.cleaned_data["is_keep"]

            if is_keep == True:
                renew_previous_method()
            else:
                method_by_POST = request.POST.get("name", "")

                # Handling POST key
                try:
                    new_chosen_method = WarehouseManagementMethod.objects.get(pk=int(method_by_POST))
                except WarehouseManagementMethod.DoesNotExist:
                    raise Exception("Invalid Method")

                inactivating_previous_method()                
                activating_new_chosen_method(new_chosen_method)
                create_new_accounting_period_obj(new_chosen_method)

                # Update the is_currently_applied field of that method
                new_chosen_method.is_currently_applied = True
                new_chosen_method.save(update_fields=["is_currently_applied"])

            return HttpResponseRedirect(reverse('index'))

def renew_previous_method():
    # Get the latest accounting period
    # Knowing that the latest accounting period is the activating method
    get_latest_accounting_period_id = AccoutingPeriod.objects.aggregate(Max("id")).get("id__max", 0)
    latest_accounting_period = AccoutingPeriod.objects.get(pk=get_latest_accounting_period_id)
    
    # Get the next last day of month
    date_time_now = datetime.now()
    UTC = pytz.utc
    date_time_utc_now = UTC.localize(date_time_now)
    next_day_of_new_month = date_time_utc_now + timedelta(days=1)
    


def inactivating_previous_method():
    pass

def activating_new_chosen_method():
    pass

def create_new_accounting_period_obj():
    pass