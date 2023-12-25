from . views import *
from urllib.parse import urlencode

def default_accounting_period_id():
    default_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    default_accounting_period_id = default_accounting_period.id
    return default_accounting_period_id

def default_year():
    default_year = datetime.now().year
    return default_year

def default_quarter(quarters):
    current_month = datetime.now().month
    for quarter, value in quarters.items():
        if current_month in value['months']:
            default_quarter = quarter
            return default_quarter
    return None

def default_month():
    default_month = datetime.now().month
    return default_month

def default_day():
    default_date = date.today()
    return default_date

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

def get_modified_path(request, GET_requests_params):
    # path handling
    path = request.path
    modified_path = path

    if 'period_type' in GET_requests_params:
        modified_path += f"?period_type={GET_requests_params['period_type']}"
    if 'chosen_period_type_param' in GET_requests_params:
        modified_path += f"&{GET_requests_params['period_type']}={GET_requests_params['chosen_period_type_param']}"

    return modified_path

def reports_revenue(request):
    """
    Dislaying each product's revenue 
    according to chosen period type
    """
    context = {}
    unchosen_period_types = {
        'year': "Năm",
        'quarter': "Quý",
        'month': "Tháng",
        'day': "Ngày",
        'accounting_period': "Kỳ kế toán"
    }
    DEFAULT_PERIOD_TYPE = "accounting_period"
    chosen_period_type = request.GET.get("period_type", "")

    if chosen_period_type not in unchosen_period_types:
        chosen_period_type = DEFAULT_PERIOD_TYPE
    chosen_period_name = unchosen_period_types[chosen_period_type]

    try:
        del unchosen_period_types[chosen_period_type]
    except KeyError:
        print("Key not found")

    GET_requests_params = {}

    # Attach these three keys to context for filter-bar
    context['unchosen_period_types'] = unchosen_period_types
    context['chosen_period_type'] = chosen_period_type
    context['chosen_period_name'] = chosen_period_name

    # JSON string for google chart
    role = {'role': "style"}
    revenue_arr = [
        ["Sản phẩm", "Doanh thu", role ]
    ]

    if chosen_period_type == 'accounting_period':
        chosen_accounting_period_id = default_accounting_period_id()

        accounting_period_id_param = request.GET.get("accounting_period", None)

        if accounting_period_id_param:
            chosen_accounting_period_id = validating_period_id(accounting_period_id_param)

        # Rendering chosen_accounting_period_id for getting selected accounting period
        # in the select input
        context["chosen_accounting_period_id"] = chosen_accounting_period_id

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_accounting_period_id

        # Get all accounting period in template
        # for user to choose
        all_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').all()
        context["all_accounting_period"] = all_accounting_period

        periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id = chosen_accounting_period_id
        )
        total_products_revenue = periods_inventory.aggregate(
            total_products_export = Sum("total_quantity_export"),
            total_products_revenue = Sum("total_revenue")
        )
        each_product_revenue = periods_inventory.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_quantity_export = F("total_quantity_export"),
            product_revenue = F("total_revenue")
        ).order_by('-product_revenue')
    
    if chosen_period_type == 'year':
        # Get the current year as an int
        chosen_year = default_year()

        year_param = request.GET.get("year", None)
        if year_param:
            chosen_year = validating_year(year_param)

        # Displaying the chosen year for user
        # in the reports/import_section.html template
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_year

        first_day_of_the_year = datetime(chosen_year, 1, 1).date()
        last_day_of_the_year = datetime(chosen_year, 12, 31).date()

        periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id__date_applied__gte = first_day_of_the_year,
            accounting_period_id__date_end__lte = last_day_of_the_year
        )
        total_products_revenue = periods_inventory.aggregate(
            total_products_export = Sum("total_quantity_export"),
            total_products_revenue = Sum("total_revenue")
        )
        each_product_revenue = periods_inventory.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_quantity_export = Sum("total_quantity_export"),
            product_revenue = Sum("total_revenue")
        ).order_by('-product_revenue')
    
    if chosen_period_type == 'quarter':
        quarters = get_quarters()
        context['quarters'] = quarters

        # Return the key in quarters dictionary
        chosen_quarter = default_quarter(quarters)
        chosen_year = default_year()
        
        quarter_param = request.GET.get('quarter', None)
        year_param = request.GET.get('quarter_year', None)

        if quarter_param:
            chosen_quarter = validating_quarter(quarter_param)
        if year_param:
            chosen_year = validating_year(year_param)

        context['chosen_quarter'] = chosen_quarter
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_quarter}&quarter_year={chosen_year}"

        chosen_quarter_months = quarters[chosen_quarter]['months']
        first_month_of_quarter = chosen_quarter_months[0]
        last_month_of_quarter = chosen_quarter_months[2]
        first_day_of_quarter = datetime(chosen_year, first_month_of_quarter, 1).date()
        last_day_of_quarter = get_lastday_of_month(date(chosen_year, last_month_of_quarter, 1))

        export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_quarter,
            export_shipment_id__date__lte = last_day_of_quarter
        )
        total_products_revenue = export_orders.aggregate(
            total_products_export = Sum("quantity_export"),
            total_products_revenue = Sum(
                F("quantity_export") * F("unit_price")
            )
        )
        each_product_revenue = export_orders.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_quantity_export = Sum("quantity_export"),
            product_revenue = Sum(F("quantity_export") * F("unit_price"))
        ).order_by('-product_revenue')

    if chosen_period_type == 'month':
        months = get_months()
        context['months'] = months

        chosen_month = default_month()
        chosen_month_year = default_year()

        month_param = request.GET.get('month', None)
        month_year_param = request.GET.get('month_year', None)
        if month_param:
            chosen_month = validating_month(month_param)
        if month_year_param:
            chosen_month_year = validating_year(month_year_param)

        # Displaying chosen month & chosen month year for user
        # in the reports/import_section.html template
        context['chosen_month'] = chosen_month
        context['chosen_month_year'] = chosen_month_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_month}&chosen_month_year={chosen_month_year}"

        first_day_of_the_month = datetime(chosen_month_year, chosen_month, 1).date()
        last_day_of_the_month = get_lastday_of_month(first_day_of_the_month)

        export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_the_month,
            export_shipment_id__date__lte = last_day_of_the_month
        )
        total_products_revenue = export_orders.aggregate(
            total_products_export = Sum("quantity_export"),
            total_products_revenue = Sum(
                F("quantity_export") * F("unit_price")
            )
        )
        each_product_revenue = export_orders.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_quantity_export = Sum("quantity_export"),
            product_revenue = Sum(F("quantity_export") * F("unit_price"))
        ).order_by('-product_revenue')

    if chosen_period_type == 'day':
        chosen_date = default_day()

        date_param = request.GET.get("day", None)
        if date_param:
            chosen_date = validating_date(date_param)

        context['chosen_date'] = chosen_date

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_date

        export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date = chosen_date
        )
        total_products_revenue = export_orders.aggregate(
            total_products_export = Sum("quantity_export"),
            total_products_revenue = Sum(
                F("quantity_export") * F("unit_price")
            )
        )
        each_product_revenue = export_orders.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_quantity_export = Sum("quantity_export"),
            product_revenue = Sum(F("quantity_export") * F("unit_price"))
        ).order_by('-product_revenue')

    # If no records are found
    if each_product_revenue.count() == 0:
        context["non_period_found_msg"] = "Không có dữ liệu"
        return render(request, "major_features/reports/revenue.html", context)

    # path handling
    context['modified_path'] = get_modified_path(request, GET_requests_params)

    # pagination
    page_number = request.GET.get("page")
    pagination = Paginator(each_product_revenue, 5)
    page_obj = pagination.get_page(page_number)

    for product in page_obj:
        # Append JSON string to google chart array
        revenue_arr.append([product['product_id__name'], product['product_revenue'], "#01257D"])

    # Append total_revenue_arr as a column in the revenue chart
    revenue_arr.append(["Tổng doanh thu", total_products_revenue['total_products_revenue'], "#01257D"])

    # For rendering reports import section table
    context['page_obj'] = page_obj
    context['total_products_export'] = total_products_revenue['total_products_export']
    context['total_products_revenue'] = total_products_revenue['total_products_revenue']
    
    # For google chart
    context['revenue_arr'] = revenue_arr

    return render(request, "major_features/reports/revenue.html", context)

