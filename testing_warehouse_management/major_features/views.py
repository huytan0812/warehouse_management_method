from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
import calendar

from django.urls import reverse
from . models import *
from . forms import *

# Create your views here.
def index(request):
    currently_applied_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)
    date_picker_form = DatePickerForm()
    context = {
        'method': currently_applied_method[0],
        'date_picker_form': date_picker_form
    }

    return render(request, "major_features/index.html", context)

def get_lastday_of_month(date_obj):
    get_datepicker_month = date_obj.month
    get_datepicker_year = date_obj.year
    last_day_of_month = calendar.monthrange(get_datepicker_year, get_datepicker_month)[1]
    return last_day_of_month

def is_last_day_of_month(date_obj):
    get_datepicker_day = date_obj.day
    return True if get_datepicker_day == get_lastday_of_month(date_obj) else False

def date_details(request):

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

            return render(request, "major_features/date_details.html", context)
        
def apply_warehouse_management(request):
    if request.method == "POST":
        warehouse_management_method_form = WarehouseManagementMethodForm(request.POST)

        if warehouse_management_method_form.is_valid():
            method_by_POST = request.POST.get("name", "")

            # Handling POST key
            try:
                method = WarehouseManagementMethod.objects.get(pk=int(method_by_POST))
            except WarehouseManagementMethod.DoesNotExist:
                raise Exception("Invalid Method")
            
            # Update the is_currently_applied field of that method
            method.is_currently_applied = True
            method.save(update_fields=["is_currently_applied"])

            return HttpResponseRedirect(reverse('index'))
