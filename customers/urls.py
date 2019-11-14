from django.urls import path
from . import views

app_name = 'customers'
urlpatterns = [
    path('', views.view_customers, name="view_customers"),
    path('customer/<customer_id>', views.view_customer, name="view_customer"),
    path('customer/<customer_id>/edit', views.edit_customer, name="edit_customer"),
    path('new/', views.new_customer, name="new"),
    path('credential/new/<customer_id>', views.new_credential, name="new_credential"),
    path('credential/edit/<credential_id>', views.edit_credential, name="edit_credential"),
]
