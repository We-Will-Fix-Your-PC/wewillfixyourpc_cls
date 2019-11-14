from django.urls import path
from . import views

app_name = 'checkin'
urlpatterns = [
    path('totp', views.totp, name='totp'),
    path('', views.index, name='index'),
    path('details', views.details, name='details'),
    path('done', views.done, name='done'),
    path('setup', views.setup, name='setup'),
    path('recent_customers', views.recent_customers, name='recent_customers'),
]
