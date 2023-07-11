from django import forms
from django.forms import ModelForm
from django.db.models import Sum, Max
from . models import *

class KeepMethodForm(forms.Form):
    is_keep = forms.BooleanField(widget=forms.CheckboxInput(attrs={}), required=False, label="Có")


class DatePickerForm(forms.Form):
    date_field = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

class WarehouseManagementMethodForm(ModelForm):
    name = forms.ModelChoiceField(queryset=WarehouseManagementMethod.objects.filter(is_currently_applied=False), required=True)
    class Meta:
        model = WarehouseManagementMethod
        fields = ["name"]
        widgets = {
            'name': forms.Select(attrs={'class': 'form-control select'}),
        }

class ImportShipmentForm(ModelForm):
    
    class Meta:
        model = ImportShipment
        fields = ["import_shipment_code", "supplier_id", "date"]
        widgets = {
            'import_shipment_code': forms.TextInput(attrs={ 'class': 'form-control', 'required': True, 'placeholder': "Mã lô hàng nhập kho"}),
            'supplier_id': forms.Select(attrs={'class': 'form-control select', 'required': True}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': "date",'required': True, 'placeholder': "Ngày nhập kho lô hàng"}),
        }
        labels = {
            'import_shipment_code': "Mã lô hàng nhập kho",
            'supplier_id': "Chọn nhà cung cấp",
            'date': "Ngày nhập kho",
        }


class ImportPurchaseForm(ModelForm):

    class Meta:
        model = ImportPurchase
        fields = ["product_id", "quantity_import", "import_cost"]
        widgets = {
            'product_id': forms.Select(attrs={'class': 'form-control select', 'required': True}),
            'quantity_import': forms.NumberInput(attrs={'class': 'form-control', 'required': True, 'placeholder': "Số lượng nhập kho"}),
            'import_cost': forms.NumberInput(attrs={'class': 'form-control', 'required': True, 'placeholder': "Đơn giá nhập kho"})
        }
        labels = {
            'product_id': "Sản phẩm",
            'quantity_import': "Số lượng sản phẩm nhập kho",
            'import_cost': "Đơn giá nhập kho",
        }

class ExportShipmentForm(ModelForm):
    class Meta:
        model = ExportShipment
        fields = ['export_shipment_code', 'agency_id', 'date']
        widgets = {
            'export_shipment_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Mã lô hàng xuất kho"}),
            'agency_id': forms.Select(attrs={'class': 'form-control select',}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': "Ngày xuất kho lô hàng"}),
        }
        labels = {
            'export_shipment_code': "Mã lô hàng xuất kho",
            'agency_id': "Xuất kho cho đại lý",
            'date': "Ngày xuất kho",
        }

class ExportOrderForm(ModelForm):
    class Meta:
        model = ExportOrder
        fields = ["product_id", "quantity_export", "unit_price"]
        widgets = {
            'product_id': forms.Select(attrs={'class': 'form-control select',}),
            'quantity_export': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': "Số lượng xuất kho"}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': "Đơn giá bán"}),
        }
        labels = {
            'product_id': "Sản phẩm",
            'quantity_export': "Số lượng sản phẩm xuất kho",
            'unit_price': "Đơn giá bán",
        }

class ActualMethodStartingInventory(forms.Form):
    chosen_purchases = forms.ModelChoiceField(widget=forms.Select(attrs={'class': 'form-control select', 'required': True}),
                                              label="Danh sách đơn hàng tồn kho đầu kỳ")
    quantity_take = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 
                                                                       'placeholder': "Số lượng lấy ra từ đơn hàng được chọn",
                                                                       'required': True}),
                                                                label="Số lượng lấy ra từ đơn hàng được chọn")
    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        current_accounting_period_id = AccoutingPeriod.objects.aggregate(Max('id')).get("id__max", 0)
        accounting_periods_id = AccoutingPeriod.objects.exclude(pk=current_accounting_period_id).values_list('id', flat=True)
        import_shipments_id = ImportShipment.objects.filter(current_accounting_period__in=accounting_periods_id).values_list('id', flat=True)
        self.fields["chosen_purchases"].queryset = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(import_shipment_id__in=import_shipments_id)

