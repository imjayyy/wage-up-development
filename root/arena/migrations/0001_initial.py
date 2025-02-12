# Generated by Django 2.1.4 on 2021-04-20 17:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0002_auto_20210311_0933'),
    ]

    operations = [
        migrations.CreateModel(
            name='hh5_driver_sat_extended',
            fields=[
                ('id', models.IntegerField(db_column='id', primary_key=True, serialize=False)),
                ('login_id', models.CharField(blank=True, db_column='login_id', max_length=255, null=True)),
                ('g1_base_size', models.IntegerField(blank=True, db_column='Nov 9 - Feb 28 group_1_base_size_sat_overall', null=True)),
                ('g1_count', models.IntegerField(blank=True, db_column='Nov 9 - Feb 28 group_1_count_overall_totly_stsfd', null=True)),
                ('g1_pcnt', models.IntegerField(blank=True, db_column='Nov 9 - Feb 28 group_1_pcnt_overall_totly_stsfd', null=True)),
                ('g2_base_size', models.IntegerField(blank=True, db_column='Dec 1 - Feb 28 group_2_base_size_sat_overall', null=True)),
                ('g2_count', models.IntegerField(blank=True, db_column='Dec 1 - Feb 28 group_2_count_overall_totly_stsfd', null=True)),
                ('g2_pcnt', models.IntegerField(blank=True, db_column='Dec 1 - Feb 28 group_2_pcnt_overall_totly_stsfd', null=True)),
                ('g3_base_size', models.IntegerField(blank=True, db_column='Jan 1 - Feb 28 group_3_base_size_sat_overall', null=True)),
                ('g3_count', models.IntegerField(blank=True, db_column='Jan 1 - Feb 28 group_3_count_overall_totly_stsfd', null=True)),
                ('g3_pcnt', models.IntegerField(blank=True, db_column='Jan 1 - Feb 28 group_3_pcnt_overall_totly_stsfd', null=True)),
                ('g4_base_size', models.IntegerField(blank=True, db_column='Feb 1 - Feb 28 group_4_base_size_sat_overall', null=True)),
                ('g4_count', models.IntegerField(blank=True, db_column='Feb 1 - Feb 28 group_4_count_overall_totly_stsfd', null=True)),
                ('g4_pcnt', models.IntegerField(blank=True, db_column='Feb 1 - Feb 28 group_4_pcnt_overall_totly_stsfd', null=True)),
                ('dec_group_base', models.IntegerField(blank=True, db_column='Dec 11 - Dec 31 base_size_sat_overall', null=True)),
                ('dec_group_count', models.IntegerField(blank=True, db_column='Dec 11 - Dec 31 count_overall_totly_stsfd', null=True)),
            ],
            options={
                'db_table': 'hh5_expansion_driver_sat_statistics_revised',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='hh5_drivers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver_name', models.CharField(blank=True, max_length=255, null=True)),
                ('station_name', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.EmailField(blank=True, max_length=255, null=True)),
                ('date_joined', models.DateTimeField(blank=True, null=True)),
                ('registered', models.BooleanField(null=True)),
                ('registered_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('username', models.CharField(blank=True, max_length=255, null=True)),
                ('registration_time', models.DateTimeField(blank=True, null=True)),
                ('reward_type', models.CharField(blank=True, max_length=255, null=True)),
                ('registration_group', models.CharField(blank=True, max_length=255, null=True)),
                ('hh5_station_cohort', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'hh5_drivers',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='hh5_drivers_sat_statistics',
            fields=[
                ('id', models.IntegerField(db_column='id', primary_key=True, serialize=False)),
                ('tech_id', models.CharField(blank=True, db_column='login_id', max_length=255, null=True)),
                ('station_name', models.CharField(blank=True, db_column='station_name', max_length=255, null=True)),
                ('registered', models.BooleanField(blank=True, db_column='registered', null=True)),
                ('id_name_helper', models.CharField(blank=True, db_column='driver_name', max_length=255, null=True)),
                ('call_volume', models.IntegerField(blank=True, db_column='call_volume', null=True)),
                ('base_size_sat_overall', models.IntegerField(blank=True, db_column='base_size_sat_overall', null=True)),
                ('count_overall_totly_stsfd', models.IntegerField(blank=True, db_column='count_overall_totly_stsfd', null=True)),
                ('pcnt_overall_totly_stsfd', models.FloatField(blank=True, db_column='pcnt_overall_totly_stsfd', null=True)),
                ('base_size_driver', models.IntegerField(blank=True, db_column='base_size_driver', null=True)),
                ('count_driver_totly_stsfd', models.IntegerField(blank=True, db_column='count_driver_totly_stsfd', null=True)),
                ('pcnt_driver_totly_stsfd', models.FloatField(blank=True, db_column='pcnt_driver_totly_stsfd', null=True)),
                ('pcnt_kept_informed_totly_stsfd', models.FloatField(blank=True, db_column='pcnt_kept_informed_totly_stsfd', null=True)),
                ('pcnt_driver_contct', models.FloatField(blank=True, db_column='pcnt_driver_contact', null=True)),
            ],
            options={
                'db_table': 'hh5_driver_sat_statistics',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Competition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Conference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('competition', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conference', to='arena.Competition')),
            ],
        ),
        migrations.CreateModel(
            name='Division',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('competition', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='division', to='arena.Competition')),
                ('conference', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='division', to='arena.Conference')),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('tournament_match', models.BooleanField(default=False)),
                ('division', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Division')),
            ],
        ),
        migrations.CreateModel(
            name='MatchScoreComponents',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='MatchScores',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(blank=True, null=True)),
                ('quarter', models.IntegerField(blank=True, null=True)),
                ('match', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Match')),
            ],
        ),
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('starts', models.DateField(blank=True, null=True)),
                ('ends', models.DateField(blank=True, null=True)),
                ('elimination', models.BooleanField(null=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('competition', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Competition')),
                ('precursor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='round_precursor', to='arena.Round')),
            ],
        ),
        migrations.CreateModel(
            name='ScoreComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('weight', models.FloatField(blank=True, null=True)),
                ('db_column_name', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SkillTreeDriverTeam',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SkillTreePlayer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_name', models.TextField(blank=True, null=True)),
                ('org_name', models.TextField(blank=True, null=True)),
                ('org_id', models.IntegerField(blank=True, null=True)),
                ('start_date', models.TextField(blank=True, null=True)),
                ('tenure_group', models.TextField(blank=True, null=True)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.Employee')),
            ],
        ),
        migrations.CreateModel(
            name='SkillTreePlayerSkills',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill_level', models.IntegerField(blank=True, null=True)),
                ('skill_level_max', models.IntegerField(blank=True, null=True)),
                ('skill_level_min', models.IntegerField(blank=True, null=True)),
                ('skill_name', models.TextField(blank=True, null=True)),
                ('tenure_average', models.FloatField(blank=True, null=True)),
                ('value', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('logo', models.CharField(blank=True, max_length=255, null=True)),
                ('abbreviation', models.CharField(blank=True, max_length=100, null=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('competition', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team', to='arena.Competition')),
                ('division', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Division')),
                ('organization_players', models.ManyToManyField(blank=True, to='accounts.Organization')),
            ],
            options={
                'ordering': ('competition', 'name'),
            },
        ),
        migrations.CreateModel(
            name='TeamEmployeeScores',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(blank=True, null=True)),
                ('volume', models.BigIntegerField(blank=True, null=True)),
                ('impact', models.FloatField(blank=True, null=True)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.Employee')),
                ('match', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Match')),
                ('round', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Team')),
            ],
        ),
        migrations.CreateModel(
            name='TeamEmployeeScoresComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField(blank=True, null=True)),
                ('component', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.ScoreComponent')),
                ('round', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round')),
                ('team_employee_scores', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.TeamEmployeeScores')),
            ],
        ),
        migrations.CreateModel(
            name='TeamOrganizationScores',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(blank=True, null=True)),
                ('volume', models.BigIntegerField(blank=True, null=True)),
                ('impact', models.FloatField(blank=True, null=True)),
                ('match', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Match')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.Organization')),
                ('round', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Team')),
            ],
        ),
        migrations.CreateModel(
            name='TeamOrganizationScoresComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField(blank=True, null=True)),
                ('component', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.ScoreComponent')),
                ('round', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round')),
                ('team_organization_scores', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.TeamOrganizationScores')),
            ],
        ),
        migrations.CreateModel(
            name='TeamRanking',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team_name', models.CharField(blank=True, max_length=255, null=True)),
                ('division', models.CharField(blank=True, max_length=255, null=True)),
                ('wins', models.IntegerField(blank=True, null=True)),
                ('losses', models.IntegerField(blank=True, null=True)),
                ('unplayed', models.IntegerField(blank=True, null=True)),
                ('division_rank', models.IntegerField(blank=True, null=True)),
                ('overall_rank', models.IntegerField(blank=True, null=True)),
                ('total_score', models.FloatField(default=0.0)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('competition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_rank', to='arena.Competition')),
                ('team', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_rank', to='arena.Team')),
            ],
            options={
                'ordering': ('competition', 'team_name'),
            },
        ),
        migrations.AddField(
            model_name='skilltreeplayer',
            name='skills',
            field=models.ManyToManyField(related_name='skills', to='arena.SkillTreePlayerSkills'),
        ),
        migrations.AddField(
            model_name='skilltreeplayer',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.SkillTreeDriverTeam'),
        ),
        migrations.AddField(
            model_name='matchscores',
            name='round',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round'),
        ),
        migrations.AddField(
            model_name='matchscores',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Team'),
        ),
        migrations.AddField(
            model_name='matchscorecomponents',
            name='component',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.ScoreComponent'),
        ),
        migrations.AddField(
            model_name='matchscorecomponents',
            name='match',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.MatchScores'),
        ),
        migrations.AddField(
            model_name='matchscorecomponents',
            name='round',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round'),
        ),
        migrations.AddField(
            model_name='match',
            name='round',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arena.Round'),
        ),
        migrations.AddField(
            model_name='match',
            name='teams',
            field=models.ManyToManyField(blank=True, to='arena.Team'),
        ),
        migrations.AlterIndexTogether(
            name='teamorganizationscores',
            index_together={('organization', 'team', 'match')},
        ),
        migrations.AlterIndexTogether(
            name='teamemployeescores',
            index_together={('employee', 'team', 'match')},
        ),
    ]
