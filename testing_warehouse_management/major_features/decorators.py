from functools import wraps
from datetime import datetime
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseRedirect
from django.urls import reverse
from . models import WarehouseManagementMethod, AccoutingPeriod

# Outer function() takes a view_function() as an argument
def is_activating_warehouse_management_method(view_function):

    # Inner function() wraps a decorated function()
    def wrapper_function(*args, **kwargs):

        # Pre handling
        print("Hello, World 1")
        print("Hello, World 2")

        # Decorated function()
        view_function(*args, **kwargs)

        # Post handling
        print("Hello, World 3")
        print("Hello, World 4")
        print("Hello, World 5")

    return wrapper_function

@is_activating_warehouse_management_method
def greet():
    print("Hello, World!")

def is_activating_accounting_period(view_function):
    def wrapper_function(*args, **kwargs):
        with transaction.atomic():
            latest_accounting_period_id = AccoutingPeriod.objects.aggregate(Max("id")).get('id__max', 0)
            accounting_period_obj = AccoutingPeriod.objects.get(pk=latest_accounting_period_id)
        today = datetime.today().date()
        if accounting_period_obj.date_end < today:
            return HttpResponseRedirect(reverse('activating_accounting_period'))
        return view_function(*args, **kwargs)
    return wrapper_function

@is_activating_accounting_period
def web_application():
    print("Welcome to the Major Feature")