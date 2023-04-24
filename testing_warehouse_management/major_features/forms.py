from django import forms
from django.forms import ModelForm
from . models import *

class KeepMethodForm(forms.Form):
    is_keep = forms.BooleanField(widget=forms.CheckboxInput(attrs={}), label="Giữ phương pháp hiện tại", label_suffix=": ", required=False, initial=False)

class DatePickerForm(forms.Form):
    date_field = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

class WarehouseManagementMethodForm(ModelForm):
    name = forms.ModelChoiceField(queryset=WarehouseManagementMethod.objects.all())
    class Meta:
        model = WarehouseManagementMethod
        fields = ["name"]
        widgets = {
            'name': forms.Select(attrs={}),
        }