def reports_gross_profits(request):
    """
    Dislaying each product's gross profits 
    according to chosen period type
    """
    context = {}
    unchosen_period_types = {
        'year': "Năm",
        'quarter': "Quý",
        'month': "Tháng",
        'day': "Ngày",
        'accounting_period': "Kỳ kế toán"
    }
    DEFAULT_PERIOD_TYPE = "accounting_period"
    chosen_period_type = request.GET.get("period_type", "")

    if chosen_period_type not in unchosen_period_types:
        chosen_period_type = DEFAULT_PERIOD_TYPE
    chosen_period_name = unchosen_period_types[chosen_period_type]

    try:
        del unchosen_period_types[chosen_period_type]
    except KeyError:
        print("Key not found")

    GET_requests_params = {}

    # Attach these three keys to context for filter-bar
    context['unchosen_period_types'] = unchosen_period_types
    context['chosen_period_type'] = chosen_period_type
    context['chosen_period_name'] = chosen_period_name

    # JSON string for google chart
    role = {'role': "style"}
    gross_profits_arr = [
        ["Sản phẩm", "Lợi nhuận", role ]
    ]

    if chosen_period_type == 'accounting_period':
        chosen_accounting_period_id = default_accounting_period_id()

        accounting_period_id_param = request.GET.get("accounting_period", None)

        if accounting_period_id_param:
            chosen_accounting_period_id = validating_period_id(accounting_period_id_param)

        # Rendering chosen_accounting_period_id for getting selected accounting period
        # in the select input
        context["chosen_accounting_period_id"] = chosen_accounting_period_id

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_accounting_period_id

        # Get all accounting period in template
        # for user to choose
        all_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').all()
        context["all_accounting_period"] = all_accounting_period

        periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id = chosen_accounting_period_id
        )
        total_products_gross_profits = periods_inventory.aggregate(
            total_products_revenue = Sum("total_revenue"),
            total_products_cogs = Sum("total_cogs"),
            total_products_gross_profits = Sum("total_revenue") - Sum("total_cogs")
        )
        each_product_gross_profits = periods_inventory.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_revenue = F("total_revenue"),
            product_cogs = F("total_cogs"),
            product_gross_profits = F("total_revenue") - F("total_cogs")
        ).order_by('-product_gross_profits')

    if chosen_period_type == 'year':
        # Get the current year as an int
        chosen_year = default_year()

        year_param = request.GET.get("year", None)
        if year_param:
            chosen_year = validating_year(year_param)

        # Displaying the chosen year for user
        # in the reports/import_section.html template
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param']= chosen_year

        first_day_of_the_year = datetime(chosen_year, 1, 1).date()
        last_day_of_the_year = datetime(chosen_year, 12, 31).date()

        accounting_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id__date_applied__gte = first_day_of_the_year,
            accounting_period_id__date_end__lte = last_day_of_the_year
        )
        total_products_gross_profits = accounting_periods_inventory.aggregate(
            total_products_revenue = Sum("total_revenue"),
            total_products_cogs = Sum("total_cogs"),
            total_products_gross_profits = Sum("total_revenue") - Sum("total_cogs")
        )           
        each_product_gross_profits = accounting_periods_inventory.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_revenue = Sum("total_revenue"),
            product_cogs = Sum("total_cogs"),
            product_gross_profits = Sum(F("total_revenue") - F("total_cogs"))
        ).order_by('-product_gross_profits')
    
    if chosen_period_type == 'quarter':
        quarters = get_quarters()
        context['quarters'] = quarters

        # Return the key in quarters dictionary
        chosen_quarter = default_quarter(quarters)
        chosen_year = default_year()
        
        quarter_param = request.GET.get('quarter', None)
        year_param = request.GET.get('quarter_year', None)

        if quarter_param:
            chosen_quarter = validating_quarter(quarter_param)
        if year_param:
            chosen_year = validating_year(year_param)

        context['chosen_quarter'] = chosen_quarter
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_quarter}&quarter_year={chosen_year}"

        chosen_quarter_months = quarters[chosen_quarter]['months']
        first_month_of_quarter = chosen_quarter_months[0]
        last_month_of_quarter = chosen_quarter_months[2]
        first_day_of_quarter = datetime(chosen_year, first_month_of_quarter, 1).date()
        last_day_of_quarter = get_lastday_of_month(date(chosen_year, last_month_of_quarter, 1))

        products_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_quarter,
            export_shipment_id__date__lte = last_day_of_quarter
        )
        total_products_gross_profits = products_export_orders.aggregate(
            total_products_revenue = Sum(F("quantity_export") * F("unit_price")),
            total_products_cogs = Sum("total_order_value"),
            total_products_gross_profits = Sum(
                (F("quantity_export") * F("unit_price")) - F("total_order_value")
            )
        )
        each_product_gross_profits = products_export_orders.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_revenue = Sum(F("quantity_export") * F("unit_price")),
            product_cogs = Sum("total_order_value"),
            product_gross_profits = Sum(
                    (F("quantity_export") * F("unit_price")) - F("total_order_value")
                )
        ).order_by('-product_gross_profits')

    if chosen_period_type == 'month':
        months = get_months()
        context['months'] = months

        chosen_month = default_month()
        chosen_month_year = default_year()

        month_param = request.GET.get('month', None)
        month_year_param = request.GET.get('month_year', None)
        if month_param:
            chosen_month = validating_month(month_param)
        if month_year_param:
            chosen_month_year = validating_year(month_year_param)

        # Displaying chosen month & chosen month year for user
        # in the reports/import_section.html template
        context['chosen_month'] = chosen_month
        context['chosen_month_year'] = chosen_month_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_month}&chosen_month_year={chosen_month_year}"

        first_day_of_the_month = datetime(chosen_month_year, chosen_month, 1).date()
        last_day_of_the_month = get_lastday_of_month(first_day_of_the_month)

        product_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_the_month,
            export_shipment_id__date__lte = last_day_of_the_month,
        )
        total_products_gross_profits = product_export_orders.aggregate(
            total_products_revenue = Sum(F("quantity_export") * F("unit_price")),
            total_products_cogs = Sum("total_order_value"),
            total_products_gross_profits = Sum(
                (F("quantity_export") * F("unit_price")) - F("total_order_value")
            )
        )
        each_product_gross_profits = product_export_orders.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_revenue = Sum(F("quantity_export") * F("unit_price")),
            product_cogs = Sum("total_order_value"),
            product_gross_profits = Sum(
                (F("quantity_export") * F("unit_price")) - F("total_order_value")
            )
        ).order_by('-product_gross_profits')

    if chosen_period_type == 'day':
        # Set default day for filter-bar to the current day
        chosen_date = default_day()

        date_param = request.GET.get("day", None)
        if date_param:
            chosen_date = validating_date(date_param)

        context['chosen_date'] = chosen_date

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_date

        product_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date = chosen_date
        )
        total_products_gross_profits = product_export_orders.aggregate(
            total_products_revenue = Sum(F("quantity_export") * F("unit_price")),
            total_products_cogs = Sum("total_order_value"),
            total_products_gross_profits = Sum(
                (F("quantity_export") * F("unit_price")) - F("total_order_value")
            )
        )
        each_product_gross_profits = product_export_orders.values('product_id__name').annotate(
            product_category = F("product_id__category_name__name"),
            product_revenue = Sum(F("quantity_export") * F("unit_price")),
            product_cogs = Sum("total_order_value"),
            product_gross_profits = Sum(
                (F("quantity_export") * F("unit_price")) - F("total_order_value")
            )
        ).order_by('-product_gross_profits')
    
    # If no records are found
    if each_product_gross_profits.count() == 0:
        context["non_period_found_msg"] = "Không có dữ liệu"
        return render(request, "major_features/reports/gross_profits.html", context)

    # path handling
    context['modified_path'] = get_modified_path(request, GET_requests_params)

    # pagination
    page_number = request.GET.get("page")
    pagination = Paginator(each_product_gross_profits, 5)
    page_obj = pagination.get_page(page_number)

    for product in page_obj:
        gross_profits_arr.append([product['product_id__name'], product['product_gross_profits'], "#01257D"])

    # Append total_gross_profits to gross_profits_arr for the gross_profits chart
    gross_profits_arr.append(["Tổng lợi nhuận", total_products_gross_profits['total_products_gross_profits'], "#01257D"])

    # For rendering reports import section table
    context['page_obj'] = page_obj
    context['total_products_revenue'] = total_products_gross_profits['total_products_revenue']
    context['total_products_cogs'] = total_products_gross_profits['total_products_cogs']
    context['total_gross_profits'] = total_products_gross_profits['total_products_gross_profits']
    
    # For google chart
    context['gross_profits_arr'] = gross_profits_arr

    return render(request, "major_features/reports/gross_profits.html", context)
        
