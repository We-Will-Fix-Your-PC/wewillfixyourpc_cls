from weasyprint import HTML
import jinja2
import escpos.constants
import escpos.printer
import math
import cairocffi as cairo
import io
import base64
import abc
import qrcode
import struct
import weasyprint
import requests
import brother_ql.devicedependent
import brother_ql.backends.helpers
import django_keycloak_auth.users
from django.conf import settings
from django.shortcuts import reverse
import importlib
from PIL import Image, ImageOps

from . import models

LABEL_TEMPLATE = jinja2.Template("""
<html>
    <head>
        <style>
            @page {
              width: {{ page_width }}px;
              height: 4000px;
              margin: 0;
            }
            body {
              margin: 0;
              font-family: sans-serif;
              text-align: center;
            }
            * {
              max-width: {{ page_width }}px;
              word-wrap: normal;
            }
            p {
                font-size: 25px;
            }
            h2 {
                font-size: 30px;
            }
            h1 {
                font-size: 40px;
            }
            img {
                max-width: 100%
            }
        </style>
    </head>
    <body>
        <div style="width:30%;float:left;">
          <img src="data:image/png;base64,{{ qr }}" />
        </div>
        <div style="width:70%;float:left;">
            <h2>Ticket #{{ id }}</h2>
            <h1>{{ customer.firstName }} {{ customer.lastName }}</h1>
        </div>
        <div>
            <p>
                {% if customer.email %}
                    <b>Email:</b>
                    {{ customer.email }}
                    <br>
                {% endif %}
                {% for phone in customer.get("attributes", {}).get("phone", []) %}
                    <b>Phone:</b>
                    {{ phone }}
                    <br>
                {% endfor %}
            </p>
        <div>
    </body>
</html>
""")

RECEIPT_TEMPLATE = jinja2.Template("""
<html>
    <head>
        <style>
            @page {
              width: {{ page_width }}px;
              height: 4000px;
              margin: 0;
            }
            body {
              margin: 0;
              font-family: sans-serif;
              text-align: center;
            }
            * {
              max-width: {{ page_width }}px;
              word-wrap: normal;
            }
            p, table {
                font-size: 25px;
            }
            h2 {
                font-size: 30px;
            }
            h1 {
                font-size: 40px;   
            }
        </style>
    </head>
    <body>
        <img src="https://wewillfixyourpc.co.uk/wwfypc-logo-wd.png" />
        <p>
            39 Lambourne Crescent<br/>
            Cardiff, CF14 5GG<br/>
            (029) 2076 6039<br />
            Any questions?<br/>account-support@wewillfixyourpc.co.uk
        </p>
        <h2>Ticket #{{ ticket.id }}</h2>
        <h1>{{ ticket.get_customer().firstName }} {{ ticket.get_customer().lastName }}</h1>
        <table>
            <tr>
                <th>Time<th>
                <td colspan="3">{{ ticket.date.strftime('%x') }} {{ ticket.date.strftime('%X') }}</td>
            </tr>
            <tr>
                <th>Equipment</th>
                <td>{{ ticket.equipment.name }}</td>
                <th>Booked by</th>
                <td>{{ ticket.get_booked_by().firstName }}</td>
            </tr>
            <tr>
                <th>Current OS</th>
                <td>{% if ticket.current_os %}{{ ticket.current_os.name }}{% else %}N/A{% endif %}</td>
                <th>Wanted OS</th>
                <td>{% if ticket.wanted_os %}{{ ticket.wanted_os.name }}{% else %}N/A{% endif %}</td>
            </tr>
            <tr>
                <th>Charger</th>
                <td>{% if ticket.has_charger %}Yes{% else %}No{% endif %}</td>
                <th>Case</th>
                <td>{% if ticket.has_case %}Yes{% else %}No{% endif %}</td>
            </tr>
            <tr>
                <th>Other equipment</th>
                <td colspan="3">{% if ticket.other_equipment %}{{ ticket.other_equipment }}{% else %}N/A{% endif %}</td>
            </tr>
        </table>
        </p>
        <p>
            Thank you for choosing<br/><b>We Will Fix Your PC</b><br/><br/>
            You can view the status of your repair using the QR code below.<br/>
            You'll need to sign in with your<br/><b>We Will Fix Your PC ID</b><br/><br/>
            {% if ticket.get_customer().email %}
                Your username is <em>{{ ticket.get_customer().username }}</em> and instructions to complete setup of
                your <b>We Will Fix Your PC ID</b> have been sent to <em>{{ ticket.get_customer().email }}</em> if you
                have not already setup your account.
            {% else %}
                Your username is <em>{{ ticket.get_customer().username }}</em>.
            {% endif %}
            <br/>
            <br/>
            You can sign into your <b>We Will Fix Your PC ID</b> using your password and/or external providers such
            as <em>Sign in with Google</em> and <em>Sign in with Apple</em>, or you can use the QR code/link below to
             login for the next 7 days.<br/>
            <img src="data:image/png;base64,{{ qr }}" /><br/>
            <em>{{ url }}</em>
        </p>
    </body>
</html>
""")


def convert_image(img: Image) -> Image:
    img_original = img.convert('RGBA')
    im = Image.new("RGB", img_original.size, (255, 255, 255))
    im.paste(img_original, mask=img_original.split()[3])
    wpercent = (384 / float(im.size[0]))
    hsize = int((float(im.size[1]) * float(wpercent)))
    im = im.resize((384, hsize), Image.ANTIALIAS)
    im = im.convert("L")
    im = ImageOps.invert(im)
    im = im.convert("1")
    return im


