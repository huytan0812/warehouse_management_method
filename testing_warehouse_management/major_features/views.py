from django.shortcuts import render
from . models import *

# Create your views here.
def index(request):
    warehouse_management_methods = WarehouseManagementMethod.objects.all()
    context = {
        'warehouse_management_methods': warehouse_management_methods
    }

    return render(request, "major_features/index.html", context)