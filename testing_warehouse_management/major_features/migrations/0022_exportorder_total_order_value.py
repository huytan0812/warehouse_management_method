# Generated by Django 4.2 on 2023-09-12 03:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('major_features', '0021_remove_exportorder_total_order_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='exportorder',
            name='total_order_value',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]