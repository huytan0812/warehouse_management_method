from django.shortcuts import render
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