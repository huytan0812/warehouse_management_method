# Generated by Django 4.2 on 2023-09-11 08:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('major_features', '0018_accountingperiodinventory'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountingperiodinventory',
            name='import_inventory',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='accountingperiodinventory',
            name='import_quantity',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