def reports_import_section(request):
    """
    Dislaying each product's import inventory & import quantity 
    according to chosen period type
    """
    context = {}
    unchosen_period_types = {
        'year': "Năm",
        'quarter': "Quý",
        'month': "Tháng",
        'day': "Ngày",
        'accounting_period': "Kỳ kế toán"
    }
    DEFAULT_PERIOD_TYPE = "accounting_period"
    chosen_period_type = request.GET.get("period_type", "")

    if chosen_period_type not in unchosen_period_types:
        chosen_period_type = DEFAULT_PERIOD_TYPE
    chosen_period_name = unchosen_period_types[chosen_period_type]

    try:
        del unchosen_period_types[chosen_period_type]
    except KeyError:
        print("Key not found")

    GET_requests_params = {}

    # Attach these three keys to context for filter-bar
    context['unchosen_period_types'] = unchosen_period_types
    context['chosen_period_type'] = chosen_period_type
    context['chosen_period_name'] = chosen_period_name

    # JSON string for google chart
    role = {'role': "style"}
    import_inventory_data_arr = [
        ["Sản phẩm", "Giá trị", role ]
    ]
    import_quantity_data_arr = [
        ["Sản phẩm", "Số lượng", role ]
    ]

    if chosen_period_type == 'accounting_period':
        chosen_accounting_period_id = default_accounting_period_id()

        accounting_period_id_param = request.GET.get("accounting_period", None)

        if accounting_period_id_param:
            chosen_accounting_period_id = validating_period_id(accounting_period_id_param)

        # Rendering chosen_accounting_period_id for getting selected accounting period
        # in the select input
        context["chosen_accounting_period_id"] = chosen_accounting_period_id

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_accounting_period_id

        # Get all accounting period in template
        # for user to choose
        all_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').all()
        context["all_accounting_period"] = all_accounting_period

        periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id = chosen_accounting_period_id
        )
        total_products_import = periods_inventory.aggregate(
            total_import_quantity = Sum("import_quantity"),
            total_import_inventory = Sum("import_inventory")
        )
        each_product_import = periods_inventory.values('product_id__name').annotate(
            product_quantity_import = Sum("import_quantity"),
            product_inventory_import = Sum("import_inventory")
        ).order_by('-product_inventory_import')

    if chosen_period_type == 'year':
        # Get the current year as an int
        chosen_year = default_year()

        year_param = request.GET.get("year", None)
        if year_param:
            chosen_year = validating_year(year_param)

        # Displaying the chosen year for user
        # in the reports/import_section.html template
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param']= chosen_year

        first_day_of_the_year = datetime(chosen_year, 1, 1).date()
        last_day_of_the_year = datetime(chosen_year, 12, 31).date()

        accounting_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id__date_applied__gte = first_day_of_the_year,
            accounting_period_id__date_end__lte = last_day_of_the_year
        )
        total_products_import = accounting_periods_inventory.aggregate(
            total_import_quantity = Sum("import_quantity"),
            total_import_inventory = Sum("import_inventory")
        )
        each_product_import = accounting_periods_inventory.values('product_id__name').annotate(
            product_quantity_import = Sum("import_quantity"),
            product_inventory_import = Sum("import_inventory")
        ).order_by('-product_inventory_import')
    
    if chosen_period_type == 'quarter':
        quarters = get_quarters()
        context['quarters'] = quarters

        # Return the key in quarters dictionary
        chosen_quarter = default_quarter(quarters)
        chosen_year = default_year()
        
        quarter_param = request.GET.get('quarter', None)
        year_param = request.GET.get('quarter_year', None)

        if quarter_param:
            chosen_quarter = validating_quarter(quarter_param)
        if year_param:
            chosen_year = validating_year(year_param)

        context['chosen_quarter'] = chosen_quarter
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_quarter}&quarter_year={chosen_year}"

        chosen_quarter_months = quarters[chosen_quarter]['months']
        first_month_of_quarter = chosen_quarter_months[0]
        last_month_of_quarter = chosen_quarter_months[2]
        first_day_of_quarter = datetime(chosen_year, first_month_of_quarter, 1).date()
        last_day_of_quarter = get_lastday_of_month(date(chosen_year, last_month_of_quarter, 1))

        products_import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
            import_shipment_id__date__gte = first_day_of_quarter,
            import_shipment_id__date__lte = last_day_of_quarter
        )
        total_products_import = products_import_purchases.aggregate(
            total_import_quantity = Sum("quantity_import"),
            total_import_inventory = Sum("value_import")
        )
        each_product_import = products_import_purchases.values('product_id__name').annotate(
            product_quantity_import = Sum("quantity_import"),
            product_inventory_import = Sum("value_import")
        ).order_by('-product_inventory_import')

    if chosen_period_type == 'month':
        months = get_months()
        context['months'] = months

        chosen_month = default_month()
        chosen_month_year = default_year()

        month_param = request.GET.get('month', None)
        month_year_param = request.GET.get('month_year', None)
        if month_param:
            chosen_month = validating_month(month_param)
        if month_year_param:
            chosen_month_year = validating_year(month_year_param)

        # Displaying chosen month & chosen month year for user
        # in the reports/import_section.html template
        context['chosen_month'] = chosen_month
        context['chosen_month_year'] = chosen_month_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_month}&chosen_month_year={chosen_month_year}"

        first_day_of_the_month = datetime(chosen_month_year, chosen_month, 1).date()
        last_day_of_the_month = get_lastday_of_month(first_day_of_the_month)

        products_import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
            import_shipment_id__date__gte = first_day_of_the_month,
            import_shipment_id__date__lte = last_day_of_the_month
        )
        total_products_import = products_import_purchases.aggregate(
            total_import_quantity = Sum("quantity_import"),
            total_import_inventory = Sum("value_import")
        )
        each_product_import = products_import_purchases.values('product_id__name').annotate(
            product_quantity_import = Sum("quantity_import"),
            product_inventory_import = Sum("value_import")
        ).order_by('-product_inventory_import')

    if chosen_period_type == 'day':
        # Set default day for filter-bar to the current day
        chosen_date = default_day()

        date_param = request.GET.get("day", None)
        if date_param:
            chosen_date = validating_date(date_param)

        context['chosen_date'] = chosen_date

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_date

        products_import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
            import_shipment_id__date = chosen_date
        )
        total_products_import = products_import_purchases.aggregate(
            total_import_quantity = Sum("quantity_import"),
            total_import_inventory = Sum("value_import")
        )
        each_product_import = products_import_purchases.values('product_id__name').annotate(
            product_quantity_import = Sum("quantity_import"),
            product_inventory_import = Sum("value_import")
        ).order_by('-product_inventory_import')
    
    # If no records are found
    if each_product_import.count() == 0:
        context["non_period_found_msg"] = "Không có dữ liệu"
        return render(request, "major_features/reports/import_section.html", context)

    # path handling
    context['modified_path'] = get_modified_path(request, GET_requests_params)

    # pagination
    page_number = request.GET.get("page")
    pagination = Paginator(each_product_import, 5)
    page_obj = pagination.get_page(page_number)

    for product in page_obj:
        import_inventory_data_arr.append([product['product_id__name'], product['product_inventory_import'], "#01257D"])
        import_quantity_data_arr.append([product['product_id__name'], product['product_quantity_import'], "#01257D"])

    # Append total_gross_profits to gross_profits_arr for the gross_profits chart
    import_inventory_data_arr.append(["Tổng giá trị nhập kho", total_products_import['total_import_inventory'], "#01257D"])
    import_quantity_data_arr.append(["Tổng SL nhập kho", total_products_import['total_import_quantity'], "#01257D"])

    # For rendering reports import section table
    context['page_obj'] = page_obj
    context['total_import_quantity'] = total_products_import['total_import_quantity']
    context['total_import_inventory'] = total_products_import['total_import_inventory']
    
    # For google chart
    context['import_inventory_data_arr'] = import_inventory_data_arr
    context['import_quantity_data_arr'] = import_quantity_data_arr

    return render(request, "major_features/reports/import_section.html", context)

