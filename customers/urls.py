from django.urls import path
from . import views

app_name = 'customers'
urlpatterns = [
    path('', views.view_customers, name="view_customers"),
    path('customers/<customer_id>', views.view_customer, name="view_customer"),
    path('customers/<customer_id>/edit', views.edit_customer, name="edit_customer"),
    path('new/', views.new_customer, name="new")
]
