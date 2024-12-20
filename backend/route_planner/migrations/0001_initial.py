# Generated by Django 3.2.23 on 2024-10-26 21:57

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Station',
            fields=[
                ('opis_id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('address', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=2)),
                ('rack_id', models.IntegerField()),
                ('price', models.DecimalField(decimal_places=8, max_digits=10)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ],
        ),
        migrations.AddIndex(
            model_name='station',
            index=models.Index(fields=['state'], name='route_plann_state_bf59c9_idx'),
        ),
        migrations.AddIndex(
            model_name='station',
            index=models.Index(fields=['price'], name='route_plann_price_7e1eab_idx'),
        ),
    ]
