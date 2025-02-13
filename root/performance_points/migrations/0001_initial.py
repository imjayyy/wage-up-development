# Generated by Django 4.0.4 on 2023-04-19 21:29

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('training', '0003_modulepage_modulequestion_moduletag_and_more'),
        ('accounts', '0011_alter_stationdriver_table'),
        ('payments', '0006_alter_paymentlog_payment_method'),
    ]

    operations = [
        migrations.CreateModel(
            name='PPCampaignBank',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_points', models.IntegerField()),
                ('cashed_points', models.IntegerField()),
                ('cashed_points_dollars', models.FloatField()),
                ('not_cashed_points', models.IntegerField()),
            ],
            options={
                'db_table': 'performance_points_campaignbank',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PPCampaignPointsBreakdown',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variable', models.CharField(max_length=255)),
                ('value', models.IntegerField()),
            ],
            options={
                'db_table': 'performance_points_campaignpointsbreakdown',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PPDriverCurrent',
            fields=[
                ('id', models.IntegerField(db_column='id', primary_key=True, serialize=False, unique=True)),
                ('points', models.FloatField(blank=True, db_column='total_points', null=True)),
            ],
            options={
                'db_table': 'performance_points_current',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PPDriverHistorical',
            fields=[
                ('id', models.IntegerField(db_column='id', primary_key=True, serialize=False, unique=True)),
                ('points', models.FloatField(blank=True, db_column='total_points', null=True)),
            ],
            options={
                'db_table': 'performance_points_historical',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PPDriverLevel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total', models.FloatField(blank=True, db_column='total_points', null=True)),
                ('level', models.FloatField(blank=True, db_column='level', null=True)),
            ],
            options={
                'db_table': 'performance_points_driver_levels',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PPDriverPoints',
            fields=[
                ('id', models.IntegerField(db_column='id', primary_key=True, serialize=False, unique=True)),
                ('sc_dt', models.DateField(blank=True, db_column='SC_DT', null=True)),
                ('variable', models.CharField(blank=True, db_column='variable', max_length=255, null=True)),
                ('value', models.FloatField(blank=True, db_column='value', null=True)),
            ],
            options={
                'db_table': 'performance_points_driver_points',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PPDriverPointsSettings',
            fields=[
                ('id', models.IntegerField(db_column='id', primary_key=True, serialize=False, unique=True)),
                ('config', models.TextField(blank=True, db_column='configuration', null=True)),
                ('start_date', models.DateField(blank=True, db_column='start_date', null=True)),
                ('end_date', models.DateField(blank=True, db_column='end_date', null=True)),
                ('active', models.BooleanField(blank=True, db_column='active', null=True)),
            ],
            options={
                'db_table': 'performance_points_settings',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CampaignPointsSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('configuration', models.TextField(blank=True, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('active', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'performance_points_settings',
            },
        ),
        migrations.CreateModel(
            name='DriverPointsSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('config', models.TextField(blank=True, db_column='configuration', null=True)),
                ('start_date', models.DateField(blank=True, db_column='start_date', null=True)),
                ('end_date', models.DateField(blank=True, db_column='end_date', null=True)),
                ('active', models.BooleanField(blank=True, db_column='active', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PerformancePointStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variable', models.CharField(blank=True, max_length=255, null=True)),
                ('max_dt', models.DateField(null=True)),
                ('avg', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PPCampaign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('start', models.DateField(blank=True, null=True)),
                ('end', models.DateField(blank=True, null=True)),
                ('active', models.BooleanField(default=True)),
                ('position_type', models.CharField(blank=True, max_length=255, null=True)),
                ('registration_eligibility', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('image', models.FileField(blank=True, null=True, upload_to='')),
                ('slug', models.SlugField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.employee')),
                ('geography_eligiblity', models.ManyToManyField(related_name='campaign_geography_eligibility', to='accounts.organization')),
                ('performance_points_config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='performance_points.campaignpointssettings')),
                ('registration_requirements', models.ManyToManyField(related_name='registration_modules', to='training.moduleoverview')),
                ('tremendousCampaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='payments.tremendouscampaign')),
            ],
        ),
        migrations.CreateModel(
            name='PPComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('explanation', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PPContest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateField()),
                ('end', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='PPDriverRanks',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, null=True)),
                ('list', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PPMatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='PPRound',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField()),
                ('elimination', models.BooleanField(default=False)),
                ('starts', models.DateField()),
                ('ends', models.DateField()),
                ('contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='round_contest', to='performance_points.ppcontest')),
            ],
        ),
        migrations.CreateModel(
            name='PPTeam',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('logo', models.FileField(null=True, upload_to='team_logos/with_background/')),
                ('transparent_logo', models.FileField(null=True, upload_to='team_logos/transparent/')),
                ('slug', models.SlugField(blank=True, null=True)),
                ('small_icon', models.FileField(null=True, upload_to='team_logos/small_icon')),
            ],
        ),
        migrations.CreateModel(
            name='PPTeamContest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='TeamContest_team_contest', to='performance_points.ppcontest')),
                ('team', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='TeamContest_team', to='performance_points.ppteam')),
                ('territory', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_contest_territory', to='accounts.organization')),
            ],
        ),
        migrations.CreateModel(
            name='TeamPreferences',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preference', models.IntegerField(blank=True, null=True)),
                ('player_level', models.IntegerField(blank=True, null=True)),
                ('player_level_group', models.IntegerField(blank=True, null=True)),
                ('captain', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_captain_preferences', to='accounts.employee')),
                ('player', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_preference_player', to='accounts.employee')),
                ('team', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_preference_team', to='performance_points.ppteamcontest')),
            ],
        ),
        migrations.CreateModel(
            name='TeamAssignments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player_type', models.CharField(choices=[('Captain', 'Captain'), ('Player', 'Player')], default='Player', max_length=255)),
                ('player', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_assignments_player', to='accounts.employee')),
                ('team', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_assignments_team', to='performance_points.ppteamcontest')),
                ('territory', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_assignments_territory', to='accounts.organization')),
            ],
        ),
        migrations.CreateModel(
            name='PPTeamScoreComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.IntegerField()),
                ('component', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_score_component_component', to='performance_points.ppcomponent')),
                ('contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_score_component_contest', to='performance_points.ppcontest')),
                ('round', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_score_component_round', to='performance_points.ppround')),
                ('team_contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_score_component_team', to='performance_points.ppteamcontest')),
            ],
        ),
        migrations.CreateModel(
            name='PPTeamScore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.IntegerField()),
                ('contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_score_contest', to='performance_points.ppcontest')),
                ('match', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='team_score_round', to='performance_points.ppmatch')),
                ('team_contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='team_score_team', to='performance_points.ppteamcontest')),
            ],
        ),
        migrations.CreateModel(
            name='PPTeamRankings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.IntegerField()),
                ('losses', models.IntegerField()),
                ('wins', models.IntegerField()),
                ('score', models.IntegerField()),
                ('team_contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_rankings_team', to='performance_points.ppteamcontest')),
            ],
        ),
        migrations.AddField(
            model_name='ppmatch',
            name='round',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='match_contest', to='performance_points.ppround'),
        ),
        migrations.AddField(
            model_name='ppmatch',
            name='teams',
            field=models.ManyToManyField(to='performance_points.ppteamcontest'),
        ),
        migrations.AddField(
            model_name='ppcomponent',
            name='contest',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='component_contest', to='performance_points.ppcontest'),
        ),
        migrations.CreateModel(
            name='PPCampaignRegistration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration_date', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='performance_points.ppcampaign')),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_registration', to='accounts.employee')),
                ('related_employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_registration_related_emp', to='accounts.employee')),
            ],
        ),
        migrations.CreateModel(
            name='PPCampaignBankTransactionLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
                ('points', models.IntegerField()),
                ('dollars', models.FloatField()),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_bank_transaction', to='performance_points.ppcampaign')),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_bank_log_employee', to='accounts.employee')),
                ('paymentLog', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_bank_transaction', to='payments.paymentlog')),
            ],
        ),
        migrations.CreateModel(
            name='Fed',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point_to_dollar_conversion', models.FloatField()),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('period', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fed_period', to='performance_points.driverpointssettings')),
            ],
        ),
        migrations.CreateModel(
            name='Bets',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(blank=True, default='PRE-PERIOD', max_length=255, null=True)),
                ('ratio', models.IntegerField()),
                ('points_bet', models.IntegerField()),
                ('target', models.IntegerField()),
                ('metric', models.CharField(blank=True, max_length=255, null=True)),
                ('bet_made_on', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(blank=True, db_column='EMP_DRIVER_ID', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='driver_bets', to='accounts.employee')),
                ('for_period', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bets_period', to='performance_points.driverpointssettings')),
            ],
        ),
        migrations.CreateModel(
            name='Bank',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('withdrawal_request', 'withdrawal_request'), ('bet_allocation', 'bet_allocation'), ('dollar_conversion', 'dollar_conversion')], max_length=255)),
                ('pending_payment_amount', models.IntegerField(default=0)),
                ('bet_allocation', models.IntegerField(default=0)),
                ('payment_summary', models.IntegerField(default=0)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bank_employee', to='accounts.employee')),
            ],
        ),
    ]
