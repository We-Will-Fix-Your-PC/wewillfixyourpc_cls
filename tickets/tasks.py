from django.conf import settings
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
import django_keycloak_auth.clients
import requests
import json
from . import models


@shared_task
def send_ticket_update(tid: int, update_type: str, **kwargs):
    ticket = models.Ticket.objects.get(id=tid)

    models.TicketRevision(
        ticket=ticket,
        user=None,
        data=json.dumps({
            "type": "message",
            "msg_type": update_type,
            "kwargs": kwargs
        })
    ).save()

    if update_type == "ready":
        context = {
            "content": "Your repair is complete and your device is ready to collect at your earliest convenience",
            "ticket": ticket
        }
        html_email = render_to_string("emails/ticket_update.html", context)
        plain_email = render_to_string("emails/ticket_update_plain.html", context)
        text_message = f"Your We Will Fix Your PC repair (ticket #{ticket.id}) of a {ticket.equipment.name.lower()} " \
                       f"is complete and your device is ready to collect at your earliest convenience"
    elif update_type == "custom":
        context = {
            "content": kwargs.get("update_text", ""),
            "ticket": ticket
        }
        html_email = render_to_string("emails/ticket_update.html", context)
        plain_email = render_to_string("emails/ticket_update_plain.html", context)
        text_message = f"An update on your We Will Fix Your PC (ticket #{ticket.id}) repair of a " \
                       f"{ticket.equipment.name.lower()}: {kwargs.get('update_text', '')}"
    else:
        return

    customer = ticket.get_customer()

    if customer.get("email"):
        mail = EmailMultiAlternatives(
            'An update on your We Will Fix Your PC repair', plain_email,
            'We Will Fix Your PC <noreply@noreply.wewillfixyourpc.co.uk>', [customer.get("email")]
        )
        mail.reply_to = ["We Will Fix Your PC <neil@wewillfixyourpc.co.uk>"]
        mail.attach_alternative(html_email, 'text/html')
        mail.send()

    requests.post(f"{settings.CUSTOMER_SUPPORT_URL}api/send_message/{customer.get('id')}/", headers={
        "Authorization": f"Bearer {django_keycloak_auth.clients.get_access_token()}"
    }, json={
        "text": text_message
    })
