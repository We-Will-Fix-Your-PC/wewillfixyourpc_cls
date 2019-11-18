import json
import socket
import urllib.parse

import django_keycloak_auth.users
from brotherprint.brotherprint import BrotherPrint
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings

from . import forms, models


def print_labels(tid: str, name: str, extra: str, num=1):
    if settings.LABEL_PRINTER_IP:
        f_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        f_socket.connect((settings.LABEL_PRINTER_IP, 9100))
        printjob = BrotherPrint(f_socket)

        printjob.template_mode()

        for i in range(num):
            printjob.template_init()
            printjob.choose_template(0)
            printjob.select_and_insert('field-1', tid)
            printjob.select_and_insert('field-2', name)
            printjob.select_and_insert('field-3', extra)
            printjob.template_print()

        f_socket.close()


@login_required
@permission_required('tickets.view_ticket', raise_exception=True)
def view_tickets(request):
    if request.method == "POST" and request.user.has_perm('tickets.change_ticket'):
        selected_tickets = list(
            map(
                lambda k: get_object_or_404(models.Ticket, id=k[len("select-ticket-"):]),
                filter(
                    lambda k: k.startswith("select-ticket-"),
                    request.POST.keys()
                )
            )
        )
        if request.POST.get("set") is not None:
            status = get_object_or_404(models.Status, name=request.POST.get("set"))
            for ticket in selected_tickets:
                ticket.status = status
                ticket.save()

    today_tickets = models.Ticket.objects.filter(to_do_by__gte=timezone.now().date())
    not_today_tickets = models.Ticket.objects.filter(Q(to_do_by__lt=timezone.now().date()) | Q(to_do_by__isnull=True))
    rebuild_tickets = not_today_tickets.filter(location__name="Rebuild")
    awaiting_customer_decision_tickets = not_today_tickets.filter(location__name="Awaiting Customer Decision")
    awaiting_parts_tickets = not_today_tickets.filter(location__name="Awaiting Parts")
    looking_for_parts_tickets = not_today_tickets.filter(location__name="Looking for Parts")
    completed_tickets = not_today_tickets.filter(location__name="Completed")
    normal_tickets = not_today_tickets.filter(
        ~Q(location__name="Rebuild"), ~Q(location__name="Awaiting Customer Decision"),
        ~Q(location__name="Awaiting Parts"), ~Q(location__name="Looking for Parts"),
        ~Q(location__name="Completed"),
    )
    return render(request, 'tickets/tickets.html', {
        "today_tickets": today_tickets,
        "normal_tickets": normal_tickets,
        "rebuild_tickets": rebuild_tickets,
        "awaiting_customer_decision_tickets": awaiting_customer_decision_tickets,
        "awaiting_parts_tickets": awaiting_parts_tickets,
        "looking_for_parts_tickets": looking_for_parts_tickets,
        "completed_tickets": completed_tickets
    })


@login_required
@permission_required('tickets.add_ticket', raise_exception=True)
def new_ticket(request):
    if request.method == "POST":
        customer_id = request.POST.get("customer_id")
        if customer_id:
            return redirect("tickets:new_step2", customer_id)
        response = redirect("customers:new")
        response["Location"] += "?" + urllib.parse.urlencode({
            "customer_name": request.POST.get("name"),
            "next": request.get_full_path()
        })
        return response
    else:
        if request.GET.get("customer_id"):
            return redirect("tickets:new_step2", request.GET["customer_id"])

    return render(request, "tickets/new_ticket.html")


@login_required
@permission_required('customers.view_customer', raise_exception=True)
def search_customer(request):
    if not request.method == "POST":
        return HttpResponseNotAllowed(permitted_methods=["POST"])

    query = request.POST.get("name").lower().strip()
    customers = list(
        filter(
            lambda u: query in u.get("firstName").lower().strip() or query in u.get("lastName").lower().strip(),
            map(
                lambda u: u.user,
                django_keycloak_auth.users.get_users()
            )
        )
    )
    return HttpResponse(json.dumps(customers))


