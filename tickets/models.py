from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import ValidationError
import django_keycloak_auth.users
import datetime
import json
import customers.models
from django.utils import timezone


class EquipmentType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class OSType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Status(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=255)
    os_required = models.BooleanField(default=False)

    def __str__(self):
        return self.name


def get_user(user_id):
    expiry = timezone.now() - datetime.timedelta(minutes=10)
    customer = customers.models.CustomerCache.objects.filter(cust_id=user_id, last_updated__gte=expiry) \
        .order_by('-last_updated').first()
    if customer:
        return json.loads(customer.data)
    user = django_keycloak_auth.users.get_user_by_id(user_id).user
    customers.models.CustomerCache(cust_id=user_id, data=json.dumps(user)).save()
    return user


class Ticket(models.Model):
    customer = models.UUIDField()
    date = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    equipment = models.ForeignKey(EquipmentType, on_delete=models.SET_NULL, null=True, blank=False)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=False)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=False)
    booked_by = models.UUIDField(null=True)
    assigned_to = models.UUIDField(blank=True, null=True)
    current_os = \
        models.ForeignKey(OSType, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_current")
    wanted_os = \
        models.ForeignKey(OSType, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_wanted")
    quote = models.DecimalField(decimal_places=2, max_digits=9, blank=True, null=True)
    has_charger = models.BooleanField(verbose_name="Charger?")
    has_case = models.BooleanField(verbose_name="Case?")
    other_equipment = models.CharField(max_length=255, blank=True, null=True)
    to_do_by = models.DateField(blank=True, null=True)
    whats_it_doing = RichTextUploadingField()
    work_done = RichTextUploadingField(blank=True, null=True)

    def __str__(self):
        return f"#{self.id}"

    def get_customer(self):
        return get_user(self.customer)

    def get_assigned_to(self):
        return get_user(self.assigned_to)

    def get_booked_by(self):
        return get_user(self.booked_by)

    def clean(self):
        if self.location.os_required:
            if not self.current_os:
                raise ValidationError({
                    'current_os': ['Please select an os'],
                })
            if not self.wanted_os:
                raise ValidationError({
                    'wanted_os': ['Please select an os'],
                })

        super().clean()


class TicketRevision(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='revisions')
    user = models.UUIDField()
    time = models.DateTimeField(auto_now_add=True)
    data = models.TextField()

    class Meta:
        ordering = ('-time',)

    def get_user(self):
        return get_user(self.user)

    def get_data(self):
        return json.loads(self.data)


class TicketImage(models.Model):
    item = models.ForeignKey(Ticket, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(blank=False)

    def __str__(self):
        return f"#{self.id}"


class Job(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    assigned_to = models.UUIDField()
    title = models.CharField(max_length=255)
    completed = models.BooleanField()
    to_do_by = models.DateField(blank=True, null=True)
    description = RichTextUploadingField(blank=True, null=True)

    def __str__(self):
        return f"#{self.id}"

    def get_assigned_to(self):
        return get_user(self.assigned_to)
