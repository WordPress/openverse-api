# Generated by Django 2.0.13 on 2019-03-07 18:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import oauth2_provider.generators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0018_auto_20190122_1917'),
    ]

    operations = [
        migrations.CreateModel(
            name='OAuth2Registration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='A unique human-readable name for your application or project requiring access to the Openverse API.', max_length=150, unique=True)),
                ('description', models.CharField(help_text='A description of what you are trying to achieve with your project using the API. Please provide as much detail as possible!', max_length=10000)),
                ('email', models.EmailField(help_text='A valid email that we can reach you at if we have any questions about your use case or data consumption.', max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='ThrottledApplication',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('client_id', models.CharField(db_index=True, default=oauth2_provider.generators.generate_client_id, max_length=100, unique=True)),
                ('redirect_uris', models.TextField(blank=True, help_text='Allowed URIs list, space separated')),
                ('client_type', models.CharField(choices=[('confidential', 'Confidential'), ('public', 'Public')], max_length=32)),
                ('authorization_grant_type', models.CharField(choices=[('authorization-code', 'Authorization code'), ('implicit', 'Implicit'), ('password', 'Resource owner password-based'), ('client-credentials', 'Client credentials')], max_length=32)),
                ('client_secret', models.CharField(blank=True, db_index=True, default=oauth2_provider.generators.generate_client_secret, max_length=255)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('skip_authorization', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('rate_limit_model', models.CharField(choices=[('standard', 'standard'), ('enhanced', 'enhanced')], default='standard', max_length=20)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='api_throttledapplication', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='image',
            name='foreign_identifier',
            field=models.CharField(blank=True, db_index=True, help_text='The identifier provided by the upstream source.', max_length=1000, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='foreign_landing_url',
            field=models.CharField(blank=True, help_text='The landing page of the work.', max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='identifier',
            field=models.UUIDField(db_index=True, help_text='A unique identifier that we assign on ingestion.', unique=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='provider',
            field=models.CharField(blank=True, db_index=True, help_text='The content provider, e.g. Flickr, 500px...', max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='source',
            field=models.CharField(blank=True, db_index=True, help_text='The source of the data, meaning a particular dataset. Source and provider can be different: the Google Open Images dataset is source=openimages., but provider=Flickr.', max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='thumbnail',
            field=models.URLField(blank=True, help_text='The thumbnail for the image, if any.', max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='url',
            field=models.URLField(help_text='The actual URL to the image.', max_length=1000, unique=True),
        ),
    ]
