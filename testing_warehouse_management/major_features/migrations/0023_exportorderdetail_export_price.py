# Generated by Django 4.2 on 2023-09-12 03:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('major_features', '0022_exportorder_total_order_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='exportorderdetail',
            name='export_price',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
