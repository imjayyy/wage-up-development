# Generated by Django 2.1.4 on 2021-06-23 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_auto_20210609_1656'),
        ('messaging', '0005_auto_20210604_1324'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcements',
            name='target_by_facility_rep',
            field=models.ManyToManyField(related_name='targeting_facility_rep', to='accounts.Organization'),
        ),
        migrations.AddField(
            model_name='announcements',
            name='target_by_station_business',
            field=models.ManyToManyField(related_name='targeting_station_business', to='accounts.Organization'),
        ),
        migrations.AddField(
            model_name='announcements',
            name='target_by_station_states',
            field=models.ManyToManyField(related_name='targeting_station_state', to='accounts.Organization'),
        ),
        migrations.AddField(
            model_name='announcements',
            name='target_by_stations',
            field=models.ManyToManyField(related_name='targeting_stations', to='accounts.Organization'),
        ),
    ]
