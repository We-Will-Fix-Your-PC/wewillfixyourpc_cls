from django.conf import settings
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
import phonenumbers
from . import models


@shared_task
def send_ticket_update(tid: int, update_type: str, **kwargs):
    ticket = models.Ticket.objects.get(id=tid)
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
        mail.reply_to = "We Will Fix Your PC <neil@wewillfixyourpc.co.uk>"
        mail.attach_alternative(html_email, 'text/html')
        mail.send()

    mobile_numbers = []
    other_numbers = []
    for n in customer.get("attributes", {}).get("phone", []):
        try:
            n = phonenumbers.parse(n, settings.PHONENUMBER_DEFAULT_REGION)
        except phonenumbers.phonenumberutil.NumberParseException:
            continue
        if phonenumbers.is_valid_number(n):
            if phonenumbers.phonenumberutil.number_type(n) == phonenumbers.PhoneNumberType.MOBILE:
                mobile_numbers.append(n)
            else:
                other_numbers.append(n)
    #
    # if len(mobile_numbers):
    #     for n in mobile_numbers:
    #         r = requests.post("https://rest.nexmo.com/sms/json", data={
    #             "from": "We Will Fix",
    #             "to": phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)[1:],
    #             "text": text_message,
    #             "api_key": settings.NEXMO_KEY,
    #             "api_secret": settings.NEXMO_SECRET
    #         })
    # else:
    #     for n in other_numbers:
    #         requests.post("https://rest.nexmo.com/sms/json", data={
    #             "from": "We Will Fix",
    #             "to": phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)[1:],
    #             "text": text_message,
    #             "api_key": settings.NEXMO_KEY,
    #             "api_secret": settings.NEXMO_SECRET
    #         })
