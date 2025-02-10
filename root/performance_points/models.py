from django.db import models
from accounts.models import Employee, Organization, UserActions
from django.db.models import Count, F, Value
from training.models import ModuleOverview, ModuleTag, ModuleCompletion
from django.utils import timezone

# Create your models here.


class PPContest(models.Model):
    start = models.DateField()
    end = models.DateField()

    def __str__(self):
        return f'{self.start:%Y-%m-%d}-{self.end:%Y-%m-%d}'

class PPRound(models.Model):
    contest = models.ForeignKey(PPContest, null=True, on_delete=models.SET_NULL, related_name='round_contest')
    order = models.IntegerField()
    elimination = models.BooleanField(default=False)
    starts = models.DateField()
    ends = models.DateField()

class PPTeam(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    logo = models.FileField(null=True, upload_to='team_logos/with_background/')
    transparent_logo = models.FileField(null=True, upload_to='team_logos/transparent/')
    slug = models.SlugField(null=True, blank=True)
    small_icon = models.FileField(null=True, upload_to='team_logos/small_icon')

class PPTeamContest(models.Model):
    team = models.ForeignKey(PPTeam, null=True, on_delete=models.SET_NULL, related_name='TeamContest_team')
    contest = models.ForeignKey(PPContest, null=True, on_delete=models.SET_NULL, related_name='TeamContest_team_contest')
    territory = models.ForeignKey(Organization, null=True, on_delete=models.SET_NULL, related_name='team_contest_territory')

class TeamAssignments(models.Model):
    territory = models.ForeignKey(Organization, null=True, on_delete=models.SET_NULL, related_name='team_assignments_territory')
    team = models.ForeignKey(PPTeamContest, null=True, on_delete=models.SET_NULL, related_name='team_assignments_team')
    player_type = models.CharField(choices=(('Captain', 'Captain'), ('Player', 'Player')), default='Player', max_length=255)
    player = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='team_assignments_player')

class PPMatch(models.Model):
    round = models.ForeignKey(PPRound, null=True, on_delete=models.SET_NULL, related_name='match_contest')
    teams = models.ManyToManyField(PPTeamContest)

    def current_winner(self):
        teams = PPTeamScore.objects.filter(match=self.id)
        return [t for t in teams if t.score == max([t.score for t in teams])][0]

class PPTeamScore(models.Model):
    team_contest = models.ForeignKey(PPTeamContest, null=True, on_delete=models.DO_NOTHING, related_name='team_score_team')
    match = models.ForeignKey(PPMatch, null=True, on_delete=models.DO_NOTHING, related_name='team_score_round')
    score = models.IntegerField()
    contest = models.ForeignKey(PPContest, null=True, on_delete=models.SET_NULL, related_name='team_score_contest')

class PPComponent(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    display_name = models.CharField(blank=True, null=True, max_length=255)
    explanation = models.TextField(null=True, blank=True)
    contest = models.ForeignKey(PPContest, null=True, on_delete=models.SET_NULL, related_name='component_contest')

class PPTeamScoreComponent(models.Model):
    team_contest = models.ForeignKey(PPTeamContest, null=True, on_delete=models.SET_NULL, related_name='team_score_component_team')
    round = models.ForeignKey(PPRound, null=True, on_delete=models.SET_NULL, related_name='team_score_component_round')
    component = models.ForeignKey(PPComponent, null=True, on_delete=models.SET_NULL, related_name='team_score_component_component')
    score = models.IntegerField()
    contest = models.ForeignKey(PPContest, null=True, on_delete=models.SET_NULL, related_name='team_score_component_contest')

class TeamPreferences(models.Model):
    captain = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='team_captain_preferences')
    team = models.ForeignKey(PPTeamContest, null=True, on_delete=models.SET_NULL, related_name='team_preference_team')
    player = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='team_preference_player')
    preference = models.IntegerField(null=True, blank=True)
    player_level = models.IntegerField(null=True, blank=True)
    player_level_group = models.IntegerField(null=True, blank=True)# 1, 2, 3

