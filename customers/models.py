from django.db import models


class CustomerCache(models.Model):
    cust_id = models.UUIDField(editable=False, primary_key=True)
    data = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)


class Credential(models.Model):
    customer = models.UUIDField()
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.name
