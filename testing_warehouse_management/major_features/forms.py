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

    def clean_quantity_export(self):
        quantity_export = self.cleaned_data["quantity_export"]
        if 'product_id' in self.cleaned_data:
            product = self.cleaned_data["product_id"]
            product_import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                product_id = product
            )
            product_quantity_remain_summarizing = product_import_purchases.aggregate(
                total_quantity_remain = Sum("quantity_remain")
            )
            product_quantity_remain = product_quantity_remain_summarizing["total_quantity_remain"]
            if product_quantity_remain is None:
                product_quantity_remain = 0
            
            if product_quantity_remain < quantity_export:
                raise ValidationError(
                    gettext_lazy("SLCL của sản phẩm %(product)s nhỏ hơn SL xuất kho của đơn hàng"),
                    params = {'product': product}
                )
            
        return quantity_export
        
            
        

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
                                                                                    label="Chọn SLCL lớn hơn",
                                                                                    error_messages = {
                                                                                        'min_value': "Giá trị này phải lớn hơn 0"
                                                                                    })
    
    quantity_remain_less_than = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                                   'placeholder': "SLCL đơn hàng nhỏ hơn",}),
                                                                                    required=False,
                                                                                    min_value=0,       
                                                                                    label="Chọn SLCL nhỏ hơn",
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
                                                                                    label="Chọn đơn giá nhập kho nhỏ hơn",
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
                date__lt = current_accounting_period_obj.date_applied,
                total_shipment_value__gt=0
            )

        elif self.type == "current_accounting_period":
            import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').filter(
                current_accounting_period = current_accounting_period_obj,
                total_shipment_value__gt=0
            )
        
        else:
            import_shipments = ImportShipment.objects.select_related('supplier_id', 'current_accounting_period').filter(
                total_shipment_value__gt=0
            )

        if self.product != None:
            product_obj = Product.objects.get(name=self.product)
            import_shipments = import_shipments.filter(
                importpurchase_import_purchases_package__product_id = product_obj,
                importpurchase_import_purchases_package__quantity_remain__gt = 0
            ).order_by('pk').distinct('pk')

        self.fields['import_shipments'].queryset = import_shipments

class ActualMethodInventory(forms.Form):
    chosen_purchases = forms.ModelChoiceField(queryset=ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                                                import_shipment_id__total_shipment_value__gt=0
                                            ),
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

    # This function can only access after validating form successfully
    def get_purchase(self):
        purchase = self.cleaned_data['chosen_purchases']
        return purchase
    
    # This function can only access after validating form successfully
    def get_quantity_take(self):
        quantity_take = self.cleaned_data['quantity_take']
        return quantity_take
    
    # This function can only access after validating form successfully
    def get_import_cost(self):
        purchase = self.get_purchase()
        return purchase.import_cost

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
                import_shipment_id__total_shipment_value__gt=0,
                product_id=product_obj,
                quantity_remain__gt=0
            ).order_by('-import_shipment_id__date')

        elif self.type == "current_accounting_period":

            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__current_accounting_period=current_accounting_period_obj,
                import_shipment_id__total_shipment_value__gt=0,
                product_id=product_obj,
                quantity_remain__gt=0
            ).order_by('import_shipment_id__date')

        else:
            import_purchases = ImportPurchase.objects.select_related('import_shipment_id', 'product_id').filter(
                import_shipment_id__total_shipment_value__gt=0
            )

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
        
class AddProductForm(ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "minimum_quantity", "category_name"]
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': "Mã sản phẩm"}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': "Tên sản phẩm"}),
            'minimum_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': "SL tồn kho tối thiểu"}),
            'category_name': forms.Select(attrs={'class': 'form-control select', 'required': False})
        }
        labels = {
            'sku': "Mã sản phẩm",
            'name': "Tên sản phẩm",
            'minimum_quantity': "Số lượng tồn kho tối thiểu",
            'category_name': "Danh mục sản phẩm"
        }

class EditProductForm(ModelForm):
    class Meta:
        model = Product
        fields = ["name", "minimum_quantity", "category_name"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Tên sản phẩm"}),
            'minimum_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': "SL tồn kho tối thiểu"}),
            'category_name': forms.Select(attrs={'class': 'form-control select', 'required': False})
        }
        labels = {
            'name': "Tên sản phẩm",
            'minimum_quantity': "Số lượng tồn kho tối thiểu",
            'category_name': "Danh mục sản phẩm"
        }

class AddCategoryForm(ModelForm):
    class Meta:
        model = Category
        fields = ["name", "parent"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': "Tên danh mục"}),
            'parent': forms.Select(attrs={'class': 'form-control select'})
        }
        labels = {
            'name': "Tên danh mục",
            'parent': "Danh mục gốc"
        }


class EditUserInfoForm(ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Họ", 'required': False}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Tên", 'required': False}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': "Email", 'required': False}),
            'is_active': forms.CheckboxInput(attrs={'required': False})
        }
        labels = {
            'first_name': "Họ",
            'last_name': "Tên",
            'email': "Email"
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.instance = None

        if "instance" in kwargs:
            self.instance = kwargs["instance"]

        active_state = False
        if self.instance:
            active_state = self.check_admin_state(self.instance)

        if active_state == True:
            self.fields["is_active"].label = "Hủy kích hoạt"
        else:
            self.fields["is_active"].label = "Kích hoạt"

    def check_admin_state(self, instance):
        if instance.is_active == True:
            return True
        return False