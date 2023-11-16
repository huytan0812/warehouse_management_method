from django.db import connection, reset_queries, transaction
import time
import functools
import pytz
import calendar
from datetime import date, datetime, timedelta
from django.db.models import Sum, F, Max
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
        print("Docstring: ", func.__doc__)
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
    """
    Validating the product quantity on hand must equal to
    the sum of product's import purchases quantity remain
    """
    current_accounting_period = AccoutingPeriod.objects.latest('id')

    product_accounting_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    for product in product_accounting_inventory:
        import_purchases_by_product = ImportPurchase.objects.filter(import_shipment_id__total_shipment_value__gt = 0, 
                                                                    product_id = product.product_id)
        import_purchases_by_product_sum = import_purchases_by_product.aggregate(Sum("quantity_remain")).get("quantity_remain__sum", 0)
        print(f"Product {product.product_id.name}: {product.ending_quantity} - Purchase: {import_purchases_by_product_sum}")
        if product.ending_quantity != import_purchases_by_product_sum:
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

    """
    Validating the product current total value must equal to
    the sum of multiplier of corresponding 
    product's import purchases quantity remain & product's import purchases import cost
    """

    current_accounting_period = AccoutingPeriod.objects.latest('id')
    product_current_total_value = {}

    import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id__total_shipment_value__gt=0)
    export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(export_shipment_id__total_shipment_value__gt=0)
    
    for purchase in import_purchases:
        if purchase.product_id.name not in product_current_total_value:
            product_current_total_value[purchase.product_id.name] = purchase.quantity_import * purchase.import_cost
        else:
            product_current_total_value[purchase.product_id.name] += purchase.quantity_import * purchase.import_cost

    for order in export_orders:
        product_current_total_value[order.product_id.name] -= order.total_order_value

    product_sum = 0
    for obj in product_current_total_value:
        product = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').get(
            accounting_period_id = current_accounting_period,
            product_id__name = obj
        )
        product_sum += product_current_total_value[obj]
        print(f"Testing dictionary: {obj} - {product_current_total_value[obj]} | From database: {product.product_id.name} - {product.ending_inventory}")
        if product.ending_inventory != product_current_total_value[obj]:
            return False
        
    product_agg_sum = AccountingPeriodInventory.objects.filter(
        accounting_period_id = current_accounting_period
    ).aggregate(Sum('ending_inventory')).get('ending_inventory__sum', 0)
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

@query_debugger
def previous_accounting_period():
    currently_accounting_period_id = AccoutingPeriod.objects.aggregate(Max("id")).get("id__max", 0)
    previous_accounting_period_id = currently_accounting_period_id - 1
    is_previous_accounting_period_obj_exists = AccoutingPeriod.objects.filter(id=previous_accounting_period_id).exists()
    if is_previous_accounting_period_obj_exists:
        previous_accounting_period_obj = AccoutingPeriod.objects.get(pk=previous_accounting_period_id)

        # Get all import shipments
        # according to the previous_accounting_period_obj

        import_purchases = ImportPurchase.objects.select_related('import_shipment_id').filter(import_shipment_id__date__range=[
            previous_accounting_period_obj.date_applied, previous_accounting_period_obj.date_end
        ])
    return import_purchases

