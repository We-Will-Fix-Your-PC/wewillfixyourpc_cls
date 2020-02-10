from celery import shared_task
from django.utils import timezone
import django_keycloak_auth.users
from . import models
import json
import datetime


@shared_task
def fetch_user(user_id):
    user = django_keycloak_auth.users.get_user_by_id(user_id).user
    models.CustomerCache(cust_id=user_id, data=json.dumps(user)).save()
    return user


def get_user(user_id):
    if not user_id:
        return None
    customer = models.CustomerCache.objects.filter(cust_id=user_id).order_by('-last_updated').first()
    if customer:
        if customer.last_updated < timezone.now() - datetime.timedelta(minutes=20):
            fetch_user.delay(user_id)
        return json.loads(customer.data)
    else:
        return fetch_user(user_id)