@login_required
@permission_required('tickets.add_ticket', raise_exception=True)
def new_ticket_step2(request, customer_id):
    ticket = models.Ticket(customer=customer_id)
    if request.method == 'POST':
        form = forms.TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()

            customer = django_keycloak_auth.users.get_user_by_id(customer_id).user
            extra = ",".join(customer.get("attributes", {}).get("phone", []))
            num = 1 + form.cleaned_data["additional_labels"]
            if form.cleaned_data["has_charger"]:
                num += 1
            if form.cleaned_data["has_case"]:
                num += 1
            print_labels(form.instance.id, f'{customer.get("firstName")} {customer.get("lastName")}', extra, num)

            return redirect("tickets:view_tickets")
    else:
        form = forms.TicketForm(instance=ticket)

    return render(request, "tickets/ticket_form.html", {
        "form": form,
        "title": "New ticket"
    })


@login_required
@permission_required('tickets.change_ticket', raise_exception=True)
def edit_ticket(request, ticket_id):
    ticket = get_object_or_404(models.Ticket, id=ticket_id)
    if request.method == 'POST':
        form = forms.TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()

            num = form.cleaned_data["additional_labels"]
            if num:
                customer = django_keycloak_auth.users.get_user_by_id(ticket.customer).user
                extra = ",".join(customer.get("attributes", {}).get("phone", []))
                print_labels(form.instance.id, f'{customer.get("firstName")} {customer.get("lastName")}', extra, num)

            return redirect("tickets:view_tickets")
    else:
        form = forms.TicketForm(instance=ticket)

    return render(request, "tickets/ticket_form.html", {
        "form": form,
        "title": "Edit ticket"
    })


@login_required
def view_ticket(request, ticket_id):
    ticket = get_object_or_404(models.Ticket, id=ticket_id)
    if not (request.user.has_perm("tickets.view_tickets") or str(ticket.customer) == request.user.username):
        raise PermissionError()

    return render(request, "tickets/ticket.html", {
        "ticket": ticket
    })


@login_required
@permission_required('tickets.change_equipmenttype', raise_exception=True)
@permission_required('tickets.add_equipmenttype', raise_exception=True)
@permission_required('tickets.delete_equipmenttype', raise_exception=True)
@permission_required('tickets.view_equipmenttype', raise_exception=True)
@permission_required('tickets.change_ostype', raise_exception=True)
@permission_required('tickets.add_ostype', raise_exception=True)
@permission_required('tickets.delete_ostype', raise_exception=True)
@permission_required('tickets.view_ostype', raise_exception=True)
@permission_required('tickets.change_location', raise_exception=True)
@permission_required('tickets.add_location', raise_exception=True)
@permission_required('tickets.delete_location', raise_exception=True)
@permission_required('tickets.view_location', raise_exception=True)
@permission_required('tickets.change_status', raise_exception=True)
@permission_required('tickets.add_status', raise_exception=True)
@permission_required('tickets.delete_status', raise_exception=True)
@permission_required('tickets.view_status', raise_exception=True)
def ticket_settings(request):
    if request.method == 'POST':
        equipment_types = forms.EquipmentTypeFormSet(request.POST, prefix='equipment_type')
        statuses = forms.StatusFormSet(request.POST, prefix='status')
        locations = forms.LocationFormSet(request.POST, prefix='location')
        os_types = forms.OSTypeFormSet(request.POST, prefix='os_type')

        if equipment_types.is_valid() and statuses.is_valid() and locations.is_valid() and os_types.is_valid():
            equipment_types.save()
            statuses.save()
            locations.save()
            os_types.save()

            equipment_types = forms.EquipmentTypeFormSet(prefix='equipment_type')
            statuses = forms.StatusFormSet(prefix='status')
            locations = forms.LocationFormSet(prefix='location')
            os_types = forms.OSTypeFormSet(prefix='os_type')
    else:
        equipment_types = forms.EquipmentTypeFormSet(prefix='equipment_type')
        statuses = forms.StatusFormSet(prefix='status')
        locations = forms.LocationFormSet(prefix='location')
        os_types = forms.OSTypeFormSet(prefix='os_type')

    return render(request, 'tickets/settings.html', {
        "equipment_types": equipment_types,
        "statuses": statuses,
        "locations": locations,
        "os_types": os_types,
    })
