# Generated by Django 2.1.4 on 2021-09-02 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0009_timeseriespredictionsbyhournew_total_drivers_wait_15'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeseriesscheduleddrivers',
            name='lunch_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='timeseriesscheduleddrivers',
            name='truck',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='timeseriesscheduleddrivers',
            name='truck_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
