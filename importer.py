import json
import typing
import datetime
import phonenumbers
import django
import mysql.connector as mysql

django.setup()

from django.conf import settings
import tickets.models
import customers.models
import django_keycloak_auth.clients
import django_keycloak_auth.users

with open("secrets/mysql.json") as f:
    secrets = json.load(f)

db = mysql.connect(
    host='localhost',
    port=3306,
    user=secrets.get("user"),
    passwd=secrets.get("pass"),
    database='cls',
)

admin_client = django_keycloak_auth.clients.get_keycloak_admin_client()
client = next(
    filter(
        lambda c: c.get("clientId") == settings.OIDC_CLIENT_ID,
        admin_client.clients.all()
    )
)
agents = admin_client._client.get(
    url=admin_client._client.get_full_url(
        'auth/admin/realms/{realm}/clients/{id}/roles/{role_name}/users'
            .format(realm=admin_client._name, id=client.get("id"), role_name="agent")
    )
)

equipment = ["Laptop", "Desktop", "Tablet", "Phone", "Other", "A.I.O", "Mac", "Multiple"]
booked_by = ["Neil", "Matt", "Dan", None, None, None, None]
assigned_to = [None, "Neil", "Matt", "Dan"]
location = [None, "Self (L)", "Shelf (R)", "Bench", "Rebuild", "Completed", "Desktop", "With customer", "Part finding"]
status = [None, "Booked in", "Assigned", "Awaiting parts", "Awaiting customer decision", "Completed", "Collected",
          "Testing", None, None, "Looking for parts"]
os = ["Windows XP", "Windows 7 Home Premium", "Windows 7 Pro", "Windows 8 Home", "Windows 8 Pro", "Windows 10 Home",
      "Windows 10 Pro", "macOS", "Linux", "N/A", "Windows 8.1 Home", "Windows 8.1 Pro", "Windows Vista",
      "OSX El Capitan"]

cursor = db.cursor()

cursor.execute("SELECT `ti_id`, `eq_id`, `bb_id`, `ast_id`, `loc_id`, `ts_id`, `ti_name`, `ti_phone_number`,"
               "`ti_email`, `ti_date`, `ti_password`, `ti_details`, `ti_quote`, `ti_charger`, `ti_case`, `ti_other`,"
               "`ti_workdone`, `ti_created`, `ti_updated`, `ti_to_do_by`, `ti_rebuild_current_os`,"
               "`ti_rebuild_wanted_os`"
               " FROM tickets WHERE `ts_id` != 6 ORDER BY `ti_id` DESC")


def map_ticket(ticket):
    try:
        phone = phonenumbers.parse(ticket[7], settings.PHONENUMBER_DEFAULT_REGION)
        if not phonenumbers.is_valid_number(phone):
            phone = None
        else:
            phone = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        phone = None

    return {
        "id": ticket[0],
        "equipment": equipment[ticket[1]],
        "booked_by": booked_by[ticket[2]],
        "assigned_to": assigned_to[ticket[3]],
        "location": location[ticket[4]],
        "status": status[ticket[5]],
        "customer": {
            "name": ticket[6],
            "phone_number": phone,
            "email": ticket[8] if ticket[8] else None,
        },
        "created": ticket[17],
        "updated": ticket[18],
        "to_do_by": ticket[19],
        "charger": bool(ticket[13]),
        "case": bool(ticket[14]),
        "other_equipment": ticket[15] if ticket[15] else None,
        "quote": ticket[12] if ticket[12] != "Q" else "",
        "details": ticket[11],
        "work_done": ticket[16] if ticket[16] else None,
        "password": ticket[10],
        "current_os": os[int(ticket[20])],
        "wanted_os": os[int(ticket[20])],
    }


ticket_objs = map(map_ticket, cursor.fetchall())


def get_or_create_object(obj: typing.Type[tickets.models.models.Model], *args, **kwargs):
    try:
        return obj.objects.get(*args, **kwargs)
    except obj.DoesNotExist:
        o = obj(*args, **kwargs)
        o.save()
        return o


