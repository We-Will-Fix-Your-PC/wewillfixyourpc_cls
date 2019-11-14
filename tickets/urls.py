from django.urls import path
from . import views

app_name = 'tickets'
urlpatterns = [
    path('', views.view_tickets, name="view_tickets"),
    path('ticket/<ticket_id>/edit', views.edit_ticket, name="edit_ticket"),
    path('new/', views.new_ticket, name="new"),
    path('new/<customer_id>', views.new_ticket_step2, name="new_step2"),
    path('settings/', views.ticket_settings, name="settings"),
    path('search-customer/', views.search_customer, name="search_customer")
]
