from django.shortcuts import render
from django.db.models import Q
import django_keycloak_auth.users
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
import tickets.models
import tickets.views
import json
import time
import hmac


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
                           q in u.get("email", "").lower().strip()) or
                          any([q in p for p in u.get("attributes").get("phone", [])]) for q in query),
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


@csrf_exempt
def slack_interactivity(request):
    if request.method != "POST":
        return HttpResponse(status=415)

    body = request.body.decode()
    timestamp = int(request.headers.get("X-Slack-Request-Timestamp", 0))
    slack_signature = request.headers.get('X-Slack-Signature')
    sig_basestring = f'v0:{timestamp}:{body}'

    if abs(time.time() - timestamp) > 60 * 5:
        return HttpResponse(status=403)

    my_signature = 'v0=' + hmac.new(
        settings.SLACK_INTERACTIVITY_TOKEN.encode(),
        sig_basestring.encode(),
        'sha256'
    ).hexdigest()
    if not hmac.compare_digest(my_signature, slack_signature):
        return HttpResponse(status=403)

    payload = json.loads(request.POST.get("payload", "{}"))
    response_url = payload.get("response_url")
    trigger_id = payload.get("trigger_id")

    if payload.get("type") == "block_actions":
        actions = payload.get("actions", {})
        for action in actions:
            action_id = action.get("action_id")
            action_value = action.get("value")

            if action_id == "send_ticket_update":
                tickets.views.slack_send_ticket_update(response_url, trigger_id, action_value)

    elif payload.get("type") == "view_submission":
        view = payload.get("view", {})
        metadata = view.get("private_metadata")
        values = view.get("state", {}).get("values", {})
        action_id = view.get("callback_id")
        if action_id == "send_ticket_update":
            tickets.views.slack_send_ticket_update2(response_url, trigger_id, metadata, values)

    return HttpResponse("")
