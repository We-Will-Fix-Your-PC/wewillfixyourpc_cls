from django.db import models


class Credential(models.Model):
    customer = models.UUIDField()
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.name
