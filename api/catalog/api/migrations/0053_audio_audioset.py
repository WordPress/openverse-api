# Generated by Django 4.1.2 on 2022-12-12 08:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0052_update_reporting_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='audio',
            name='audioset',
            field=models.ForeignObject(from_fields=['audio_set_foreign_identifier', 'provider'], null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='api.audioset', to_fields=['foreign_identifier', 'provider']),
        ),
    ]
