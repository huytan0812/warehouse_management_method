# Generated by Django 4.2.4 on 2023-09-07 09:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('major_features', '0013_accoutingperiod_cogs_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accoutingperiod',
            name='quantity_inventory',
        ),
    ]
