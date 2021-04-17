from django.shortcuts import render
import django_keycloak_auth.users
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.http import HttpResponse
from django.conf import settings
from sentry_sdk import last_event_id
import customers.tasks
import customers.views
import tickets.models
import tickets.views
import json
import time
import hmac
import jwt
import datetime


@login_required
def index(request):
    msg = request.GET.get("msg")
    user = django_keycloak_auth.users.get_user_by_id(request.user.username)
    role = next(
        filter(
            lambda r: r.get("name") == "customer",
            user.role_mappings.realm.get()
        ),
        False
    )
    is_customer = True if role else False
    email = user.user.get("email")
    phones = user.user.get("attributes", {}).get("phone", [])

    customer_id_jwt = jwt.encode({
        'cust_id': user.user.get("id"),
        'iat': datetime.datetime.utcnow(),
        'nbf': datetime.datetime.utcnow()
    }, settings.FACEBOOK_OPTIN_SECRET, algorithm='HS256')

    repairs = tickets.models.Ticket.objects.filter(Q(customer=request.user.username), ~Q(status__name="Collected"))

    return render(request, "cls/index.html", {
        "is_customer": is_customer,
        "repairs": repairs,
        "customer": {
            "email": email,
            "phones": phones,
            "ref": customer_id_jwt
        },
        "msg": msg
    })


@login_required
@permission_required('customers.view_customer', raise_exception=True)
@permission_required('tickets.view_ticket', raise_exception=True)
def search(request):
    query_2 = request.GET.get("q").strip()
    query = query_2.lower().split(" ")

    c = list(
        filter(
            lambda u: any(
                ((q in u.get("firstName", "").lower().strip() or q in u.get("lastName", "").lower().strip() or
                           q in u.get("email", "").lower().strip()) or
                 any([q in p for p in u.get("attributes", {}).get("phone", [])])) for q in query),
            customers.views.get_customers()
        )
    )
    customer_ids = list(
        map(
            lambda u: u.get("id"),
            c
        )
    )

    ticket_filter = Q(customer__in=customer_ids)
    if query_2.isnumeric():
        ticket_filter |= Q(id=query_2)
    ticket_objs = tickets.models.Ticket.objects.filter(ticket_filter)

    return render(request, "cls/search.html", {
        "tickets": ticket_objs,
        "customers": c
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


def handler500(request, *args, **argv):
    email = None
    name = None
    if request.user:
        email = request.user.email
        name = f"{request.user.first_name} {request.user.last_name}"
    return render(request, "500.html", {
        'sentry_event_id': last_event_id(),
        "email": email,
        "name": name
    }, status=500)
