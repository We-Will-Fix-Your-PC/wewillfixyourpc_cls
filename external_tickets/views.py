from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
import tickets.models
import django_keycloak_auth
import json
from . import forms


def require_booker(func):
    @login_required
    def inner(request, *args, **kwargs):
        user = django_keycloak_auth.users.get_user_by_id(request.user.username)
        is_booker = bool(next(
            filter(
                lambda r: r.get("name") == "external-booker",
                user.role_mappings.realm.get()
            ),
            False
        ))

        if not is_booker:
            return HttpResponseForbidden()

        return func(request, *args, **kwargs)

    return inner


@require_booker
def view_tickets(request):
    cust_tickets = tickets.models.Ticket.objects\
        .filter(Q(customer=request.user.username), ~Q(status__name="Collected"))\
        .order_by('-date')

    return render(request, "external_tickets/index.html", {
        "tickets": cust_tickets,
        "msg": request.session.pop("external_tickets_msg", None)
    })


@require_booker
def new_ticket(request):
    ticket = tickets.models.Ticket(
        customer=request.user.username,
        booked_by=request.user.username,
        status=tickets.models.Status.objects.get(name="Booked in"),
        location=tickets.models.Location.objects.get(name="With customer"),
        has_charger=False,
    )
    if request.method == 'POST':
        form = forms.TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()

            tickets.models.TicketRevision(
                ticket=form.instance,
                user=request.user.username,
                data=json.dumps({
                    "type": "create"
                })
            ).save()

            request.session["external_tickets_msg"] = f"Ticket #{form.instance.id} successfully created"
            return redirect("external_tickets:view_tickets")

        print(form.errors)
    else:
        form = forms.TicketForm(instance=ticket)

    return render(request, "external_tickets/new_ticket.html", {
        "form": form,
    })
