from django import forms
from django.forms import ModelForm
from django.db.models import Sum, Max
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy
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

class ActualMethodInventory(forms.Form):
    chosen_purchases = forms.ModelChoiceField(queryset=None,
                                              widget=forms.Select(attrs={'class': 'form-control select', 'required': True}),
                                              label="Danh sách đơn hàng tồn kho đầu kỳ")
    quantity_take = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 
                                                                       'placeholder': "Số lượng lấy ra từ đơn hàng được chọn",
                                                                       'required': True}),
                                                                label="Số lượng lấy ra từ đơn hàng được chọn")
    
    def __init__(self, *args, **kwargs):

        self._product = kwargs.pop("product")
        self._type = kwargs.pop("type")
        self._len_queryset = 0
        super().__init__(*args, **kwargs)

    @property
    def product(self):
        return self._product
    
    @property
    def type(self):
        return self._type
    
    @property
    def len_queryset(self):
        return self._len_queryset
    
    @len_queryset.setter
    def len_queryset(self, new_length):
        self._len_queryset = new_length
        print("New length of queryset is: ", self.len_queryset)


    def assigning_queryset(self):

        product_obj = Product.objects.get(name=self.product)
        current_accounting_period_obj = AccoutingPeriod.objects.latest('id')

        if self.type == "starting_inventory":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__date__lt=current_accounting_period_obj.date_applied,
                product_id=product_obj,
                quantity_remain__gt=0
            )
            self.fields["chosen_purchases"].queryset = import_purchases
            import_purchases_count = import_purchases.count()

            self.len_queryset = import_purchases_count

        if self.type == "current_accounting_period":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__current_accounting_period=current_accounting_period_obj,
                product_id=product_obj,
                quantity_remain__gt=0
            )
            self.fields["chosen_purchases"].queryset = import_purchases
            import_purchases_count = import_purchases.count()

            self.len_queryset = import_purchases_count

    def clean_chosen_purchases(self):
        # Validating the chosen purchase
        # must be in the chosen_purchases queryset
        chosen_purchase = self.cleaned_data["chosen_purchases"]
        chosen_purchases_queryset = self.fields["chosen_purchases"].queryset

        if chosen_purchase not in chosen_purchases_queryset:
            raise ValidationError(gettext_lazy(f"This purchase is not in the {self.type}"))
        
        return chosen_purchase

    def clean_quantity_take(self):
        # Validating the quantity take field's value
        # must less or equal than
        # the chosen purchase's quantity_remain value
        pass



