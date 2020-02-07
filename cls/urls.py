from django.urls import path
from . import views

app_name = 'cls'
urlpatterns = [
    path('', views.index, name='index'),
    path('search', views.search, name='search'),
    path('slack/interactive', views.slack_interactivity, name='slack_interactivity'),
]