class LabelDriver(abc.ABC):
    @property
    def width(self):
        raise NotImplementedError

    def start_print(self):
        raise NotImplementedError

    def print_image(self, image: Image.Image):
        raise NotImplementedError

    def end_print(self):
        raise NotImplementedError

    def print_doc(self, doc: weasyprint.Document):
        dppx = 1

        widths = [int(math.ceil(p.width * dppx)) for p in doc.pages]
        heights = [int(math.ceil(p._page_box.children[0].height * dppx)) for p in doc.pages]

        max_width = max(widths)
        self.start_print()
        for page, width, height in zip(doc.pages, widths, heights):
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max_width, height)
            context = cairo.Context(surface)
            pos_x = (max_width - width) / 2
            page.paint(context, pos_x, 0, scale=dppx, clip=True)
            target = io.BytesIO()
            surface.write_to_png(target)
            target.seek(0)
            im = Image.open(target)
            im.load()
            self.print_image(im)
        self.end_print()


class EscPosUsbDriver(LabelDriver):
    def __init__(self, width=384):
        self._width = width
        self._printer = escpos.printer.Usb(0x0416, 0x5011)
        self._printer._raw(escpos.constants.ESC + b"@")

    @property
    def width(self):
        return self._width

    def start_print(self):
        self._printer._raw(escpos.constants.ESC + b"3\x16")

    def end_print(self):
        self._printer._raw(escpos.constants.ESC + b"2")
        self._printer.text("\n" * 3)

    def print_image(self, im: Image.Image):
        im = convert_image(im)
        outp = []
        header = escpos.constants.ESC + b"*\x21" + struct.pack("<H", im.width)
        im = im.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
        line_height = 24
        width_pixels, height_pixels = im.size
        top = 0
        left = 0
        while left < width_pixels:
            box = (left, top, left + line_height, top + height_pixels)
            im_slice = im.transform((line_height, height_pixels), Image.EXTENT, box)
            im_bytes = im_slice.tobytes()
            outp.append(header + im_bytes + b"\n")
            left += line_height
        self._printer._raw(b''.join(outp))


class BrotherDriver(LabelDriver):
    def __init__(self, printer=None, model='QL-720NW', label='62'):
        self._label_id = label
        self._label = brother_ql.devicedependent.label_type_specs[label]
        self._model = model
        self._printer = printer
        self._qrl = None

    @property
    def width(self):
        return self._label['dots_printable'][0]//1.3

    def start_print(self):
        self._qrl = brother_ql.BrotherQLRaster(self._model)

    def end_print(self):
        brother_ql.backends.helpers.send(self._qrl.data, self._printer)
        self._qrl = None

    def print_image(self, im: Image.Image):
        brother_ql.create_label(self._qrl, im, self._label_id, dither=True)


class DummyDriver(LabelDriver):
    def __init__(self, width=384):
        self._width = width

    @property
    def width(self):
        return self._width

    def start_print(self):
        pass

    def end_print(self):
        pass

    def print_image(self, im: Image.Image):
        pass


def _get_default_driver(driver: LabelDriver = None):
    if driver:
        return driver

    module_name, class_name = settings.PRINTER_DRIVER.rsplit('.', 1)
    return getattr(importlib.import_module(module_name), class_name)(**settings.PRINTER_DRIVER_OPS)

def make_qr(link):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    target = io.BytesIO()
    img.save(target, 'png')
    qr_b64 = base64.b64encode(target.getvalue()).decode()
    return qr_b64


def print_ticket_label(ticket: models.Ticket, driver: LabelDriver = None, num=1):
    driver = _get_default_driver(driver)

    url = f"{settings.EXTERNAL_URL_BASE}{reverse('tickets:view_ticket', args=(ticket.id,))}"

    r = requests.post("https://firebasedynamiclinks.googleapis.com/v1/shortLinks", params={
        'key': settings.FIREBASE_URL_API_KEY
    }, json={
        "dynamicLinkInfo": {
            "domainUriPrefix": "https://wwfypc.xyz",
            "link": url,
        },
        "suffix": {
            "option": "SHORT"
        }
    })
    r.raise_for_status()
    short_url = r.json().get("shortLink")

    for _ in range(num):
        doc = HTML(string=LABEL_TEMPLATE.render(
            id=ticket.id, customer=ticket.get_customer(), qr=make_qr(short_url), page_width=driver.width
        ))\
            .render(enable_hinting=True)
        driver.print_doc(doc)


def print_ticket_receipt(ticket: models.Ticket, driver: LabelDriver=None, num=1):
    driver = _get_default_driver(driver)

    user = ticket.get_customer()
    key = django_keycloak_auth.users.get_user_magic_key(user.get("id")).get('key')
    url = f"{settings.EXTERNAL_URL_BASE}{reverse('oidc_login')}?key={key}"

    r = requests.post("https://firebasedynamiclinks.googleapis.com/v1/shortLinks", params={
        'key': settings.FIREBASE_URL_API_KEY
    }, json={
        "dynamicLinkInfo": {
            "domainUriPrefix": "https://wwfypc.xyz",
            "link": url,
        },
        "suffix": {
            "option": "UNGUESSABLE"
        }
    })
    r.raise_for_status()
    short_url = r.json().get("shortLink")

    for _ in range(num):
        doc = HTML(string=RECEIPT_TEMPLATE.render(
            ticket=ticket, qr=make_qr(short_url), url=short_url, page_width=driver.width
        ))\
            .render(enable_hinting=True)
        driver.print_doc(doc)
