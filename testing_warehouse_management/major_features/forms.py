from django import forms
from django.forms import ModelForm
from . models import *

class KeepMethodForm(forms.Form):
    CHOICES = [
        ("1", "Có"),
        ("2", "Không")
    ]

    current_method = WarehouseManagementMethod.objects.filter(is_currently_applied=True)[0]

    is_keep = forms.ChoiceField(widget=forms.RadioSelect(attrs={}), choices=CHOICES, 
                                label=f"Bạn có muốn giữ phương pháp hiện tại: {current_method.name} không?")
    
    # def clean_is_keep(self):
    #     data = self.cleaned_data["is_keep"]
    #     if data == "1":
    #         if self.fields["is_keep"]

class DatePickerForm(forms.Form):
    date_field = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

class WarehouseManagementMethodForm(ModelForm):
    name = forms.ModelChoiceField(queryset=WarehouseManagementMethod.objects.all(), required=True)
    class Meta:
        model = WarehouseManagementMethod
        fields = ["name"]
        widgets = {
            'name': forms.Select(attrs={}),
        }