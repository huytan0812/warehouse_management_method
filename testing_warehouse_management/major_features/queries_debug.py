from django.db import connection, reset_queries, transaction
import time
import functools
import pytz
import calendar
from datetime import date, datetime, timedelta
from django.db.models import Sum
from . models import *

def query_debugger(func):
    @functools.wraps(func)
    def inner_func(*args, **kwargs):
        reset_queries()

        start_queries = len(connection.queries)

        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()

        end_queries = len(connection.queries)

        print("Function : " + func.__name__)
        print("Number of Queries : {}".format(end_queries - start_queries))
        print("Finished in : {}".format(end - start))

        return result

    return inner_func

def renew_previous_method(date_obj):
    # Get the latest accounting period
    # Knowing that the latest accounting period is the activating method
    
    # Get the next last day of month
    next_day_of_new_month = date_obj + timedelta(days=1)
    last_day_of_new_month = calendar.monthrange(next_day_of_new_month.year, next_day_of_new_month.month)[1]
    new_date_obj = date(next_day_of_new_month.year, next_day_of_new_month.month, last_day_of_new_month)
    return new_date_obj

def convert_to_next_last_day():
    dates = [
        date(2023, 1, 31),
        date(2023, 2, 28),
        date(2023, 3, 31),
        date(2023, 4, 30),
        date(2023, 5, 31),
        date(2023, 6, 30),
        date(2023, 7, 31),
        date(2023, 8, 31),
        date(2023, 9, 30),
        date(2023, 10, 31),
        date(2023, 11, 30),
        date(2023, 12, 31),
    ]

    for date_obj in dates:
        print(renew_previous_method(date_obj))

def validating_shipment_value():
    import_shipments = ImportShipment.objects.all()
    for import_shipment_obj in import_shipments:
        import_shipment_obj_purchases = ImportPurchase.objects.filter(import_shipment_id=import_shipment_obj)
        current_import_shipment_obj_value = 0
        for purchase in import_shipment_obj_purchases:
            current_import_shipment_obj_value += purchase.quantity_remain * purchase.import_cost
        print(f"Import Shipment Code: {import_shipment_obj.import_shipment_code} {import_shipment_obj.total_shipment_value} | {current_import_shipment_obj_value}")
        if current_import_shipment_obj_value != import_shipment_obj.total_shipment_value:
            return False
    return True

@query_debugger
def assigning_quantity_remain():
    import_purchases = ImportPurchase.objects.all()
    for purchase in import_purchases:
        purchase.quantity_remain = purchase.quantity_import
    ImportPurchase.objects.bulk_update(import_purchases, ["quantity_remain"])
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)
    print(f"Queries: {len(connection_queries)}")

@query_debugger
def assigning_quantity_on_hand():
    products = Product.objects.all()
    for product in products:
        import_purchases_by_product = ImportPurchase.objects.filter(product_id=product.pk)
        import_purchases_by_product_sum = import_purchases_by_product.aggregate(Sum('quantity_remain')).get("quantity_remain__sum", 0)
        product.quantity_on_hand = import_purchases_by_product_sum
    Product.objects.bulk_update(products, ["quantity_on_hand"])
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)
    print(f"Queries: {len(connection_queries)}")

def is_equal_quantity_on_hand():
    products = Product.objects.all()
    for product in products:
        import_purchases_by_product = ImportPurchase.objects.filter(product_id=product)
        import_purchases_by_product_sum = import_purchases_by_product.aggregate(Sum("quantity_remain")).get("quantity_remain__sum", 0)
        print(f"Product: {product.quantity_on_hand} - Purchase: {import_purchases_by_product_sum}")
        if product.quantity_on_hand != import_purchases_by_product_sum:
            return False
    return True

@query_debugger
def assigning_current_total_value():
    product_current_total_value = {}
    purchases = ImportPurchase.objects.select_related('product_id').all()
    products = Product.objects.all()
    for purchase in purchases:
        if purchase.product_id.name not in product_current_total_value:
            product_current_total_value[purchase.product_id.name] = purchase.quantity_remain * purchase.import_cost
        else:
            product_current_total_value[purchase.product_id.name] += purchase.quantity_remain * purchase.import_cost
    for obj in product_current_total_value:
        product = products.get(name=obj)
        product.current_total_value = product_current_total_value[obj]
    Product.objects.bulk_update(products, ["quantity_on_hand"])

@query_debugger 
def is_equal_current_total_value():
    product_current_total_value = {}
    purchases = ImportPurchase.objects.select_related('product_id').all()
    
    for purchase in purchases:
        if purchase.product_id.name not in product_current_total_value:
            product_current_total_value[purchase.product_id.name] = purchase.quantity_remain * purchase.import_cost
        else:
            product_current_total_value[purchase.product_id.name] += purchase.quantity_remain * purchase.import_cost

    product_sum = 0
    for obj in product_current_total_value:
        product = Product.objects.get(name=obj)
        product_sum += product_current_total_value[obj]
        if product.current_total_value != product_current_total_value[obj]:
            return False
        
    product_agg_sum = Product.objects.all().aggregate(Sum('current_total_value')).get("current_total_value__sum", 0)
    print(f"Product Aggregate Sum: {product_agg_sum} - Product Sum: {product_sum}")

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)
    print(f"Queries: {len(connection_queries)}")

    if product_sum != product_agg_sum:
        return False

    return True

@query_debugger
def count_queries():
    products = Product.objects.all()
    for product in products:
        purchase = ImportPurchase.objects.filter(product_id=product)
        purchase_sum = purchase.aggregate(Sum("quantity_remain")).get("quantity_remain__sum", 0)
        product.quantity_on_hand = purchase_sum
    Product.objects.bulk_update(products, ["quantity_on_hand"])
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)
    print(f"Queries: {len(connection_queries)}")

@query_debugger
def assigning_address_for_supplier():
    suppliers = Supplier.objects.all()
    for supplier in suppliers:
        print(supplier.name)
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)