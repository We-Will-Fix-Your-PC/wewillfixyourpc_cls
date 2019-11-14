from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import ValidationError
import django_keycloak_auth.users


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


class Ticket(models.Model):
    customer = models.UUIDField()
    date = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    equipment = models.ForeignKey(EquipmentType, on_delete=models.SET_NULL, null=True, blank=False)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=False)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=False)
    booked_by = models.UUIDField()
    assigned_to = models.UUIDField()
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
        return django_keycloak_auth.users.get_user_by_id(self.customer)

    def get_assigned_to(self):
        return django_keycloak_auth.users.get_user_by_id(self.assigned_to)

    def get_booked_by(self):
        return django_keycloak_auth.users.get_user_by_id(self.booked_by)

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
