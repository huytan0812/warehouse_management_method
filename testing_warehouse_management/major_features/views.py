from django.shortcuts import render
from datetime import datetime
import calendar
from . models import *
from . forms import *

# Create your views here.
def index(request):
    warehouse_management_methods = WarehouseManagementMethod.objects.all()
    date_picker_form = DatePickerForm()
    context = {
        'warehouse_management_methods': warehouse_management_methods,
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
            get_datepicker = datepicker_form.cleaned_data["date_field"]
            context = {
                'datepicker': datepicker_form.cleaned_data["date_field"],
            }

            if is_last_day_of_month(get_datepicker):
                context["warehouse_management_method_form"] = WarehouseManagementMethodForm()

            return render(request, "major_features/date_details.html", context)