def get_create_agent(name):
    user = next(filter(lambda a: a.get("firstName") == name, agents), None)
    if user is None:
        user = django_keycloak_auth.users.get_or_create_user(first_name=name)
        role = next(
            filter(
                lambda r: r.get("name") == "agent",
                admin_client._client.get(
                    url=admin_client._client.get_full_url(
                        'auth/admin/realms/{realm}/users/{id}/role-mappings/clients/{client}/available'
                            .format(realm=admin_client._name, id=user.get("id"), client=client.get("id"))
                    )
                ),
            ),
            None
        )
        admin_client._client.post(
            url=admin_client._client.get_full_url(
                'auth/admin/realms/{realm}/users/{id}/role-mappings/clients/{client}'
                    .format(realm=admin_client._name, id=user.get("id"), client=client.get("id"))
            ),
            data=json.dumps([role])
        )
        agents.append(user)
    return user


def get_create_customer(customer):
    users = django_keycloak_auth.users.get_users()

    if customer["phone_number"]:
        user_by_phone = next(
            filter(
                lambda u: customer["phone_number"] in u.user.get("attributes", {}).get("phone", []),
                users
            ),
            None
        )
        if user_by_phone:
            django_keycloak_auth.users.link_roles_to_user(user_by_phone.user["id"], ["customer"])
            return user_by_phone.user

    if customer["email"]:
        user_by_email = next(
            filter(
                lambda u: u.user.get("email") == customer["email"],
                users
            ),
            None
        )
        if user_by_email:
            django_keycloak_auth.users.link_roles_to_user(user_by_email.user["id"], ["customer"])
            return user_by_email.user

    names = customer["name"].split(" ")
    first_name = " ".join(names[:-1])
    last_name = names[-1]

    user_by_name = next(
        filter(
            lambda u: u.user.get("firstName") == first_name and u.user.get("lastName") == last_name,
            users
        ),
        None
    )
    if user_by_name:
        django_keycloak_auth.users.link_roles_to_user(user_by_name.user["id"], ["customer"])
        return user_by_name.user

    user = django_keycloak_auth.users.get_or_create_user(
        email=customer["email"], first_name=first_name, last_name=last_name, phone=customer["phone_number"],
        required_actions=["UPDATE_PROFILE", "UPDATE_PASSWORD"]
    )
    django_keycloak_auth.users.link_roles_to_user(user["id"], ["customer"])
    return user


def create_secondary_objects(ticket):
    ticket["current_os"] = get_or_create_object(tickets.models.OSType, name=ticket["current_os"])
    ticket["wanted_os"] = get_or_create_object(tickets.models.OSType, name=ticket["wanted_os"])
    ticket["equipment"] = get_or_create_object(tickets.models.EquipmentType, name=ticket["equipment"])
    ticket["location"] = get_or_create_object(tickets.models.Location, name=ticket["location"])
    ticket["status"] = get_or_create_object(tickets.models.Status, name=ticket["status"])

    ticket["booked_by"] = get_create_agent(ticket["booked_by"])["id"]

    if ticket["assigned_to"] is not None:
        ticket["assigned_to"] = get_create_agent(ticket["assigned_to"])["id"]

    ticket["customer"] = get_create_customer(ticket["customer"])["id"]

    return ticket


for ticket in map(create_secondary_objects, ticket_objs):
    if ticket["password"]:
        credential = customers.models.Credential(
            customer=ticket["customer"],
            name="Password",
            password=ticket["password"]
        )
        credential.save()

    try:
        quote = float(ticket["quote"]) if ticket["quote"] else None
    except ValueError:
        quote = None

    ticket_o = tickets.models.Ticket(
        id=int(ticket["id"]),
        date=ticket["created"],
        equipment=ticket["equipment"],
        status=ticket["status"],
        location=ticket["location"],
        booked_by=ticket["booked_by"],
        assigned_to=ticket["assigned_to"],
        current_os=ticket["current_os"],
        wanted_os=ticket["wanted_os"],
        quote=quote,
        has_charger=ticket["charger"],
        has_case=ticket["case"],
        other_equipment=ticket["other_equipment"],
        to_do_by=ticket["to_do_by"] if ticket["to_do_by"] != datetime.datetime(1970, 1, 1) else None,
        whats_it_doing=ticket["details"],
        work_done=ticket["work_done"],
        customer=ticket["customer"],
    )
    ticket_o.save()
    tickets.models.Ticket.objects.filter(id=ticket_o.id).update(date=ticket["created"], date_updated=ticket["updated"])
