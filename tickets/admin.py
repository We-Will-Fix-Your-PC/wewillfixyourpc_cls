from django.contrib import admin
from . import models

admin.site.register(models.Job)
admin.site.register(models.Status)
admin.site.register(models.EquipmentType)
admin.site.register(models.Location)
admin.site.register(models.OSType)
admin.site.register(models.Ticket)
admin.site.register(models.TicketImage)
admin.site.register(models.TicketRevision)
