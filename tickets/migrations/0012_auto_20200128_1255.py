# Generated by Django 2.2.7 on 2020-01-28 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0011_auto_20200118_1205'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='booked_by',
            field=models.UUIDField(null=True),
        ),
    ]
