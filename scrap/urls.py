from django.urls import path
from . import views

app_name = 'scrap'
urlpatterns = [
    path('', views.view_items, name="view_items"),
    path('new/', views.new_item, name="new_item"),
    path('item/<item_id>/', views.view_item, name="view_item"),
    path('item/<item_id>/edit/', views.edit_item, name="edit_item"),
    path('item/<item_id>/delete/', views.delete_item, name="delete_item"),
    path('settings/', views.item_settings, name="settings"),
]
