from django import forms
from django.forms import ModelForm
from . models import *

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