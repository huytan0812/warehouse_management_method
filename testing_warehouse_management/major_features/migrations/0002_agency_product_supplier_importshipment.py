# Generated by Django 4.0.2 on 2023-04-18 05:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('major_features', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Agency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('sku', models.CharField(default='000000', max_length=14, primary_key=True, serialize=False)),
                ('name', models.CharField(default='', max_length=500)),
                ('quantity_on_hand', models.IntegerField(blank=True, default=0, null=True)),
                ('minimum_quantity', models.IntegerField(blank=True, default=1, null=True)),
                ('current_total_value', models.IntegerField(blank=True, default=1, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ImportShipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('total_shipment_value', models.IntegerField(blank=True, default=0, null=True)),
                ('supplier_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_sent_import_shipments', to='major_features.supplier')),
            ],
        ),
    ]
