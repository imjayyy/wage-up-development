# Generated by Django 4.0.4 on 2023-05-26 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance_points', '0010_alter_ppcampaignpointsbreakdown_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampaignRegistrationStatusView2023',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(blank=True, max_length=255, null=True)),
                ('organization_name', models.CharField(blank=True, max_length=255, null=True)),
                ('facility_rep', models.CharField(blank=True, max_length=255, null=True)),
                ('registration_date', models.DateField(blank=True, null=True)),
                ('username', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'CampaignRegistrationStatusView2023',
                'managed': False,
            },
        ),
        migrations.AlterModelOptions(
            name='ppcampaignbank',
            options={'managed': True},
        ),
    ]
