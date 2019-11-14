from django.shortcuts import render
from django.db.models import Q
import django_keycloak_auth.users
from django.contrib.auth.decorators import login_required, permission_required
import tickets.models


@login_required
@permission_required('customers.view_customer', raise_exception=True)
@permission_required('tickets.view_ticket', raise_exception=True)
def index(request):
    return render(request, "cls/index.html")


@login_required
@permission_required('customers.view_customer', raise_exception=True)
@permission_required('tickets.view_ticket', raise_exception=True)
def search(request):
    query = request.GET.get("q").strip().lower()

    customers = list(
        filter(
            lambda u: query in u.get("firstName").lower().strip() or query in u.get("lastName").lower().strip(),
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
    )
    customer_ids = list(
        map(
            lambda u: u.get("id"),
            customers
        )
    )

    ticket_filter = Q(customer__in=customer_ids)
    if query.isnumeric():
        ticket_filter |= Q(id=query)
    ticket_objs = tickets.models.Ticket.objects.filter(ticket_filter)

    return render(request, "cls/search.html", {
        "tickets": ticket_objs,
        "customers": customers
    })