@query_debugger
def previous_accounting_period2():
    accounting_period = AccoutingPeriod.objects.all().order_by('-date_applied')[:2]
    if len(accounting_period) > 1:
        accounting_period_obj = accounting_period[1]

    print(accounting_period_obj)
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def latest_accounting_period():
    latest_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    print(latest_accounting_period_obj)

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def assigning_accounting_period():
    accounting_periods = AccoutingPeriod.objects.all()
    for obj in accounting_periods:
        import_shipments = ImportShipment.objects.filter(date__range=[
            obj.date_applied, obj.date_end
        ])
        import_shipments.update(current_accounting_period=obj)
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def starting_inventory(product_name):
    product = Product.objects.get(name=product_name)

    latest_accounting_period_id = AccoutingPeriod.objects.aggregate(Max('id')).get('id__max', 0)
    product_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(product_id=product,
                                                      quantity_remain__gt=0,
                                                      import_shipment_id__current_accounting_period__id__lt=latest_accounting_period_id
                                                      )
    
    product_purchases_count = product_purchases.count()
    print(product_purchases_count)

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def starting_inventory_ver_2(product_name):
    product = Product.objects.get(name=product_name)

    current_accounting_period_id = AccoutingPeriod.objects.aggregate(Max('id')).get("id__max", 0)
    accounting_periods_id = AccoutingPeriod.objects.exclude(pk=current_accounting_period_id).values_list('id', flat=True)
    import_shipments_id = ImportShipment.objects.filter(current_accounting_period__in=accounting_periods_id).values_list('id', flat=True)
    product_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id__in=import_shipments_id,
                                                                                                        product_id=product,
                                                                                                        quantity_remain__gt=0)
    
    product_purchases_count = product_purchases.count()
    print(product_purchases_count)

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def starting_inventory_ver_3(product_name):
    product = Product.objects.get(name=product_name)
    current_accounting_period_obj = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    starting_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        product_id=product,
        quantity_remain__gt=0,
        import_shipment_id__date__lt=current_accounting_period_obj.date_applied
    )

    starting_purchases_count = starting_purchases.count()
    print(starting_purchases_count)

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def testing_queryset():
    import_shipment_obj = ImportShipment.objects.get(import_shipment_code='NEW0022')
    queryset1 = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id=import_shipment_obj,
        quantity_remain__gt=0
    )

    pre_queryset2 = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        quantity_remain__gt=0
    )
    queryset2 = pre_queryset2.filter(import_shipment_id=import_shipment_obj)

    print(f"Queryset1 - {len(queryset1)}: ", queryset1)
    print("~~~~~~~~~~~~~~~~~~")
    print(f"Queryset2 - {len(queryset2)}: ", queryset2)

    connection_queries = connection.queries

    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def testing_queryset2():
    product = Product.objects.get(name='Cebraton')
    queryset1 = ImportShipment.objects.select_related('supplier_id').all()
    # Try to find the way to connect
    # the import shipments containing at least
    # one chosen's product purchase in the efficient way
    queryset2 = queryset1.filter(
        importpurchase_import_purchases_package__product_id=product
    ).values('import_shipment_code').distinct().order_by('id')

    for queryset in queryset2:
        print(queryset)

    print(len(queryset2))

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def testing_queryset3():
    product = Product.objects.get(name='Cebraton')
    queryset1 = ImportShipment.objects.select_related('supplier_id').all().values('import_shipment_code')
    queryset2 = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        product_id=product,
        import_shipment_id__import_shipment_code__in=queryset1
    ).values('import_shipment_id__import_shipment_code').distinct().order_by('import_shipment_id_id')

    for queryset in queryset2:
        print(queryset)

    print(len(queryset2))

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def testing_chaining_queryset():

    product = Product.objects.get(name='Cebraton')

    queryset = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').all()
    queryset = queryset.filter(product_id=product)
    queryset = queryset.filter(quantity_remain__gt=50)

    print(queryset)

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def assigning_starting_inventory():
    accounting_periods = AccoutingPeriod.objects.select_related('warehouse_management_method').exclude(pk=20)
    for accounting_period in accounting_periods:
        prev_period = AccoutingPeriod.objects.select_relate('warehouse_management_method').filter(
            pk__lt=accounting_period.id
        ).order_by('-id').first()
        accounting_period.starting_inventory = prev_period.ending_inventory
        accounting_period.save(update_fields=["starting_inventory"])

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def assigning_ending_inventory():
    accounting_periods = AccoutingPeriod.objects.select_related('warehouse_management_method').exclude(pk=20)
    for accounting_period in accounting_periods:
        import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').filter(
            current_accounting_period=accounting_period
        )
        total_import_shipments_value = import_shipments.aggregate(Sum('total_shipment_value')).get('total_shipment_value__sum', 0)
        accounting_period.ending_inventory = accounting_period.starting_inventory + total_import_shipments_value
        accounting_period.save(update_fields=["ending_inventory"])
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def testing_select_for_update():
    accounting_period_obj = AccoutingPeriod.objects.latest('id')
    product = Product.objects.get(name='Cebraton')

    with transaction.atomic():
        accounting_period_inventory_objs1 = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').select_for_update().filter(
            accounting_period_id=accounting_period_obj,
            product_id__name=product.name
        )
        accounting_period_inventory_objs1.update(starting_inventory=10)
        accounting_period_inventory_objs2 = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').select_for_update().all()
        list(accounting_period_inventory_objs2)
        accounting_period_inventory_objs2.update(ending_inventory=20)

    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def testing_locking_transaction():
    with transaction.atomic():
        accounting_period_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').select_for_update().filter(
            product_id__name = 'Cebraton'
        )
        for obj in accounting_period_inventory:
            with transaction.atomic():
                product = obj.product_id
                product.minimum_quantity += 10
                product.save(update_fields=["minimum_quantity"])
            
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@transaction.atomic()    
@query_debugger
def testing_select_related():
    purchase = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').select_for_update(of=("self", "import_shipment_id")).latest('id')
    print(purchase)
    connection_queries = connection.queries
    for connection_query in connection_queries:
        print(connection_query)