class PPTeamRankings(models.Model):
    team_contest = models.ForeignKey(PPTeamContest, null=True, on_delete=models.SET_NULL, related_name='team_rankings_team')
    rank = models.IntegerField()
    losses = models.IntegerField()
    wins = models.IntegerField()
    score = models.IntegerField()

class PPDriverPointsSettings(models.Model):
    id = models.IntegerField(db_column='id', unique=True, primary_key=True)
    config = models.TextField(db_column='configuration', null=True, blank=True)
    start_date = models.DateField(db_column='start_date', null=True, blank=True)
    end_date = models.DateField(db_column='end_date', null=True, blank=True)
    active = models.BooleanField(db_column='active', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'performance_points_settings'

class DriverPointsSettings(models.Model):
    config = models.TextField(db_column='configuration', null=True, blank=True)
    start_date = models.DateField(db_column='start_date', null=True, blank=True)
    end_date = models.DateField(db_column='end_date', null=True, blank=True)
    active = models.BooleanField(db_column='active', null=True, blank=True)

class PPDriverPoints(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True, unique=True)
    sc_dt = models.DateField(db_column='SC_DT', null=True, blank=True)
    driver = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_points')
    station = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_points_station')
    station_business = models.ForeignKey(Organization, db_column='ORG_BUSINESS_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_points_station_business')
    # territory = models.ForeignKey(Organization, db_column='ORG_TERRITORY_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_points_territory')
    # club_region = models.ForeignKey(Organization, db_column='ORG_CLUB_REGION', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_points_region')
    config = models.ForeignKey(DriverPointsSettings, db_column='config_id', on_delete=models.SET_NULL, null=True, blank=True, related_name='pp_driver_points_settings')
    variable = models.CharField(db_column='variable', max_length=255, null=True, blank=True)
    value = models.FloatField(db_column='value', null=True, blank=True)

    class Meta:
        # managed = False
        db_table = 'performance_points_driver_points'


class PPDriverCurrent(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True, unique=True)
    driver = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', on_delete=models.SET_NULL, null=True, blank=True, related_name='pp_driver_current')
    station = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_current_station')
    station_business = models.ForeignKey(Organization, db_column='ORG_BUSINESS_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_current_station_business')
    territory = models.ForeignKey(Organization, db_column='ORG_TERRITORY_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_current_territory')
    club_region = models.ForeignKey(Organization, db_column='ORG_CLUB_REGION', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_current_region')
    config = models.ForeignKey(PPDriverPointsSettings, db_column='config_id', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_current_settings')
    points = models.FloatField(db_column='total_points', blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'performance_points_current'

class PPDriverHistorical(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True, unique=True)
    driver = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', on_delete=models.SET_NULL, null=True, blank=True, related_name='pp_driver_history')
    station = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_history_station')
    station_business = models.ForeignKey(Organization, db_column='ORG_BUSINESS_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_history_station_business')
    territory = models.ForeignKey(Organization, db_column='ORG_TERRITORY_ID', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_history_territory')
    club_region = models.ForeignKey(Organization, db_column='ORG_CLUB_REGION', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_history_region')
    config = models.ForeignKey(DriverPointsSettings, db_column='config_id', on_delete=models.SET_NULL, blank=True, null=True, related_name='pp_driver_history_settings')
    points = models.FloatField(db_column='total_points', blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'performance_points_historical'


class PPDriverLevel(models.Model):
    driver = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', null=True, blank=True, on_delete=models.SET_NULL, related_name='pp_driver_level')
    total = models.FloatField(db_column='total_points', null=True, blank=True)
    level = models.FloatField(db_column='level', null=True, blank=True)

    class Meta:
        # managed = False
        db_table = 'performance_points_driver_levels'

class PPDriverRanks(models.Model):
    date = models.DateField(null=True, blank=True)
    list = models.TextField(null=True, blank=True)

class Fed(models.Model):
    point_to_dollar_conversion = models.FloatField()
    date = models.DateTimeField(auto_now_add=True)
    period = models.ForeignKey(DriverPointsSettings, null=True, blank=True, on_delete=models.SET_NULL, related_name='fed_period')

class Bank(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='bank_employee')
    action = models.CharField(max_length=255, choices=[('withdrawal_request', 'withdrawal_request'), ('bet_allocation', 'bet_allocation'), ('dollar_conversion', 'dollar_conversion')])
    pending_payment_amount = models.IntegerField(default=0)
    bet_allocation = models.IntegerField(default=0)
    payment_summary = models.IntegerField(default=0)

class Bets(models.Model):
    driver = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', null=True, blank=True, on_delete=models.SET_NULL, related_name='driver_bets')
    status = models.CharField(null=True, max_length=255, blank=True, default='PRE-PERIOD')
    ratio = models.IntegerField()
    points_bet = models.IntegerField()
    target = models.IntegerField()
    metric = models.CharField(null=True, max_length=255, blank=True)
    bet_made_on = models.DateTimeField(auto_now_add=True)
    for_period = models.ForeignKey(DriverPointsSettings, null=True, blank=True, on_delete=models.SET_NULL, related_name='bets_period')


class PerformancePointStats(models.Model):
    variable = models.CharField(null=True, max_length=255, blank=True)
    max_dt = models.DateField(null=True)
    avg = models.FloatField(null=True, blank=True)

### campaigns

class PPCampaign(models.Model):
    title = models.CharField(max_length=255)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    display_start = models.DateField(null=True, blank=True)
    display_end = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    confirmation_message = models.TextField(null=True, blank=True)
    registration_requirements = models.ManyToManyField(ModuleOverview, related_name='registration_modules')
    show_performance_metrics = models.BooleanField(default=False)
    geography_eligiblity = models.ManyToManyField(Organization, related_name='campaign_geography_eligibility')
    position_type = models.CharField(max_length=255, null=True, blank=True)
    registration_eligibility = models.TextField(null=True, blank=True) #json related to minimum thresholds etc. we should just have a points limit though??
    created_by = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(null=True, blank=True)
    performance_points_config = models.ForeignKey('CampaignPointsSettings', null=True, blank=True, on_delete=models.SET_NULL)
    slug = models.SlugField(null=True, blank=True)
    footnotes = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.title)

class CampaignListItem(models.Model):
    campaign = models.ForeignKey(PPCampaign, related_name='list_items', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text

class PPCampaignPaymentPeriod(models.Model):
    campaign = models.ForeignKey(PPCampaign, on_delete=models.SET_NULL, null=True)
    pay_period = models.DateField(null=True, blank=True)
    cutoff = models.DateField(null=True, blank=True)

class PPCampaignRegistration(models.Model):
    campaign = models.ForeignKey(PPCampaign, blank=True, null=True, on_delete=models.SET_NULL)
    employee = models.ForeignKey(Employee, blank=True, null=True, on_delete=models.SET_NULL, related_name='campaign_registration')
    registration_date = models.DateTimeField(null=True, blank=True, default=timezone.now)
    related_employee = models.ForeignKey(Employee, blank=True, null=True, on_delete=models.SET_NULL, related_name='campaign_registration_related_emp')
    communication_opt_in = models.BooleanField(default=False, verbose_name="Opt-in for Communications")

    def __str__(self):
        return f'{self.employee} - {self.campaign}'

class PPCampaignDriverMetricTrackingTable(models.Model):
        employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='campaign_metric_tracking_employee')
        campaign = models.ForeignKey(PPCampaign, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='campaign_metric_tracking_campaign')
        registered = models.BooleanField(default=False)
        date = models.DateField(null=True, blank=True)
        overall_sat = models.FloatField(null=True, blank=True)
        call_volume = models.IntegerField(null=True, blank=True)
        logins = models.IntegerField(null=True, blank=True)
        completed_clips = models.IntegerField(null=True, blank=True)

class PPCampaignBankTransactionLog(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_bank_log_employee')
    campaign = models.ForeignKey(PPCampaign, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_bank_transaction')
    date = models.DateTimeField(null=True, blank=True, default=timezone.now)
    points = models.IntegerField()
    dollars = models.FloatField()
    overall_sat = models.FloatField(null=True, blank=True)
    totally_satisfied_count = models.IntegerField(default=0)
    overall_sat_threshold = models.BooleanField(default=False)

class PPCampaignBank(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_bank_employee')
    campaign = models.ForeignKey(PPCampaign, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_bank')
    total_points = models.IntegerField()
    cashed_points = models.IntegerField()
    cashed_points_dollars = models.FloatField()
    not_cashed_points = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'performance_points_campaignbank'

class PPCampaignPointsBreakdown(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_points_breakdown_employee')
    variable = models.CharField(max_length=255)
    value = models.IntegerField()
    campaign = models.ForeignKey(PPCampaign, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_points_breakdown_campaign')

    class Meta:
        managed = False
        db_table = 'performance_points_campaignpointsbreakdown'

class CampaignPointsSettings(models.Model):
    configuration = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=False)

    class Meta:
        db_table = 'performance_points_settings'
####




class SpringUp2024DriverTable(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    driver_id = models.CharField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    station = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    field_consultant = models.CharField(max_length=255, null=True, blank=True)
    registered = models.CharField(max_length=255, null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    mar_overall_sat = models.FloatField(null=True, blank=True)
    mar_totally_sat_survey = models.IntegerField(null=True, blank=True)
    mar_potential_payment = models.FloatField(null=True, blank=True)
    mar_actual_payment = models.FloatField(null=True, blank=True)
    apr_overall_sat = models.FloatField(null=True, blank=True)
    apr_totally_sat_survey = models.IntegerField(null=True, blank=True)
    apr_potential_payment = models.FloatField(null=True, blank=True)
    apr_actual_payment = models.FloatField(null=True, blank=True)


    may_overall_sat = models.FloatField(null=True, blank=True)
    may_totally_sat_survey = models.IntegerField(null=True, blank=True)
    may_potential_payment = models.FloatField(null=True, blank=True)
    may_actual_payment = models.FloatField(null=True, blank=True)


    june_overall_sat = models.FloatField(null=True, blank=True)
    june_totally_sat_survey = models.IntegerField(null=True, blank=True)
    june_potential_payment = models.FloatField(null=True, blank=True)
    june_actual_payment = models.FloatField(null=True, blank=True)


    july_overall_sat = models.FloatField(null=True, blank=True)
    july_totally_sat_survey = models.IntegerField(null=True, blank=True)
    july_potential_payment = models.FloatField(null=True, blank=True)
    july_actual_payment = models.FloatField(null=True, blank=True)


    august_overall_sat = models.FloatField(null=True, blank=True)
    august_totally_sat_survey = models.IntegerField(null=True, blank=True)
    august_potential_payment = models.FloatField(null=True, blank=True)
    august_actual_payment = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'spring_2024_driver_table'

class CampaignRegistrationStatusView2023(models.Model):
    full_name = models.CharField(max_length=255, null=True, blank=True)
    organization_name = models.CharField(max_length=255, null=True, blank=True)
    facility_rep = models.CharField(max_length=255, null=True, blank=True)
    emp = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_status')
    reg = models.ForeignKey(PPCampaignRegistration, null=True, blank=True, on_delete=models.SET_NULL)
    org = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    registration_date = models.DateField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'CampaignRegistrationStatusView2023'


# class FedDriverPoints(models.Model):
#     is_registered = models.NullBooleanField()
#     date = models.DateField()
#
#     class Meta:
#         managed = False
#         db_table = 'performance_points_fed_driver_points'