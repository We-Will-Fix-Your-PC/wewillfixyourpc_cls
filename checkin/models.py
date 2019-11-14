from django.db import models


class Checkin(models.Model):
    customer = models.UUIDField()
    timestamp = models.DateTimeField(auto_now_add=True)
