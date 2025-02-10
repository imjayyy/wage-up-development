# Generated by Django 4.0.4 on 2024-12-06 16:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance_points', '0015_remove_ppcampaign_tremendouscampaign_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpringUp2024DriverTable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver_id', models.CharField(blank=True, max_length=255, null=True)),
                ('full_name', models.CharField(blank=True, max_length=255, null=True)),
                ('station', models.CharField(blank=True, max_length=255, null=True)),
                ('username', models.CharField(blank=True, max_length=255, null=True)),
                ('field_consultant', models.CharField(blank=True, max_length=255, null=True)),
                ('registered', models.CharField(blank=True, max_length=255, null=True)),
                ('registration_date', models.DateField(blank=True, null=True)),
                ('mar_overall_sat', models.FloatField(blank=True, null=True)),
                ('mar_totally_sat_survey', models.IntegerField(blank=True, null=True)),
                ('mar_potential_payment', models.FloatField(blank=True, null=True)),
                ('mar_actual_payment', models.FloatField(blank=True, null=True)),
                ('apr_overall_sat', models.FloatField(blank=True, null=True)),
                ('apr_totally_sat_survey', models.IntegerField(blank=True, null=True)),
                ('apr_potential_payment', models.FloatField(blank=True, null=True)),
                ('apr_actual_payment', models.FloatField(blank=True, null=True)),
                ('may_overall_sat', models.FloatField(blank=True, null=True)),
                ('may_totally_sat_survey', models.IntegerField(blank=True, null=True)),
                ('may_potential_payment', models.FloatField(blank=True, null=True)),
                ('may_actual_payment', models.FloatField(blank=True, null=True)),
                ('june_overall_sat', models.FloatField(blank=True, null=True)),
                ('june_totally_sat_survey', models.IntegerField(blank=True, null=True)),
                ('june_potential_payment', models.FloatField(blank=True, null=True)),
                ('june_actual_payment', models.FloatField(blank=True, null=True)),
                ('july_overall_sat', models.FloatField(blank=True, null=True)),
                ('july_totally_sat_survey', models.IntegerField(blank=True, null=True)),
                ('july_potential_payment', models.FloatField(blank=True, null=True)),
                ('july_actual_payment', models.FloatField(blank=True, null=True)),
                ('august_overall_sat', models.FloatField(blank=True, null=True)),
                ('august_totally_sat_survey', models.IntegerField(blank=True, null=True)),
                ('august_potential_payment', models.FloatField(blank=True, null=True)),
                ('august_actual_payment', models.FloatField(blank=True, null=True)),
            ],
            options={
                'db_table': 'spring_2024_driver_table',
                'managed': False,
            },
        ),
        migrations.AddField(
            model_name='ppcampaignregistration',
            name='communication_opt_in',
            field=models.BooleanField(default=False, verbose_name='Opt-in for Communications'),
        ),
    ]
