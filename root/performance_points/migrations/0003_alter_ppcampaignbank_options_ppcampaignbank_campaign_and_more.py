# Generated by Django 4.0.4 on 2023-04-21 23:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_stationdriver_table'),
        ('performance_points', '0002_alter_ppcampaignbank_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ppcampaignbank',
            options={'managed': True},
        ),
        migrations.AddField(
            model_name='ppcampaignbank',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_bank', to='performance_points.ppcampaign'),
        ),
        migrations.AddField(
            model_name='ppcampaignbank',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_bank_employee', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='ppcampaignpointsbreakdown',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_points_breakdown_campaign', to='performance_points.ppcampaign'),
        ),
        migrations.AddField(
            model_name='ppcampaignpointsbreakdown',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_points_breakdown_employee', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='ppdrivercurrent',
            name='club_region',
            field=models.ForeignKey(blank=True, db_column='ORG_CLUB_REGION', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_current_region', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdrivercurrent',
            name='config',
            field=models.ForeignKey(blank=True, db_column='config_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_current_settings', to='performance_points.ppdriverpointssettings'),
        ),
        migrations.AddField(
            model_name='ppdrivercurrent',
            name='driver',
            field=models.ForeignKey(blank=True, db_column='EMP_DRIVER_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_current', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='ppdrivercurrent',
            name='station',
            field=models.ForeignKey(blank=True, db_column='ORG_SVC_FACL_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_current_station', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdrivercurrent',
            name='station_business',
            field=models.ForeignKey(blank=True, db_column='ORG_BUSINESS_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_current_station_business', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdrivercurrent',
            name='territory',
            field=models.ForeignKey(blank=True, db_column='ORG_TERRITORY_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_current_territory', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverhistorical',
            name='club_region',
            field=models.ForeignKey(blank=True, db_column='ORG_CLUB_REGION', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_history_region', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverhistorical',
            name='config',
            field=models.ForeignKey(blank=True, db_column='config_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_history_settings', to='performance_points.driverpointssettings'),
        ),
        migrations.AddField(
            model_name='ppdriverhistorical',
            name='driver',
            field=models.ForeignKey(blank=True, db_column='EMP_DRIVER_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_history', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='ppdriverhistorical',
            name='station',
            field=models.ForeignKey(blank=True, db_column='ORG_SVC_FACL_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_history_station', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverhistorical',
            name='station_business',
            field=models.ForeignKey(blank=True, db_column='ORG_BUSINESS_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_history_station_business', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverhistorical',
            name='territory',
            field=models.ForeignKey(blank=True, db_column='ORG_TERRITORY_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_history_territory', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverlevel',
            name='driver',
            field=models.ForeignKey(blank=True, db_column='EMP_DRIVER_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_level', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='ppdriverpoints',
            name='club_region',
            field=models.ForeignKey(blank=True, db_column='ORG_CLUB_REGION', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_points_region', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverpoints',
            name='config',
            field=models.ForeignKey(blank=True, db_column='config_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_points_settings', to='performance_points.driverpointssettings'),
        ),
        migrations.AddField(
            model_name='ppdriverpoints',
            name='driver',
            field=models.ForeignKey(blank=True, db_column='EMP_DRIVER_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_points', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='ppdriverpoints',
            name='station',
            field=models.ForeignKey(blank=True, db_column='ORG_SVC_FACL_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_points_station', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverpoints',
            name='station_business',
            field=models.ForeignKey(blank=True, db_column='ORG_BUSINESS_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_points_station_business', to='accounts.organization'),
        ),
        migrations.AddField(
            model_name='ppdriverpoints',
            name='territory',
            field=models.ForeignKey(blank=True, db_column='ORG_TERRITORY_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pp_driver_points_territory', to='accounts.organization'),
        ),
    ]
