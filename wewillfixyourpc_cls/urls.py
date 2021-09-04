"""wewillfixyourpc_cls URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('cls.urls')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('checkin/', include('checkin.urls', namespace='checkin')),
    path('tickets/', include('tickets.urls', namespace='tickets')),
    path('sale/', include('sale.urls', namespace='sale')),
    path('scrap/', include('scrap.urls', namespace='scrap')),
    path('external/', include('external_tickets.urls', namespace='external_tickets')),
    path("auth/", include("django_keycloak_auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static("static/", document_root=settings.STATIC_ROOT)
    urlpatterns += static("media/", document_root=settings.MEDIA_ROOT)

handler500 = 'cls.views.handler500'
