from django import forms
from django.forms import ModelForm
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
            'name': forms.Select(attrs={}),
        }

class ImportShipmentForm(ModelForm):
    
    class Meta:
        model = ImportShipment
        fields = ["import_shipment_code", "supplier_id", "date"]
        widgets = {
            'import_shipment_code': forms.TextInput(attrs={}),
            'supplier_id': forms.Select(attrs={}),
            'date': forms.DateInput(attrs={'type': "date"}),
        }
        labels = {
            'import_shipment_code': "Mã lô hàng nhập kho",
            'supplier_id': "Chọn nhà cung cấp",
            'date': "Ngày",
        }


class ImportPurchaseForm(ModelForm):

    class Meta:
        model = ImportPurchase
        fields = ["product_id", "quantity_import", "import_cost"]
        widgets = {
            'product_id': forms.Select(attrs={}),
            'quantity_import': forms.NumberInput(attrs={}),
            'import_cost': forms.NumberInput(attrs={})
        }
        labels = {
            'product_id': "",
            'quantity_import': "",
            'import_cost': "",
        }