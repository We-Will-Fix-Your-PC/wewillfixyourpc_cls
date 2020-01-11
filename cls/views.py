from django.shortcuts import render
from django.db.models import Q
import django_keycloak_auth.users
from django.contrib.auth.decorators import login_required, permission_required
import tickets.models


@login_required
def index(request):
    user = django_keycloak_auth.users.get_user_by_id(request.user.username)
    role = next(
        filter(
            lambda r: r.get("name") == "customer",
            user.role_mappings.realm.get()
        ),
        False
    )
    is_customer = True if role else False

    repairs = tickets.models.Ticket.objects.filter(customer=request.user.username)

    return render(request, "cls/index.html", {
        "is_customer": is_customer,
        "repairs": repairs
    })


@login_required
@permission_required('customers.view_customer', raise_exception=True)
@permission_required('tickets.view_ticket', raise_exception=True)
def search(request):
    query = request.GET.get("q").strip().lower().split(" ")

    customers = list(
        filter(
            lambda u: any((q in u.get("firstName", "").lower().strip() or q in u.get("lastName", "").lower().strip() or
                           q in u.get("email", "").lower().strip()) for q in query),
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
