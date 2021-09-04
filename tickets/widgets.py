import django_keycloak_auth.clients
import django_keycloak_auth.users
from django import forms
from django.conf import settings


class CustomerWidget(forms.Select):
    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)

    @property
    def choices(self):
        customers = list(
            map(
                lambda u: (
                    u.user.get("id"),
                    f'{u.user.get("firstName")} {u.user.get("lastName")} '
                    f'({u.user.get("email") if u.user.get("email") else "no email"})'
                ),
                filter(
                    lambda u: next(filter(
                        lambda r: r.get('name') == 'customer', u.role_mappings.realm.get()
                    ), False),
                    django_keycloak_auth.users.get_users()
                )
            )
        )
        customers.insert(0, ('', '---------'))
        return customers

    @choices.setter
    def choices(self, _):
        pass


class AgentWidget(forms.Select):
    def __init__(self, external_booker=False, attrs=None):
        print(external_booker)
        self.external_booker = external_booker
        super().__init__(attrs=attrs)
        self._client = None

    @property
    def choices(self):
        client = django_keycloak_auth.clients.get_keycloak_admin_client()
        if not self._client:
            self._client = next(
                filter(
                    lambda c: c.get("clientId") == settings.OIDC_CLIENT_ID,
                    client.clients.all()
                )
            )

        def map_user(u):
            return u.get("id"), f'{u.get("firstName", "")} {u.get("lastName", "")} '

        def get_by_role(role):
            return list(
                map(
                    map_user,
                    filter(
                        lambda u: u.get('enabled', False),
                        client._client.get(
                            url=client._client.get_full_url(
                                role
                            )
                        )
                    )
                )
            )

        agents = get_by_role('auth/admin/realms/{realm}/clients/{id}/roles/agent/users'.format(realm=client._name, id=self._client.get("id")))
        if self.external_booker:
            external_bookers = get_by_role('auth/admin/realms/{realm}/roles/external-booker/users'.format(realm=client._name))
            agents += external_bookers

        agents.insert(0, ('', '---------'))
        return agents

    @choices.setter
    def choices(self, _):
        pass

    def __deepcopy__(self, memodict={}):
        return AgentWidget(external_booker=self.external_booker, attrs=self.attrs)
