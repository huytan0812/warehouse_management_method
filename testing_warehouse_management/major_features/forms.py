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

class FilteringInventory(forms.Form):
    import_shipments = forms.ModelChoiceField(queryset=ImportShipment.objects.select_related('supplier_id').all(),
                                              widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
                                              label="Lô hàng tồn kho")
    quantity_remain_greater_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                   'placeholder': "SLCL đơn hàng lớn hơn",
                                                                                   'min': 0}),
                                                                            label="Chọn SLCL lớn hơn: ")
    quantity_remain_less_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                   'placeholder': "SLCL đơn hàng nhỏ hơn",
                                                                                   'min': 0}),
                                                                            label="Chọn SLCL nhỏ hơn: ")
    import_cost_greater_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                  'placeholder': "Đơn giá nhập kho lớn hơn",
                                                                                  'min': 0}),
                                                                            label="Chọn đơn giá nhập kho lớn hơn")
    import_cost_less_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                  'placeholder': "Đơn giá nhập kho nhỏ hơn",
                                                                                  'min': 0}),
                                                                            label="Chọn đơn giá nhập kho nhỏ hơn: ")
    
    def clean_quantity_remain_greater_than(self):
        quantity_remain = self.cleaned_data['quantity_remain_greater_than']
        if quantity_remain < 0:
            raise ValidationError(gettext_lazy("Số lượng còn lại phải lớn hơn 0"))
        return quantity_remain

    def clean_quantity_remain_less_than(self):
        quantity_remain = self.cleaned_data['quantity_remain_less_than']
        if quantity_remain < 0:
            raise ValidationError(gettext_lazy("Số lượng còn lại phải lớn hơn 0"))
        return quantity_remain

    def clean_import_cost_greater_than(self):
        import_cost = self.cleaned_data['import_cost_greater_than']
        if import_cost < 0:
            raise ValidationError(gettext_lazy("Đơn giá nhập kho phải lớn hơn 0"))
        return import_cost

    def clean_import_cost_less_than(self):
        import_cost = self.cleaned_data['import_cost_less_than']
        if import_cost < 0:
            raise ValidationError(gettext_lazy("Đơn giá nhập kho phải lớn hơn 0"))
        return import_cost  

class ActualMethodInventory(forms.Form):
    chosen_purchases = forms.ModelChoiceField(queryset=ImportPurchase.objects.select_related('import_shipment_id', 'product_id').all(),
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

        self.assigning_queryset()

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

    def get_purchase(self):
        purchase = self.cleaned_data['chosen_purchases']
        return purchase
    
    def get_quantity_take(self):
        quantity_take = self.cleaned_data['quantity_take']
        return quantity_take

    def assigning_queryset(self):

        product_obj = Product.objects.get(name=self.product)
        current_accounting_period_obj = AccoutingPeriod.objects.latest('id')

        if self.type == "starting_inventory":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__date__lt=current_accounting_period_obj.date_applied,
                product_id=product_obj,
                quantity_remain__gt=0
            ).order_by('-import_shipment_id__date')

            self.fields["chosen_purchases"].queryset = import_purchases

            import_purchases_count = import_purchases.count()
            self.len_queryset = import_purchases_count

        if self.type == "current_accounting_period":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__current_accounting_period=current_accounting_period_obj,
                product_id=product_obj,
                quantity_remain__gt=0
            ).order_by('import_shipment_id__date')

            self.fields["chosen_purchases"].queryset = import_purchases

            import_purchases_count = import_purchases.count()
            self.len_queryset = import_purchases_count

    def clean_quantity_take(self):
        quantity_take = self.cleaned_data['quantity_take']

        if 'chosen_purchases' in self.cleaned_data:
            chosen_purchase = self.cleaned_data['chosen_purchases']
            purchase_obj = chosen_purchase

            if quantity_take > purchase_obj.quantity_remain:
                raise ValidationError(
                    gettext_lazy("""Quantity take is greater than import purchase's quantity remain:
                                 %(quantity_take)s > %(quantity_remain)s 
                                 """),
                    params = {'quantity_take': quantity_take,
                              'quantity_remain': purchase_obj.quantity_remain}
                )

        return quantity_take
        



