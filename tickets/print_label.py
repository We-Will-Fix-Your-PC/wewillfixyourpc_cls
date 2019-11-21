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
import secrets
import weasyprint
import django_keycloak_auth.users
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
        </style>
    </head>
    <body>
        <h2>Ticket #{{ id }}</h2>
        <h1>{{ customer.firstName }} {{ customer.lastName }}</h1>
        <p>
        {% if customer.email %}
            <b>Email:</b>
            {{ customer.email }}
            <br>
        {% endif %}
        {% for phone in customer.attributes.phone %}
            <b>Phone:</b>
            {{ phone }}
            <br>
        {% endfor %}
        </p>
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
            p {
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
            Any questions? Visit wewillfixyourpc.co.uk
        </p>
        <h2>Ticket #{{ ticket.id }}</h2>
        <h1>{{ ticket.get_customer().firstName }} {{ ticket.get_customer().lastName }}</h1>
        <p>
            <b>Date:</b> {{ ticket.date.strftime('%x') }}<br/>
            <b>Time:</b> {{ ticket.date.strftime('%X') }}<br/>
            <b>Equipment:</b> {{ ticket.equipment.name }}<br/>
            <b>Booked by:</b> {{ ticket.get_booked_by().firstName }}<br/>
            <b>Current OS:</b> {% if ticket.current_os %}{{ ticket.current_os.name }}{% else %}N/A{% endif %}<br/>
            <b>Wanted OS:</b> {% if ticket.wanted_os %}{{ ticket.wanted_os.name }}{% else %}N/A{% endif %}<br/>
            <b>Charger:</b> {% if ticket.has_charger %}Yes{% else %}No{% endif %}<br/>
            <b>Case:</b> {% if ticket.has_case %}Yes{% else %}No{% endif %}<br/>
            <b>Other equipment:</b> {% if ticket.other_equipment %}{{ ticket.other_equipment }}{% else %}N/A{% endif %}<br/>
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
                Your username is <em>{{ ticket.get_customer().username }}</em> and your temporary password is 
                <em>{{ temp_pass }}</em>
            {% endif %}
            <br/>
            <img src="data:image/png;base64,{{ qr }}" />
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
            im = convert_image(im)
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


def print_ticket_label(ticket: models.Ticket, driver: LabelDriver, num=1):
    doc = HTML(string=LABEL_TEMPLATE.render(id=ticket.id, customer=ticket.get_customer(), page_width=driver.width))\
        .render(enable_hinting=True)
    for i in range(num):
        driver.print_doc(doc)


def print_ticket_receipt(ticket: models.Ticket, driver: LabelDriver, num=1):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data('https://2.cardifftec.uk')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    target = io.BytesIO()
    img.save(target, 'png')
    qr_b64 = base64.b64encode(target.getvalue()).decode()

    user = ticket.get_customer()
    temp_pass = None
    if not user.get("email"):
        user = django_keycloak_auth.users.get_user_by_id(user.get("id"))
        temp_pass = secrets.token_hex(4)
        user.reset_password(temp_pass, temporary=True)

    doc = HTML(string=RECEIPT_TEMPLATE.render(ticket=ticket, qr=qr_b64, temp_pass=temp_pass, page_width=driver.width))\
        .render(enable_hinting=True)
    for i in range(num):
        driver.print_doc(doc)