@query_debugger
def check_import_inventory():
    current_accounting_period = AccoutingPeriod.objects.latest('id')
    product_current_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__current_accounting_period = current_accounting_period,
        import_shipment_id__total_shipment_value__gt = 0
    )
    product_inventory_container = {}

    for purchase in product_current_purchases:
        if purchase.product_id.name not in product_inventory_container:
            product_inventory_container[purchase.product_id.name] = {
                'import_quantity': purchase.quantity_import,
                'import_inventory': purchase.quantity_import * purchase.import_cost
            }
        else:
            product_inventory_container[purchase.product_id.name]['import_quantity'] += purchase.quantity_import
            product_inventory_container[purchase.product_id.name]['import_inventory'] += purchase.quantity_import * purchase.import_cost

    products_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )
    for product in products_inventory:
        product_current_inventory = product_inventory_container[product.product_id.name]

        if product_current_inventory['import_quantity'] != product.import_quantity:
            return False
        if product_current_inventory['import_inventory'] != product.import_inventory:
            return False
        
        print(f"""
            From Import Purchase:
              - Import quantity: {product_current_inventory['import_quantity']}
              - Import inventory : {product_current_inventory['import_inventory']}
            From Accounting Period Inventory:
              - Import quantity: {product.import_quantity}
              - Import inventory: {product.import_inventory}
        """)

    return True

@query_debugger
def check_month_inventory(month):
    current_year = datetime.now().year
    first_day_of_month = datetime(current_year, month, 1).date()
    get_last_day_of_month = calendar.monthrange(current_year, month)[1]
    last_day_of_month = datetime(current_year, month, get_last_day_of_month).date()
    products_import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__date__gte = first_day_of_month,
        import_shipment_id__date__lte = last_day_of_month
    )
    products_inventory = products_import_purchases.values('product_id__name').annotate(
        total_quantity = Sum('quantity_import'),
        total_inventory = Sum('value_import')
    )
    group_by_products = {}
    group_by_total_quantity = 0
    group_by_total_inventory = 0
    for product in products_inventory:
        group_by_products[product['product_id__name']] = {
            'total_quantity': product['total_quantity'],
            'total_inventory': product['total_inventory']
        }
        group_by_total_quantity += product['total_quantity']
        group_by_total_inventory += product['total_inventory']

    iterable_products = {}
    iterable_total_quantity = 0
    iterable_total_inventory = 0

    for purchase in products_import_purchases:
        if purchase.product_id.name not in iterable_products:
            iterable_products[purchase.product_id.name] = {
                'total_quantity': purchase.quantity_import,
                'total_inventory': purchase.value_import
            }
        else:
            iterable_products[purchase.product_id.name]['total_quantity'] += purchase.quantity_import
            iterable_products[purchase.product_id.name]['total_inventory'] += purchase.value_import

        iterable_total_quantity += purchase.quantity_import
        iterable_total_inventory += purchase.value_import
    
    if products_inventory.count() == 0:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Không có dữ liệu")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    
    no_bug = 0

    for product, value in group_by_products.items():
        iterable_product = iterable_products[product]
        print(f"""Group by product {product}: total quantity {value['total_quantity']} total inventory {value['total_inventory']} ~
        Iterable product {iterable_product}: total quantity {iterable_product['total_quantity']} total inventory {iterable_product['total_inventory']}
        """)
        if value['total_quantity'] != iterable_product['total_quantity'] or value['total_inventory'] != iterable_product['total_inventory']:
            print("False")
            no_bug = 1
            break
    
    print(f"Group by total quantity: {group_by_total_quantity}, Iterable total quantity: {iterable_total_quantity}")
    print(f"Group by total inventory: {group_by_total_inventory}, Iterable total inventory: {iterable_total_inventory}")
    if group_by_total_quantity != iterable_total_quantity or group_by_total_inventory != iterable_total_inventory:
        no_bug = 1
    
    for connection_query in connection.queries:
        print(connection_query)
    if no_bug == 1:
        return False
    return True

