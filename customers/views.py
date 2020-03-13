from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
import django_keycloak_auth.users
import django_keycloak_auth.clients
import tickets.models
from . import forms
from . import models
from . import tasks
import twilio.rest
import json
import requests
import keycloak.exceptions
import urllib.parse
import tickets.models
import secrets


twilio_client = twilio.rest.Client(settings.TWILIO_ACCOUNT, settings.TWILIO_TOKEN)


def get_customers():
    client = django_keycloak_auth.clients.get_keycloak_admin_client()

    users = []
    first = 0
    inc = 500
    while True:
        new_users = client._client.get(
                    url=client._client.get_full_url(
                        'auth/admin/realms/{realm}/roles/{role_name}/users?first={first}&max={max}'
                            .format(realm=client._name, role_name="customer", first=first, max=inc)
                    )
                )
        users.extend(new_users)
        if len(new_users) < inc:
            break
        first += inc

    return list(
            map(
                lambda u: tasks.get_user(u.get("id")),
                users
            )
        )


@login_required
@permission_required('customers.view_customer', raise_exception=True)
def view_customers(request):
    customers = sorted(
        get_customers(),
        key=lambda c: f"{c.get('firstName')} {c.get('lastName')}"
    )
    return render(request, "customer/customers.html", {
        "customers": customers
    })


@login_required
@permission_required('customers.view_customer', raise_exception=True)
def view_customer(request, customer_id):
    try:
        user = django_keycloak_auth.users.get_user_by_id(customer_id).get()
    except keycloak.exceptions.KeycloakClientError:
        raise Http404()
    models.CustomerCache(cust_id=customer_id, data=json.dumps(user)).save()
    address = user.get("attributes", {}).get("address", [])
    address = address[0] if len(address) else None
    credentials = models.Credential.objects.filter(customer=customer_id) \
        if request.user.has_perm("customers.view_credential") else []
    cust_tickets = tickets.models.Ticket.objects.filter(customer=customer_id) \
        if request.user.has_perm("tickets.view_ticket") else []
    return render(request, "customer/customer.html", {
        "customer": user,
        "address": json.loads(address) if address else None,
        "credentials": credentials,
        "tickets": cust_tickets
    })


def transform_customer_form(form, phone_numbers):
    args = {
        "first_name": form.cleaned_data["first_name"],
        "last_name": form.cleaned_data["last_name"],
        "email": form.cleaned_data["email"],
        "enabled": form.cleaned_data["enabled"],
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
@permission_required('customers.change_customer', raise_exception=True)
def edit_customer(request, customer_id):
    if request.method == 'POST':
        form = forms.CustomerForm(request.POST, prefix="primary")
        phone_numbers = forms.CustomerPhoneFormSet(request.POST)
        phone_numbers.clean()
        if form.is_valid() and phone_numbers.is_valid():
            django_keycloak_auth.users.update_user(customer_id, force_update=True, **transform_customer_form(form, phone_numbers))
            models.CustomerCache.objects.filter(cust_id=customer_id).delete()

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
                "enabled": user.get("enabled"),
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
        "title": "Edit customer"
    })


@login_required
@permission_required('customers.add_customer', raise_exception=True)
def new_customer(request):
    msg = None
    if request.method == 'POST':
        form = forms.CustomerForm(request.POST, prefix="primary")
        phone_numbers = forms.CustomerPhoneFormSet(request.POST)
        phone_numbers.clean()
        if form.is_valid() and phone_numbers.is_valid():
            try:
                user = django_keycloak_auth.users.get_or_create_user(
                    required_actions=["UPDATE_PROFILE", "UPDATE_PASSWORD"],
                    **transform_customer_form(form, phone_numbers)
                )
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 409:
                    msg = "Customer already exists"
            else:
                models.CustomerCache(cust_id=user.get("id"), data=json.dumps(user)).save()
                django_keycloak_auth.users.link_roles_to_user(user.get("id"), ["customer"])

                numbers = list(
                    map(
                        lambda p: p["phone_number"].as_e164,
                        filter(
                            lambda p: p.get("phone_number"),
                            phone_numbers.cleaned_data
                        )
                    )
                )

                def send_message(num, body):
                    requests.post(f"{settings.VSMS_URL}message/new/",  headers={
                        "Authorization": f"Bearer {django_keycloak_auth.clients.get_access_token()}"
                    }, json={
                        "to": num,
                        "contents": body
                    })
                    # twilio_client.messages.create(
                    #     to=num,
                    #     messaging_service_sid=settings.TWILIO_MSID,
                    #     body=body
                    # )

                if form.cleaned_data["email"] and len(numbers):
                    for num in numbers:
                        send_message(
                            num,
                            f"Welcome to your We Will Fix Your PC account. Your username is "
                            f"{user.get('username')}, and details to setup your account have been"
                            f"emailed to you. Login to see your repairs at https://wwfypc.xyz/cls",
                        )
                elif len(numbers):
                    password = secrets.token_hex(4)
                    django_keycloak_auth.users.get_user_by_id(user.get("id")).reset_password(password, temporary=True)
                    for num in numbers:
                        send_message(
                            num,
                            f"Welcome to your We Will Fix Your PC account. Your username is "
                            f"{user.get('username')}, and your temporary password is "
                            f"{password}. Login to see your repairs at https://wwfypc.xyz/cls",
                        )

                if not request.GET.get("next"):
                    return redirect("customers:view_customers")
                else:
                    response = redirect(request.GET["next"])
                    response["Location"] += "?" + urllib.parse.urlencode({
                        "customer_id": user.get("id")
                    })
                    return response
    else:
        name = request.GET.get("customer_name", "").split(" ")

        form = forms.CustomerForm(prefix="primary", initial={
            "first_name": name[0],
            "last_name": " ".join(name[1:])
        })
        phone_numbers = forms.CustomerPhoneFormSet()

    return render(request, "customer/customer_form.html", {
        "form": form,
        "phone_numbers": phone_numbers,
        "title": "New customer",
        "msg": msg
    })


@login_required
@permission_required('customers.change_credential', raise_exception=True)
def edit_credential(request, credential_id):
    credential = get_object_or_404(models.Credential, id=credential_id)

    if request.method == 'POST':
        form = forms.CredentialForm(request.POST, instance=credential)
        if form.is_valid():
            form.save()
            return redirect("customers:view_customer", credential.customer)
    else:
        form = forms.CredentialForm(instance=credential)

    return render(request, "customer/credential_form.html", {
        "form": form,
        "title": "Edit credential"
    })


@login_required
@permission_required('customers.add_credential', raise_exception=True)
def new_credential(request, customer_id):
    credential = models.Credential(customer=customer_id)

    if request.method == 'POST':
        form = forms.CredentialForm(request.POST, instance=credential)
        if form.is_valid():
            form.save()
            return redirect("customers:view_customer", credential.customer)
    else:
        form = forms.CredentialForm(instance=credential)

    return render(request, "customer/credential_form.html", {
        "form": form,
        "title": "New credential"
    })