def reports_export_section(request):
    """
    Dislaying each product's total cogs & export quantity 
    according to chosen period type
    """
    context = {}
    unchosen_period_types = {
        'year': "Năm",
        'quarter': "Quý",
        'month': "Tháng",
        'day': "Ngày",
        'accounting_period': "Kỳ kế toán"
    }
    DEFAULT_PERIOD_TYPE = "accounting_period"
    chosen_period_type = request.GET.get("period_type", "")

    if chosen_period_type not in unchosen_period_types:
        chosen_period_type = DEFAULT_PERIOD_TYPE
    chosen_period_name = unchosen_period_types[chosen_period_type]

    try:
        del unchosen_period_types[chosen_period_type]
    except KeyError:
        print("Key not found")

    GET_requests_params = {}

    # Attach these three keys to context for filter-bar
    context['unchosen_period_types'] = unchosen_period_types
    context['chosen_period_type'] = chosen_period_type
    context['chosen_period_name'] = chosen_period_name

    # JSON string for google chart
    role = {'role': "style"}
    export_value_data_arr = [
        ["Sản phẩm", "Giá trị", role ]
    ]
    export_quantity_data_arr = [
        ["Sản phẩm", "Số lượng", role ]
    ]

    if chosen_period_type == 'accounting_period':
        chosen_accounting_period_id = default_accounting_period_id()

        accounting_period_id_param = request.GET.get("accounting_period", None)

        if accounting_period_id_param:
            chosen_accounting_period_id = validating_period_id(accounting_period_id_param)

        # Rendering chosen_accounting_period_id for getting selected accounting period
        # in the select input
        context["chosen_accounting_period_id"] = chosen_accounting_period_id

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_accounting_period_id

        # Get all accounting period in template
        # for user to choose
        all_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').all()
        context["all_accounting_period"] = all_accounting_period

        periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id = chosen_accounting_period_id
        )
        total_products_export = periods_inventory.aggregate(
            total_export_quantity = Sum("total_quantity_export"),
            total_export_value = Sum("total_cogs")
        )
        each_product_export = periods_inventory.values('product_id__name').annotate(
            product_quantity_export = Sum("total_quantity_export"),
            product_cogs = Sum("total_cogs")
        ).order_by('-product_cogs')

    if chosen_period_type == 'year':
        # Get the current year as an int
        chosen_year = default_year()

        year_param = request.GET.get("year", None)
        if year_param:
            chosen_year = validating_year(year_param)

        # Displaying the chosen year for user
        # in the reports/import_section.html template
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param']= chosen_year

        first_day_of_the_year = datetime(chosen_year, 1, 1).date()
        last_day_of_the_year = datetime(chosen_year, 12, 31).date()

        accounting_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
            accounting_period_id__date_applied__gte = first_day_of_the_year,
            accounting_period_id__date_end__lte = last_day_of_the_year
        )
        total_products_export = accounting_periods_inventory.aggregate(
            total_export_quantity = Sum("total_quantity_export"),
            total_export_value = Sum("total_cogs")
        )
        each_product_export = accounting_periods_inventory.values('product_id__name').annotate(
            product_quantity_export = Sum("total_quantity_export"),
            product_cogs = Sum("total_cogs")
        ).order_by('-product_cogs')
    
    if chosen_period_type == 'quarter':
        quarters = get_quarters()
        context['quarters'] = quarters

        # Return the key in quarters dictionary
        chosen_quarter = default_quarter(quarters)
        chosen_year = default_year()
        
        quarter_param = request.GET.get('quarter', None)
        year_param = request.GET.get('quarter_year', None)

        if quarter_param:
            chosen_quarter = validating_quarter(quarter_param)
        if year_param:
            chosen_year = validating_year(year_param)

        context['chosen_quarter'] = chosen_quarter
        context['chosen_year'] = chosen_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_quarter}&quarter_year={chosen_year}"

        chosen_quarter_months = quarters[chosen_quarter]['months']
        first_month_of_quarter = chosen_quarter_months[0]
        last_month_of_quarter = chosen_quarter_months[2]
        first_day_of_quarter = datetime(chosen_year, first_month_of_quarter, 1).date()
        last_day_of_quarter = get_lastday_of_month(date(chosen_year, last_month_of_quarter, 1))

        products_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_quarter,
            export_shipment_id__date__lte = last_day_of_quarter
        )
        total_products_export = products_export_orders.aggregate(
            total_export_quantity = Sum("quantity_export"),
            total_export_value = Sum("total_order_value")
        )
        each_product_export = products_export_orders.values('product_id__name').annotate(
            product_quantity_export = Sum("quantity_export"),
            product_cogs = Sum("total_order_value")
        ).order_by('-product_cogs')

    if chosen_period_type == 'month':
        months = get_months()
        context['months'] = months

        chosen_month = default_month()
        chosen_month_year = default_year()

        month_param = request.GET.get('month', None)
        month_year_param = request.GET.get('month_year', None)
        if month_param:
            chosen_month = validating_month(month_param)
        if month_year_param:
            chosen_month_year = validating_year(month_year_param)

        # Displaying chosen month & chosen month year for user
        # in the reports/import_section.html template
        context['chosen_month'] = chosen_month
        context['chosen_month_year'] = chosen_month_year

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = f"{chosen_month}&chosen_month_year={chosen_month_year}"

        first_day_of_the_month = datetime(chosen_month_year, chosen_month, 1).date()
        last_day_of_the_month = get_lastday_of_month(first_day_of_the_month)

        products_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date__gte = first_day_of_the_month,
            export_shipment_id__date__lte = last_day_of_the_month,
        )
        total_products_export = products_export_orders.aggregate(
            total_export_quantity = Sum("quantity_export"),
            total_export_value = Sum("total_order_value")
        )
        each_product_export = products_export_orders.values('product_id__name').annotate(
            product_quantity_export = Sum("quantity_export"),
            product_cogs = Sum("total_order_value")
        ).order_by('-product_cogs')

    if chosen_period_type == 'day':
        # Set default day for filter-bar to the current day
        chosen_date = default_day()

        date_param = request.GET.get("day", None)
        if date_param:
            chosen_date = validating_date(date_param)

        context['chosen_date'] = chosen_date

        GET_requests_params['period_type'] = chosen_period_type
        GET_requests_params['chosen_period_type_param'] = chosen_date

        products_export_orders = ExportOrder.objects.select_related('export_shipment_id', 'product_id').filter(
            export_shipment_id__date = chosen_date
        )
        total_products_export = products_export_orders.aggregate(
            total_export_quantity = Sum("quantity_export"),
            total_export_value = Sum("total_order_value")
        )
        each_product_export = products_export_orders.values('product_id__name').annotate(
            product_quantity_export = Sum("quantity_export"),
            product_cogs = Sum("total_order_value")
        ).order_by('-product_cogs')
    
    # If no records are found
    if each_product_export.count() == 0:
        context["non_period_found_msg"] = "Không có dữ liệu"
        return render(request, "major_features/reports/export_section.html", context)

    # path handling
    context['modified_path'] = get_modified_path(request, GET_requests_params)

    # pagination
    page_number = request.GET.get("page")
    pagination = Paginator(each_product_export, 5)
    page_obj = pagination.get_page(page_number)

    for product in page_obj:
        export_value_data_arr.append([product['product_id__name'], product['product_cogs'], "#01257D"])
        export_quantity_data_arr.append([product['product_id__name'], product['product_quantity_export'], "#01257D"])

    # Append total_gross_profits to gross_profits_arr for the gross_profits chart
    export_value_data_arr.append(["Tổng giá trị xuất kho", total_products_export['total_export_value'], "#01257D"])
    export_quantity_data_arr.append(["Tổng SL xuất kho", total_products_export['total_export_quantity'], "#01257D"])

    # For rendering reports import section table
    context['page_obj'] = page_obj
    context['total_export_quantity'] = total_products_export['total_export_quantity']
    context['total_export_value'] = total_products_export['total_export_value']
    
    # For google chart
    context['export_value_data_arr'] = export_value_data_arr
    context['export_quantity_data_arr'] = export_quantity_data_arr

    return render(request, "major_features/reports/export_section.html", context)