@query_debugger
def check_quarter_inventory(quarter):
    quarters = {
        1: {'quarter_name': "Quý 1", 'months': [1,2,3]},
        2: {'quarter_name': "Quý 2", 'months': [4,5,6]},
        3: {'quarter_name': "Quý 3", 'months': [7,8,9]},
        4: {'quarter_name': "Quý 4", 'months': [10,11,12]},
    }
    quarter_obj = quarters[quarter]
    quarter_months = quarter_obj['months']
    first_month = quarter_months[0]
    last_month = quarter_months[2]
    current_year = datetime.now().year
    first_day_of_quarter = datetime(current_year, first_month, 1)
    get_last_day_of_quarter = calendar.monthrange(current_year, last_month)[1]
    last_day_of_quarter = datetime(current_year, last_month, get_last_day_of_quarter)

    products_import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
        import_shipment_id__date__gte = first_day_of_quarter,
        import_shipment_id__date__lte = last_day_of_quarter
    )
    products_inventory = products_import_purchases.values('product_id__name').annotate(
        total_quantity = Sum('quantity_import'),
        total_inventory = Sum('value_import')
    )
    group_by_products = {}
    group_by_total_quantity = 0
    group_by_total_inventory = 0
    for product in products_inventory:
        group_by_products[product['product_id__name']] = {
            'total_quantity': product['total_quantity'],
            'total_inventory': product['total_inventory']
        }
        group_by_total_quantity += product['total_quantity']
        group_by_total_inventory += product['total_inventory']

    iterable_products = {}
    iterable_total_quantity = 0
    iterable_total_inventory = 0

    for purchase in products_import_purchases:
        if purchase.product_id.name not in iterable_products:
            iterable_products[purchase.product_id.name] = {
                'total_quantity': purchase.quantity_import,
                'total_inventory': purchase.value_import
            }
        else:
            iterable_products[purchase.product_id.name]['total_quantity'] += purchase.quantity_import
            iterable_products[purchase.product_id.name]['total_inventory'] += purchase.value_import

        iterable_total_quantity += purchase.quantity_import
        iterable_total_inventory += purchase.value_import
    
    if products_inventory.count() == 0:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Không có dữ liệu")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    
    no_bug = 0

    for product, value in group_by_products.items():
        iterable_product = iterable_products[product]
        print(f"""Group by product {product}: total quantity {value['total_quantity']} total inventory {value['total_inventory']} ~
        Iterable product {iterable_product}: total quantity {iterable_product['total_quantity']} total inventory {iterable_product['total_inventory']}
        """)
        if value['total_quantity'] != iterable_product['total_quantity'] or value['total_inventory'] != iterable_product['total_inventory']:
            print("False")
            no_bug = 1
            break
    
    print(f"Group by total quantity: {group_by_total_quantity}, Iterable total quantity: {iterable_total_quantity}")
    print(f"Group by total inventory: {group_by_total_inventory}, Iterable total inventory: {iterable_total_inventory}")
    if group_by_total_quantity != iterable_total_quantity or group_by_total_inventory != iterable_total_inventory:
        no_bug = 1
    
    for connection_query in connection.queries:
        print(connection_query)
        
    if no_bug == 1:
        return False
    return True

