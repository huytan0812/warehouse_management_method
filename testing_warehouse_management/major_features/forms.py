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

    # ImportShipment model
    import_shipments = forms.ModelChoiceField(queryset=ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').all(),
                                              widget=forms.Select(attrs={'class': 'form-control'}),
                                              required=False,
                                              label="Lô hàng tồn kho",
                                              )
    
    # ImportPurchase model
    quantity_remain_greater_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                   'placeholder': "SLCL đơn hàng lớn hơn",}),
                                                                                    required=False,
                                                                                    min_value=0,
                                                                                    label="Chọn SLCL lớn hơn: ",
                                                                                    error_messages = {
                                                                                        'min_value': "Giá trị này phải lớn hơn 0"
                                                                                    })
    
    quantity_remain_less_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                   'placeholder': "SLCL đơn hàng nhỏ hơn",}),
                                                                                    required=False,
                                                                                    min_value=0,       
                                                                                    label="Chọn SLCL nhỏ hơn: ",
                                                                                    error_messages = {
                                                                                        'min_value': "Giá trị này phải lớn hơn 0"
                                                                                    })
    
    import_cost_greater_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                  'placeholder': "Đơn giá nhập kho lớn hơn",}),
                                                                                    required=False,
                                                                                    min_value=0,     
                                                                                    label="Chọn đơn giá nhập kho lớn hơn",
                                                                                    error_messages = {
                                                                                        'min_value': "Giá trị này phải lớn hơn 0"
                                                                                    })
    
    import_cost_less_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                  'placeholder': "Đơn giá nhập kho nhỏ hơn",}),
                                                                                    required=False,
                                                                                    min_value=0,
                                                                                    label="Chọn đơn giá nhập kho nhỏ hơn: ",
                                                                                    error_messages = {
                                                                                        'min_value': "Giá trị này phải lớn hơn 0"
                                                                                    })
    
    def __init__(self, *args, **kwargs):
        self._product = kwargs.pop('product') if 'product' in kwargs else None
        self._type = kwargs.pop('type')
        super().__init__(*args, **kwargs)

        self.assigning_queryset()

    @property
    def product(self):
        return self._product
     
    @property
    def type(self):
        return self._type
    
    def assigning_queryset(self):
        current_accounting_period_obj = AccoutingPeriod.objects.latest('id')

        if self.type == "starting_inventory":
            import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').filter(
                date__lt = current_accounting_period_obj.date_applied
            )

        elif self.type == "current_accounting_period":
            import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').filter(
                current_accounting_period = current_accounting_period_obj
            )
        
        else:
            import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').all()

        if self.product != None:
            product_obj = Product.objects.get(name=self.product)
            import_shipments = import_shipments.filter(
                importpurchase_import_purchases_package__product_id = product_obj
            ).order_by('import_shipment_code').distinct('import_shipment_code')

        self.fields['import_shipments'].queryset = import_shipments

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

        # Filter section
        self._import_shipment_code = kwargs.pop("import_shipment_code") if "import_shipment_code" in kwargs else None
        self._quantity_remain_greater_than = kwargs.pop("quantity_remain_greater_than") if "quantity_remain_greater_than" in kwargs else None
        self._quantity_remain_less_than = kwargs.pop("quantity_remain_less_than") if "quantity_remain_less_than" in kwargs else None
        self._import_cost_greater_than = kwargs.pop("import_cost_greater_than") if "import_cost_greater_than" in kwargs else None
        self._import_cost_less_than = kwargs.pop("import_cost_less_than") if "import_cost_less_than" in kwargs else None

        # Export handling logic
        self._quantity_export_remain = kwargs.pop("quantity_export_remain") if "quantity_export_remain" in kwargs else None

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
    
    # Filter section
    @property
    def import_shipment_code(self):
        return self._import_shipment_code
    
    @property
    def quantity_remain_greater_than(self):
        return self._quantity_remain_greater_than
    
    @property
    def quantity_remain_less_than(self):
        return self._quantity_remain_less_than
    
    @property
    def import_cost_greater_than(self):
        return self._import_cost_greater_than
    
    @property
    def import_cost_less_than(self):
        return self._import_cost_less_than

    @property
    def quantity_export_remain(self):
        return self._quantity_export_remain

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

    def combine_quantity_remain_queryset(self, queryset, filter_greater_than, filter_less_than):
        combine_queryset = queryset

        if filter_less_than >= filter_greater_than:
            combine_queryset = combine_queryset.filter(Q(quantity_remain__gte=filter_greater_than), Q(quantity_remain__lte=filter_less_than))
        else:
            combine_queryset = combine_queryset.filter(Q(quantity_remain__gte=filter_greater_than) | Q(quantity_remain__lte=filter_less_than))

        return combine_queryset

    def combine_import_cost_queryset(self, queryset, filter_greater_than, filter_less_than):
        combine_queryset = queryset

        if filter_less_than > filter_greater_than:
            combine_queryset = combine_queryset.filter(Q(import_cost__gte=filter_greater_than), Q(import_cost__lte=filter_less_than))
        else:
            combine_queryset = combine_queryset.filter(Q(import_cost__gte=filter_greater_than) | Q(import_cost__lte=filter_less_than))

        return combine_queryset

    def filter_queryset_by_factors(self, import_purchases):
        queryset = import_purchases

        if self.import_shipment_code:
            try:
                import_shipment_obj = ImportShipment.objects.get(pk=int(self.import_shipment_code))
            except ImportShipment.DoesNotExist:
                raise Exception("Invalid Import Shipment")
            queryset = queryset.filter(import_shipment_id=import_shipment_obj)

        if self.quantity_remain_greater_than and self.quantity_remain_less_than:
            queryset = self.combine_quantity_remain_queryset(queryset, self.quantity_remain_greater_than, self.quantity_remain_less_than)
        elif self.quantity_remain_greater_than:
            queryset = queryset.filter(quantity_remain__gte=self.quantity_remain_greater_than)
        elif self.quantity_remain_less_than:
            queryset = queryset.filter(quantity_remain__lte=self.quantity_remain_less_than)
        else:
            pass

        if self.import_cost_greater_than and self.import_cost_less_than:
            queryset = self.combine_import_cost_queryset(queryset, self.import_cost_greater_than, self.import_cost_less_than)
        elif self.import_cost_greater_than:
            queryset = queryset.filter(import_cost__gte=self.import_cost_greater_than)
        elif self.import_cost_less_than:
            queryset = queryset.filter(import_cost__lte=self.import_cost_less_than)
        else:
            pass

        return queryset

    def assigning_queryset(self):

        product_obj = Product.objects.get(name=self.product)
        current_accounting_period_obj = AccoutingPeriod.objects.latest('id')

        if self.type == "starting_inventory":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__date__lt=current_accounting_period_obj.date_applied,
                product_id=product_obj,
                quantity_remain__gt=0
            ).order_by('-import_shipment_id__date')

        elif self.type == "current_accounting_period":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__current_accounting_period=current_accounting_period_obj,
                product_id=product_obj,
                quantity_remain__gt=0
            ).order_by('import_shipment_id__date')

        else:
            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').all()

        import_purchases = self.filter_queryset_by_factors(import_purchases)

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
                    gettext_lazy("""Số lượng lấy ra lớn hơn SLCL của đơn hàng nhập kho:
                                 %(quantity_take)s > %(quantity_remain)s 
                                 """),
                    params = {'quantity_take': quantity_take,
                              'quantity_remain': purchase_obj.quantity_remain}
                )
            elif self.quantity_export_remain:
                if quantity_take > self.quantity_export_remain:
                    raise ValidationError(
                        gettext_lazy("Số lượng lấy ra lớn hơn số lượng xuất kho còn lại đơn hàng xuất kho")
                    )
            else:
                pass

        return quantity_take
        



