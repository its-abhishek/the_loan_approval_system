# Generated by Django 5.1.3 on 2024-11-10 18:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0002_customer_age"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loan",
            name="emis_paid_on_time",
            field=models.BooleanField(default=False),
        ),
    ]