@query_debugger
def check_day_export(product_id, day):
    product_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        export_shipment_id__date = day,
        product_id = product_id
    )
    group_by_products = {}
    group_by_export_orders = product_export_orders.values('product_id__name').annotate(
        total_quantity_export = Sum('quantity_export'),
        total_cogs = Sum('total_order_value')
    )

    group_by_total_quantity_export = 0
    group_by_total_cogs = 0
    for product in group_by_export_orders:
        group_by_products[product['product_id__name']] = {
            'total_quantity_export': product['total_quantity_export'],
            'total_cogs': product['total_cogs']
        }
        group_by_total_quantity_export += product['total_quantity_export']
        group_by_total_cogs += product['total_cogs']

    iterable_products = {}
    iterable_total_quantity_export = 0
    iterable_total_cogs = 0

    for product in product_export_orders:
        if product.product_id.name not in iterable_products:
            iterable_products[product.product_id.name] = {
                'total_quantity_export': product.quantity_export,
                'total_cogs': product.total_order_value
            }
        else:
            iterable_products[product.product_id.name]['total_quantity_export'] += product.quantity_export
            iterable_products[product.product_id.name]['total_cogs'] += product.total_order_value

        iterable_total_quantity_export += product.quantity_export
        iterable_total_cogs += product.total_order_value

    no_bug = 0
    for product, value in group_by_products.items():
        iterable_product = iterable_products[product]
        if value['total_quantity_export'] != iterable_product['total_quantity_export'] or value['total_cogs'] != iterable_product['total_cogs']:
            print("Bug found")
            no_bug = 1
    
    if group_by_total_quantity_export != iterable_total_quantity_export or group_by_total_cogs != iterable_total_cogs:
        print("Bug found")
        no_bug = 1

    for connection_query in connection.queries:
        print(connection_query)

    if no_bug == 1:
        return False
    
@query_debugger
def update_export_shipments():
    export_shipments = ExportShipment.objects.select_related('agency_id', 'current_accounting_period').all()
    for export_shipment in export_shipments:
        export_shipment_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id = export_shipment
        )
        sub_revenue = export_shipment_orders.values('export_shipment_id__export_shipment_code').annotate(
            sub_revenue = Sum(F("quantity_export") * F("unit_price"))
        )
        sub_revenue_obj = sub_revenue[0]
        print("~~~~~~~~~~~~~~~~~~~")
        print(sub_revenue_obj)
        print("~~~~~~~~~~~~~~~~~~~")
        export_shipment.shipment_revenue = sub_revenue_obj['sub_revenue']

    # update_export_shipments = ExportShipment.objects.bulk_update(export_shipments, ["shipment_revenue"])
    # print(update_export_shipments)
    for connection_query in connection.queries:
        print(connection_query)

@query_debugger
def update_period_revenue(product_id):
    periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        product_id = product_id
    )
    for period in periods_inventory:
        export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__current_accounting_period = period.accounting_period_id,
            product_id = product_id
        )
        current_period_product_revenue = export_orders.values('product_id__name').annotate(
            revenue = Sum(F("quantity_export") * F("unit_price"))
        )
        current_period_product_revenue_obj = current_period_product_revenue[0]

        print("~~~~~~~~~~~~~~~~~~~")
        print(current_period_product_revenue_obj)
        print("~~~~~~~~~~~~~~~~~~~")

        period.total_revenue = current_period_product_revenue_obj['revenue']
    
    update_periods_revenue = AccountingPeriodInventory.objects.bulk_update(periods_inventory, ["total_revenue"])
    print(update_periods_revenue)

    for connection_query in connection.queries:
        print(connection_query)

@query_debugger
def check_period_revenue():
    periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').all()
    total_period_revenue = periods_inventory.aggregate(Sum('total_revenue')).get('total_revenue__sum', 0)
    export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').all()
    total_exports_order_revenue = export_orders.aggregate(
        total_revenue = Sum(F("quantity_export") * F("unit_price"))
    ).get('total_revenue', 0)
    if total_period_revenue == total_exports_order_revenue:
        print(f"total_period_revenue: {total_period_revenue} = total_exports_order_revenue: {total_exports_order_revenue}")
        print("True")
    for connection_query in connection.queries:
        print(connection_query)
    return total_period_revenue == total_exports_order_revenue

@query_debugger
def check_each_product_revenue(product_id):
    product_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        product_id = product_id
    )
    total_product_periods_revenue = product_periods_inventory.aggregate(Sum('total_revenue')).get('total_revenue__sum', 0)
    product_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        product_id = product_id
    )
    total_product_orders_revenue = product_export_orders.aggregate(
        total_product_revenue = Sum(F("quantity_export") * F("unit_price"))
    ).get('total_product_revenue', 0)
    if total_product_periods_revenue == total_product_orders_revenue:
        print(f"total_product_periods_revenue: {total_product_periods_revenue} = total_product_orders_revenue: {total_product_orders_revenue}")
        print("True")
    for connection_query in connection.queries:
        print(connection_query)
    return total_product_periods_revenue == total_product_orders_revenue
    
