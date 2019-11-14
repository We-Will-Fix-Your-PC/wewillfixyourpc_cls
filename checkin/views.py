from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse
import django_keycloak_auth.users
from . import forms
from . import models
from django.contrib.auth.decorators import login_required, permission_required
import pyotp
import json


@login_required
@permission_required('customers.add_customer', raise_exception=True)
def totp(request):
    totp = pyotp.TOTP(settings.OTP_SECRET)
    return HttpResponse(totp.now())


@login_required
@permission_required('customers.view_customer', raise_exception=True)
def recent_customers(request):
    recent = models.Checkin.objects.order_by('-timestamp')[:5]
    return HttpResponse(json.dumps(list(
        map(
            lambda u: django_keycloak_auth.users.get_user_by_id(u.customer).user,
            recent
        )
    )), content_type="application/json")


def setup_required(f):
    def w(request, *args, **kwargs):
        if not request.session.get("is_checkin_setup"):
            return redirect('checkin:setup')

        return f(request, *args, **kwargs)
    return w


@setup_required
def done(request):
    return render(request, "checkin/done.html")


@setup_required
def index(request):
    if request.method == "POST":
        if request.POST.get("customer_id") and request.POST.get("confirm"):
            if request.POST["confirm"] == "yes":
                django_keycloak_auth.users.link_roles_to_user(request.POST["customer_id"], "customer")
                checkin = models.Checkin(customer=request.POST["customer_id"])
                checkin.save()
                return redirect('checkin:done')
            else:
                return redirect('checkin:details')

        form = forms.NameForm(request.POST)

        if form.is_valid():
            request.session["checkin_first_name"] = form.cleaned_data["first_name"]
            request.session["checkin_last_name"] = form.cleaned_data["last_name"]
            request.session.save()

            user = next(
                filter(
                    lambda u: u.user.get("firstName", "").strip().lower() == form.cleaned_data['first_name'].strip().lower()
                              and u.user.get("lastName", "").strip().lower() == form.cleaned_data['last_name'].strip().lower(),
                    django_keycloak_auth.users.get_users()
                ),
                None
            )
            if user:
                return render(request, "checkin/index.html", {
                    "customer": user.user
                })
            else:
                return redirect('checkin:details')
    else:
        form = forms.NameForm()

    return render(request, "checkin/index.html", {
        "form": form
    })


def create_user(request, phone=None, email=None):
    user = django_keycloak_auth.users.get_or_create_user(
        email=email,
        phone=phone,
        first_name=request.session.get("checkin_first_name"),
        last_name=request.session.get("checkin_first_name")
    )
    django_keycloak_auth.users.link_roles_to_user(user.get("id"), "customer")
    return user


@setup_required
def details(request):
    if request.method == "POST":
        if request.POST.get("customer_id") and request.POST.get("confirm"):
            if request.POST["confirm"] == "yes":
                django_keycloak_auth.users.link_roles_to_user(request.POST["customer_id"], "customer")
                checkin = models.Checkin(customer=request.POST["customer_id"])
                checkin.save()
            else:
                user = create_user(request, request.session.get("checkin_phone"), request.session.get("checkin_email"))
                checkin = models.Checkin(customer=user.get("id"))
                checkin.save()

            return redirect('checkin:done')

        form = forms.DetailsForm(request.POST)

        if form.is_valid():
            user = next(
                filter(
                    lambda u: (form.cleaned_data['email'] and u.user.get("email", "").strip().lower() == form.cleaned_data['email'].strip().lower())
                              or (form.cleaned_data['phone'] and form.cleaned_data['phone'] in u.user.get("attributes", {}).get("phone", [])),
                    django_keycloak_auth.users.get_users()
                ),
                None
            )
            if user:
                request.session["checkin_email"] = form.cleaned_data["phone"]
                request.session["checkin_phone"] = form.cleaned_data["email"]
                request.session.save()
                return render(request, "checkin/details.html", {
                    "customer": user.user
                })
            else:
                user = create_user(request, form.cleaned_data['phone'], form.cleaned_data['email'])
                checkin = models.Checkin(customer=user.get("id"))
                checkin.save()
                return redirect('checkin:done')
    else:
        form = forms.DetailsForm()

    return render(request, "checkin/details.html", {
        "form": form
    })


def setup(request):
    if request.method == "POST":
        form = forms.SetupForm(request.POST)

        if form.is_valid():
            totp = pyotp.TOTP(settings.OTP_SECRET)
            if totp.verify(form.cleaned_data['code']):
                request.session["is_checkin_setup"] = True
                request.session.save()
                return redirect('checkin:index')
    else:
        form = forms.SetupForm()

    return render(request, "checkin/setup.html", {
        "form": form
    })
