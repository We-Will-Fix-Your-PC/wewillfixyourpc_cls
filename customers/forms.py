from django import forms
from django.forms import formset_factory
from phonenumber_field.formfields import PhoneNumberField


class CustomerForm(forms.Form):
    first_name = forms.CharField(required=True, label="First name/name of business")
    last_name = forms.CharField(required=False)
    email = forms.CharField(required=False)
    address_line_1 = forms.CharField(required=False)
    address_line_2 = forms.CharField(required=False)
    address_line_3 = forms.CharField(required=False)
    city = forms.CharField(required=False)
    country = forms.CharField(initial="United Kingdom", required=False)
    postal_code = forms.CharField(required=False)
    # class Meta:
    #     model = models.Customer
    #     fields = [
    #         'first_name', 'last_name', 'email', 'address_line_1', 'address_line_2', 'city',
    #         'country', 'postal_code'
    #     ]


class CustomerPhoneForm(forms.Form):
    phone_number = PhoneNumberField(required=True)


CustomerPhoneFormSet = formset_factory(CustomerPhoneForm, can_delete=True)