@query_debugger
def check_each_product_revenue_on_per_accounting_period(product_id):
    product_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        product_id = product_id
    )
    no_bug = 0
    for period in product_periods_inventory:
        print("+++++++++++++++++++++++")
        print(period.accounting_period_id.pk)
        product_period_revenue = product_periods_inventory.filter(
            accounting_period_id = period.accounting_period_id
        ).aggregate(Sum('total_revenue')).get('total_revenue__sum', 0)

        product_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__current_accounting_period = period.accounting_period_id,
            product_id = product_id
        )

        total_product_revenue = product_export_orders.aggregate(
            total_revenue = Sum(F("quantity_export") * F("unit_price"))
        ).get('total_revenue', 0)

        if product_period_revenue != total_product_revenue:
            print(f"product_period_revenue: {product_period_revenue} != total_product_revenue: {total_product_revenue}")
            print("False")
            no_bug = 1
            break

        print(f"product_period_revenue: {product_period_revenue} = total_product_revenue: {total_product_revenue}")
        print("~~~~~~~~~~~~~~~~~~~~~~~")
    
    for connection_query in connection.queries:
        print(connection_query)

    if no_bug == 1:
        return False
    return True

def get_quarters():
    quarters = {
        1: {'quarter_name': "Quý 1", 'months': [1,2,3]},
        2: {'quarter_name': "Quý 2", 'months': [4,5,6]},
        3: {'quarter_name': "Quý 3", 'months': [7,8,9]},
        4: {'quarter_name': "Quý 4", 'months': [10,11,12]},
    }
    return quarters

def get_months():
    months = {
        1: "Tháng 1",
        2: "Tháng 2",
        3: "Tháng 3",
        4: "Tháng 4",
        5: "Tháng 5",
        6: "Tháng 6",
        7: "Tháng 7",
        8: "Tháng 8",
        9: "Tháng 9",
        10: "Tháng 10",
        11: "Tháng 11",
        12: "Tháng 12",
    }
    return months

@query_debugger
def check_quarter_product_revenue():
    current_year = 2023
    quarters = get_quarters()

    for quarter, value in quarters.items():
        first_day_of_quarter = datetime(current_year, value['months'][0], 1).date()
        get_last_day_of_quarter = calendar.monthrange(current_year, value['months'][2])[1]
        last_day_of_quarter = datetime(current_year, value['months'][2], get_last_day_of_quarter).date()
        export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_quarter,
            export_shipment_id__date__lte = last_day_of_quarter,
        )
        products_revenue = export_orders.values('product_id__name').annotate(
            revenue = Sum(F("quantity_export") * F("unit_price"))
        )
        print(f"Quarter: {quarter}")
        for product in products_revenue:
            print(f"Product {product['product_id__name']}: revenue {product['revenue']}")

@query_debugger
def check_month_product_revenue():
    current_year = 2023
    months = get_months()

    for month in months:
        first_day_of_month = datetime(current_year, month, 1).date()
        get_last_day_of_month = calendar.monthrange(current_year, month)[1]
        last_day_of_month = datetime(current_year, month, get_last_day_of_month)
        export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_month,
            export_shipment_id__date__lte = last_day_of_month,
        )
        products_revenue = export_orders.values('product_id__name').annotate(
            revenue = Sum(F("quantity_export") * F("unit_price"))
        )
        print("++++++++++++++++++++")
        print(f"Month: {month}")
        for product in products_revenue:
            print(f"Product {product['product_id__name']}: revenue {product['revenue']}")
        print("------------------------")

@query_debugger
def check_day_product_revenue(day):
    current_year = 2023
    export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
        export_shipment_id__date = day
    )
    products_revenue = export_orders.values('product_id__name').annotate(
        revenue = Sum(F("quantity_export") * F("unit_price"))
    )
    day_format = datetime.strftime(day, "%d/%m/%Y")
    print(f"Day: {day_format}")
    for product in products_revenue:
        print(f"Product {product['product_id__name']}: revenue {product['revenue']}")