# Validating functions for reports filter bar
def validating_period_id(period_id_param):
    """
    Checking valid accounting period id
    """

    try:
        accounting_period_id = int(period_id_param)
    except ValueError:
        raise Exception("Dữ liệu phải là số")
    
    return accounting_period_id

def validating_year(year_param):
    """
    Checking valid year as an positive int
    """
    try:
        chosen_year = int(year_param)
    except ValueError:
        raise Exception("Năm không hợp lệ")
    if chosen_year <= 0:
        raise Exception("Năm phải là số dương")
    
    return chosen_year

def validating_quarter(quarter_param):
    """
    Checking valid quarter as an positive int
    """
    try:
        chosen_quarter = int(quarter_param)
    except ValueError:
        raise Exception("Quý không hợp lệ")
    if chosen_quarter <= 0:
        raise Exception("Quý phải là số dương")
    if chosen_quarter > 4:
        raise Exception("Quý không tồn tại")
    return chosen_quarter

def validating_month(month_param):
    """
    Checking valid month as an positive int
    """
    try:
        chosen_month = int(month_param)
    except ValueError:
        raise Exception("Tháng không hợp lệ")  
    if chosen_month <= 0:
        raise Exception("Tháng phải là số dương")
    if chosen_month > 12:
        raise Exception("Tháng không tồn tại")
    
    return chosen_month

def validating_date(date_param):
    """
    Checking valid date as a valid date string
    """
    try:
        date_param_to_python = datetime.strptime(date_param, "%Y-%m-%d").date()
        chosen_date = date_param_to_python
    except ValueError:
        raise Exception("Ngày không hợp lệ")
    
    return chosen_date