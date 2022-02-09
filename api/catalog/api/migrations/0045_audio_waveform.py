# Generated by Django 3.2.9 on 2022-02-09 16:45

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0044_singular_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='audio',
            name='waveform',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), blank=True, help_text='The waveform peaks. A list of floats in the range of 0 -> 1 inclusively.', null=True, size=1500),
        ),
    ]
