from django.utils import timezone
from django.template.loader import render_to_string
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import EmailMessage
from tickets import models


class Command(BaseCommand):
    help = "Emails about old tickets"

    def handle(self, *args, **options):
        old_tickets = models.Ticket.objects.filter(date_updated__lte=(timezone.now() - timezone.timedelta(days=1)))

        email_cont = render_to_string("emails/old_tickets.html", {
            "url_prefix": settings.EXTERNAL_URL_BASE,
            "tickets": old_tickets
        })

        email = EmailMessage(
            'Old ticket summary', email_cont, 'noreply@noreply.wewillfixyourpc.co.uk', [settings.UPDATES_EMAIL]
        )
        email.content_subtype = 'html'
        email.send()
