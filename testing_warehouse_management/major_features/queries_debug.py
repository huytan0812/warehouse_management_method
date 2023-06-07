from django.db import connection, reset_queries, transaction
import time
import functools
from django.db import connection
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
        import_purchases_by_product_sum = import_purchases_by_product.aggregate(Sum('quantity_import')).get("quantity_import__sum", 0)
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
        import_purchases_by_product_sum = import_purchases_by_product.aggregate(Sum("quantity_import")).get("quantity_import__sum", 0)
        print(f"Product {product.name}: {product.quantity_on_hand} - Purchase: {import_purchases_by_product_sum}")
        if product.quantity_on_hand != import_purchases_by_product_sum:
            return False
    return True

@query_debugger
def assigning_current_total_value():
    product_current_total_value = {}
    purchases = ImportPurchase.objects.select_related('product_id').all()
    for purchase in purchases:
        if purchase.product_id.name not in product_current_total_value:
            product_current_total_value[purchase.product_id.name] = purchase.quantity_import * purchase.import_cost
        else:
            product_current_total_value[purchase.product_id.name] += purchase.quantity_import * purchase.import_cost

    with transaction.atomic():
        for obj in product_current_total_value:
            Product.objects.filter(name=obj).update(current_total_value=product_current_total_value[obj])

    

@query_debugger 
def is_equal_current_total_value():
    product_current_total_value = {}
    purchases = ImportPurchase.objects.select_related('product_id').all()
    
    for purchase in purchases:
        if purchase.product_id.name not in product_current_total_value:
            product_current_total_value[purchase.product_id.name] = purchase.quantity_import * purchase.import_cost
        else:
            product_current_total_value[purchase.product_id.name] += purchase.quantity_import * purchase.import_cost

    product_sum = 0
    for obj in product_current_total_value:
        product = Product.objects.get(name=obj)
        product_sum += product_current_total_value[obj]
        print(f"Testing dictionary: {obj} - {product_current_total_value[obj]} | From database: {product.name} - {product.current_total_value}")
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

def for_testing_transaction():
    products = Product.objects.all().select_for_update(of=("self",))
    suppliers = Supplier.objects.all()
    for supplier in suppliers:
        print(supplier.name)

    with transaction.atomic():
        for product in products:
            print(product.name)

        print(products.explain(ANALYZE=True))
    
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def for_testing_advance_transaction():
    import_shipment_purchases = ImportPurchase.objects.select_related('product_id').select_for_update().filter(import_shipment_id=10)

    total_shipment_value = 0
    with transaction.atomic():
        import_shipment_obj = ImportShipment.objects.select_related('supplier_id').select_for_update().filter(pk=10)
        for purchase in import_shipment_purchases:
            total_shipment_value += purchase.quantity_import * purchase.import_cost
            print(purchase.product_id.name)
        print(import_shipment_obj[0].total_shipment_value)
        print(f"Total Shipment Value in transaction block: {total_shipment_value}")
    print(f"Total Shipment Value out transaction block: {total_shipment_value}")
    
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def for_testing_advance_transaction_scenario1(import_shipment_id):
    import_shipment_purchases = ImportPurchase.objects.select_related('product_id').select_for_update(of=("self","product_id",)).filter(import_shipment_id=import_shipment_id)
    with transaction.atomic():
        for purchase in import_shipment_purchases:
            print(purchase.product_id.name)
        print(import_shipment_purchases.explain(ANALYZE=True))

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def advance_testing_quantity_on_hand():
    import_shipment_past = ImportShipment.objects.filter(date__lt="2023-06-03").only("id")
    import_purchases_past = ImportPurchase.objects.select_related('product_id').filter(import_shipment_id__in=import_shipment_past)
    product_quantity_on_hand_past = {}
    for purchase in import_purchases_past:
        if purchase.product_id.name not in product_quantity_on_hand_past:
            product_quantity_on_hand_past[purchase.product_id.name] = [purchase.quantity_import, purchase.quantity_import * purchase.import_cost]
        else:
            product_quantity_on_hand_past[purchase.product_id.name][0] += purchase.quantity_import
            product_quantity_on_hand_past[purchase.product_id.name][1] += purchase.quantity_import * purchase.import_cost


    import_shipment_today = ImportShipment.objects.filter(date="2023-06-03").only("id")
    import_purchases_today = ImportPurchase.objects.select_related('product_id').filter(import_shipment_id__in=import_shipment_today)
    product_quantity_on_hand_today = {}
    for purchase in import_purchases_today:
        if purchase.product_id.name not in product_quantity_on_hand_today:
            product_quantity_on_hand_today[purchase.product_id.name] = purchase.quantity_import
        else:
            product_quantity_on_hand_today[purchase.product_id.name] += purchase.quantity_import

    print(import_shipment_past)
    print(product_quantity_on_hand_past)

    print(import_shipment_today)
    print(product_quantity_on_hand_today)

@query_debugger
def advance_testing_transaction_scenario2(import_shipment_id):
    import_purchases = ImportPurchase.objects.select_related('product_id').select_for_update(of=("self", "product_id",)).filter(import_shipment_id=import_shipment_id)

    with transaction.atomic():
        for purchase in import_purchases:
            print(purchase.product_id.name)
        print(import_purchases.explain(ANALYZE=True))

    connection_queries = connection.queries
    for connection_query in connection.queries:
        print(connection_query)

@query_debugger
def advance_testing_transaction_scenario3(product_id = []):
    products = Product.objects.select_for_update(of=("self",)).filter(pk__in=product_id)

    with transaction.atomic():
        for product in products:
            print(product.name)
        print(products.explain(ANALYZE=True))
        
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

def hashmap(import_shipment_id):
    import_purchases = ImportPurchase.objects.select_related('product_id').filter(import_shipment_id=import_shipment_id)
    product_additional_fields = {}

    for purchase in import_purchases:
        import_purchase_value = purchase.quantity_import * purchase.import_cost
        if purchase.product_id.name not in product_additional_fields:
            product_additional_fields[purchase.product_id.name] = [purchase.quantity_import, import_purchase_value]
        else:
            product_additional_fields[purchase.product_id.name][0] += purchase.quantity_import
            product_additional_fields[purchase.product_id.name][1] += import_purchase_value

    for product, value in product_additional_fields.items():
        product_obj = Product.objects.filter(name=product)
        print(f"{product_obj} - {value[0]} - {value[1]}")

