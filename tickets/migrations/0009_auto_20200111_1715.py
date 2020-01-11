# Generated by Django 2.2.7 on 2020-01-11 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0008_job'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='completed',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='to_do_by',
            field=models.DateField(blank=True, null=True),
        ),
    ]
