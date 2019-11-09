from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib.auth.decorators import login_required
import django_keycloak_auth.users
from . import forms
import json
import keycloak


@login_required
def view_customers(request):
    customers = list(
        map(
            lambda u: u.user,
            filter(
                lambda u: next(filter(
                    lambda r: r.get('name') == 'customer', u.role_mappings.realm.get()
                ), False),
                django_keycloak_auth.users.get_users()
            )
        )
    )
    return render(request, "customer/customers.html", {
        "customers": customers
    })


@login_required
def view_customer(request, customer_id):
    try:
        user = django_keycloak_auth.users.get_user_by_id(customer_id).get()
    except keycloak.exceptions.KeycloakClientError:
        raise Http404()
    return render(request, "customer/customer.html", {
        "customer": user
    })


def transform_customer_form(form, phone_numbers):
    args = {
        "first_name": form.cleaned_data["first_name"],
        "last_name": form.cleaned_data["last_name"],
        "email": form.cleaned_data["email"],
        "phone": list(
            map(
                lambda p: p["phone_number"].as_e164,
                filter(
                    lambda p: p.get("phone_number"),
                    phone_numbers.cleaned_data
                )
            )
        )
    }

    if form.cleaned_data["address_line_1"]:
        args["address"] = json.dumps({
            "line_1": form.cleaned_data["address_line_1"],
            "line_2": form.cleaned_data["address_line_2"],
            "line_3": form.cleaned_data["address_line_3"],
            "city": form.cleaned_data["city"],
            "country": form.cleaned_data["country"],
            "postal_code": form.cleaned_data["postal_code"],
        })

    return args


@login_required
def edit_customer(request, customer_id):
    if request.method == 'POST':
        form = forms.CustomerForm(request.POST, prefix="primary")
        phone_numbers = forms.CustomerPhoneFormSet(request.POST)
        if form.is_valid() and phone_numbers.is_valid():
            django_keycloak_auth.users.update_user(customer_id, force_update=True, **transform_customer_form(form, phone_numbers))

            return redirect("customers:view_customers")
    else:
        try:
            user = django_keycloak_auth.users.get_user_by_id(customer_id).get()
        except keycloak.exceptions.KeycloakClientError:
            raise Http404()

        address = user.get("attributes", {}).get("address", [])
        address = json.loads(address[0]) if len(address) else {}
        phone_numbers = user.get("attributes", {}).get("phone", [])

        form = forms.CustomerForm(
            prefix="primary",
            initial={
                "first_name": user.get("firstName"),
                "last_name": user.get("lastName"),
                "email": user.get("email"),
                "address_line_1": address.get("line_1"),
                "address_line_2": address.get("line_2"),
                "address_line_3": address.get("line_3"),
                "city": address.get("city"),
                "country": address.get("country"),
                "postal_code": address.get("postal_code"),
            }
        )
        phone_numbers = forms.CustomerPhoneFormSet(
            initial=list(map(lambda p: {
                "phone_number": p
            }, phone_numbers))
        )

    return render(request, "customer/customer_form.html", {
        "form": form,
        "phone_numbers": phone_numbers,
        "title": "New Customer"
    })


@login_required
def new_customer(request):
    if request.method == 'POST':
        form = forms.CustomerForm(request.POST, prefix="primary")
        phone_numbers = forms.CustomerPhoneFormSet(request.POST)
        if form.is_valid() and phone_numbers.is_valid():
            user = django_keycloak_auth.users.get_or_create_user(**transform_customer_form(form, phone_numbers))
            django_keycloak_auth.users.link_roles_to_user(user.get("id"), ["customer"])

            return redirect("customers:view_customers")
    else:
        form = forms.CustomerForm(prefix="primary")
        phone_numbers = forms.CustomerPhoneFormSet()

    return render(request, "customer/customer_form.html", {
        "form": form,
        "phone_numbers": phone_numbers,
        "title": "New Customer"
    })
