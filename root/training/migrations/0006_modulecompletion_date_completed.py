# Generated by Django 4.0.4 on 2024-12-26 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0005_remove_moduletag_campaign_moduleoverview_campaign_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='modulecompletion',
            name='date_completed',
            field=models.DateField(blank=True, null=True),
        ),
    ]
