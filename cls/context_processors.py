from django.conf import settings


def facebook_processor(request):
    return {
        "facebook_app_id": settings.FACEBOOK_APP_ID,
        "facebook_page_id": settings.FACEBOOK_PAGE_ID
    }


def keycloak_processor(request):
    return {
        "keycloak_realm": settings.KEYCLOAK_REALM
    }
