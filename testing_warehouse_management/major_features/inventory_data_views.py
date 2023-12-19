import openpyxl
from io import BytesIO
from . views import *

def inventory_data(request):
    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    accounting_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )

    context = {
        'accounting_periods_inventory': accounting_periods_inventory
    }
    return render(request, "major_features/inventory_data/inventory_data.html", context)

def export_data_to_excel(request):
    # Get all current products period inventory
    current_accounting_period = AccoutingPeriod.objects.select_related('warehouse_management_method').latest('id')
    accounting_periods_inventory = AccountingPeriodInventory.objects.select_related('accounting_period_id', 'product_id').filter(
        accounting_period_id = current_accounting_period
    )

    # Create a new workbook
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "HTK kỳ kế toán hiện tại"

    # Populating data
    worksheet = populating_header(worksheet)

    # Create a temporary memory object using BytesIO
    excelfile = BytesIO()

    # Save the new one workbook to the excelfile
    workbook.save(excelfile)

    # Create the HttpResponse object with the appropriate headers
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="headers.xlsx"'

    # Write the workbook data as a bytes-like object
    # that was created before using BytesIO
    response.write(excelfile.getvalue())

    return response

def populating_header(worksheet):
    titles = [
        "STT",
        "Sản phẩm",
        "Danh mục",
        "Tồn kho đầu kỳ",
        "Nhập kho trong kỳ",
        "Xuất kho trong kỳ"
        "Tồn kho cuối kỳ"
    ]
    # STT cell header
    cell_A1 = worksheet["A1"]
    cell_A1.value = "STT"

    # Product cell header
    cell_B1 = worksheet["B1"]
    cell_B1.value = "Sản phẩm"

    # Category cell header
    cell_C1 = worksheet["C1"]
    cell_C1.value = "Danh mục"

    # Starting Inventory cell header
    cell_D1 = worksheet["D1"]
    cell_D1.value = "Tồn kho đầu kỳ"
    
    # Import Inventory cell header
    cell_F1 = worksheet["F1"]
    cell_F1.value = "Nhập kho trong kỳ"

    # Export cell header
    cell_H1 = worksheet["H1"]
    cell_H1.value = "Xuất kho trong kỳ"

    # Ending inventory cell header
    cell_J1 = worksheet["J1"]
    cell_J1.value = "Tồn kho cuối kỳ"

    # Merging rows
    worksheet.merge_cells("A1:A2")
    worksheet.merge_cells("B1:B2")
    worksheet.merge_cells("C1:C2")

    # Merging columns
    worksheet.merge_cells("D1:E1")
    worksheet.merge_cells("F1:G1")
    worksheet.merge_cells("H1:I1")
    worksheet.merge_cells("J1:K1")

    cell_D2 = worksheet["D2"]
    cell_D2.value = "Số lượng"
    cell_E2 = worksheet["E2"]
    cell_E2.value = "Giá trị"

    cell_F2 = worksheet["F2"]
    cell_F2.value = "Số lượng"
    cell_G2 = worksheet["G2"]
    cell_G2.value = "Giá trị"

    cell_H2 = worksheet["H2"]
    cell_H2.value = "Số lượng"
    cell_I2 = worksheet["I2"]
    cell_I2.value = "Giá trị"

    cell_J2 = worksheet["J2"]
    cell_J2.value = "Số lượng"
    cell_K2 = worksheet["K2"]
    cell_K2.value = "Giá trị"

    return worksheet