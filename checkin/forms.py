from django import forms
from phonenumber_field.formfields import PhoneNumberField


class SetupForm(forms.Form):
    code = forms.CharField(max_length=6, required=True, label="Setup code")


class NameForm(forms.Form):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)


class DetailsForm(forms.Form):
    email = forms.EmailField(required=False)
    phone = PhoneNumberField(required=False)
