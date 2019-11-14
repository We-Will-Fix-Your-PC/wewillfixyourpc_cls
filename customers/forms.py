from django import forms
from django.forms import formset_factory
from phonenumber_field.formfields import PhoneNumberField
from . import models


class CustomerForm(forms.Form):
    first_name = forms.CharField(required=True, label="First name/name of business")
    last_name = forms.CharField(required=False)
    email = forms.CharField(required=False)
    enabled = forms.BooleanField(required=False, initial=True, label="Account enabled")
    address_line_1 = forms.CharField(required=False)
    address_line_2 = forms.CharField(required=False)
    address_line_3 = forms.CharField(required=False)
    city = forms.CharField(required=False)
    country = forms.CharField(initial="United Kingdom", required=False)
    postal_code = forms.CharField(required=False)


class CustomerPhoneForm(forms.Form):
    phone_number = PhoneNumberField(required=True)


class CredentialForm(forms.ModelForm):
    class Meta:
        model = models.Credential
        fields = ['name', 'username', 'password']


CustomerPhoneFormSet = formset_factory(CustomerPhoneForm, can_delete=True)
