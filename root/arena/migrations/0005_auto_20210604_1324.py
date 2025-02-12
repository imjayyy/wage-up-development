# Generated by Django 2.1.4 on 2021-06-04 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arena', '0004_drivercampaign_payout_converter'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaignmetrics',
            name='agg_metric',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='campaignmetrics',
            name='agg_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='campaignmetrics',
            name='templated',
            field=models.BooleanField(default=False),
        ),
    ]
