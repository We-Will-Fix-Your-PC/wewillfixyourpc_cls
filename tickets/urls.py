from django.urls import path
from . import views

app_name = 'tickets'
urlpatterns = [
    path('', views.view_tickets, name="view_tickets"),
    path('ticket/<ticket_id>/edit/', views.edit_ticket, name="edit_ticket"),
    path('ticket/<ticket_id>/label/', views.print_ticket_label, name="print_ticket"),
    path('ticket/<ticket_id>/receipt/', views.print_ticket_receipt, name="print_receipt"),
    path('ticket/<ticket_id>/', views.view_ticket, name="view_ticket"),
    path('new/', views.new_ticket, name="new"),
    path('new/<customer_id>/', views.new_ticket_step2, name="new_step2"),
    path('settings/', views.ticket_settings, name="settings"),
    path('search-customer/', views.search_customer, name="search_customer"),
    path('update/', views.send_ticket_update, name="send_update"),
    path('job/new/', views.new_job, name="new_job"),
    path('jobs/<user_id>/', views.view_jobs, name="view_jobs"),
    path('job/<job_id>/edit/', views.edit_job, name="edit_job"),
    path('job/<job_id>/', views.view_job, name="view_job"),
]
