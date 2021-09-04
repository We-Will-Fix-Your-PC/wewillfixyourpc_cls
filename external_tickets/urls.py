from django.urls import path
from . import views

app_name = 'scrap'
urlpatterns = [
    path('', views.view_tickets, name="view_tickets"),
    path('new_ticket', views.new_ticket, name="new_ticket"),
]
