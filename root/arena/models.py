import datetime as dt
from django.db.models import F
from accounts.models import *
from django.db import models
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.utils.text import slugify
# from payments.models import TremendousCampaign

# Create your models here.

class Competition(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    display_name = models.CharField(blank=True, null=True, max_length=255)
    updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")

        if not self.display_name:
            try:
                self.display_name = self.name
            except:
                print("Couldnt create a display name!")
        return super(Competition, self).save(*args, **kwargs)

class Conference(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    competition = models.ForeignKey(Competition, null=True, on_delete=models.SET_NULL, related_name='conference')
    display_name = models.CharField(blank=True, null=True, max_length=255)
    updated = models.DateTimeField(null=True, blank=True)

class Division(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    competition = models.ForeignKey(Competition, null=True, on_delete=models.SET_NULL, related_name='division')
    display_name = models.CharField(blank=True, null=True, max_length=255)
    updated = models.DateTimeField(null=True, blank=True)
    conference = models.ForeignKey(Conference, null=True, on_delete=models.SET_NULL, related_name='division')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")

        if not self.display_name:
            try:
                self.display_name = self.name
            except:
                print("Couldnt create a display name!")
        return super(Division, self).save(*args, **kwargs)

class Team(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    logo = models.CharField(blank=True, null=True, max_length=255)
    abbreviation = models.CharField(blank=True, null=True, max_length=100)
    division = models.ForeignKey(Division, null=True, on_delete=models.SET_NULL)
    competition = models.ForeignKey(Competition, null=True, on_delete=models.SET_NULL, related_name='team')
    display_name = models.CharField(blank=True, null=True, max_length=255)
    updated = models.DateTimeField(null=True, blank=True)
    organization_players = models.ManyToManyField(Organization, blank=True)

    def __str__(self):
        return str(self.competition.name) + ": " + str(self.abbreviation)

    def employee_players(self):
        organizations = self.organization_players.all()
        return Employee.objects.filter(organization__in=organizations)

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")

        if not self.display_name:
            try:
                self.display_name = self.name
            except:
                print("Couldnt create a display name!")
        return super(Team, self).save(*args, **kwargs)

    class Meta:
        ordering = ('competition', 'name')

class TeamRanking(models.Model):
    team = models.ForeignKey(Team, null=True, on_delete=models.SET_NULL, related_name='team_rank')
    team_name = models.CharField(blank=True, null=True, max_length=255)
    division = models.CharField(blank=True, null=True, max_length=255)
    competition = models.ForeignKey(Competition, null=True, blank=True, on_delete=models.SET_NULL, related_name='team_rank')
    wins = models.IntegerField(null=True, blank=True) # set by MP
    losses = models.IntegerField(null=True, blank=True) # set by MP
    unplayed = models.IntegerField(null=True, blank=True) # set by MP
    division_rank = models.IntegerField(null=True, blank=True) # set by MP
    overall_rank = models.IntegerField(null=True, blank=True) # set by MP
    total_score = models.FloatField(default=0.0) # set by MP
    updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.team.name)

    # def set_overall_rank(self, competition_id):
    #     for rank, team in enumerate(TeamRanking.objects.filter(competition_id=competition_id).order_by('-wins', '-total_score'), 1):
    #         tr = TeamRanking.objects.get(id=team.id)
    #         tr.overall_rank = rank
    #         tr.save()
    #
    # def set_division_rank(self, competition_id, division_id):
    #     for rank, team in enumerate(TeamRanking.objects.filter(competition_id=competition_id, division_id=division_id).order_by('-wins', '-total_score'), 1):
    #         tr = TeamRanking.objects.get(id=team.id)
    #         tr.division_rank = rank
    #         tr.save()

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")

        if not self.team_name:
            try:
                self.team_name = self.team.name
            except:
                print("Couldnt add a team name!")
        return super(TeamRanking, self).save(*args, **kwargs)

    class Meta:
        ordering = ('competition', 'team_name')

class Round(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    competition = models.ForeignKey(Competition, null=True, on_delete=models.SET_NULL)
    starts = models.DateField(blank=True, null=True)
    ends = models.DateField(blank=True, null=True)
    precursor = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='round_precursor')
    elimination = models.BooleanField(null=True)
    updated = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")
        return super(Round, self).save(*args, **kwargs)

    def all_winners(self):
        matches = Match.objects.filter(round=self.id)
        winners = {}
        for match in matches:
            winners[match.name] = match.winner()
        return winners

    def all_losers(self):
        matches = Match.objects.filter(round=self.id)
        losers = {}
        for match in matches:
            losers[match.name] = match.losers()
        return losers

    def eligible_players(self):
        if self.precursor.elimination:
            return self.precursor.all_winners()
        else:
            return Team.objects.filter(competition=self.competition)

    def is_current_round(self):
        if (dt.date.today() >= self.starts) and (dt.date.today() <= self.ends):
            return True
        else:
            return False

    def get_current_round(self):
        current_rounds = []
        for round in Round.objects.all():
            if round.is_current_round():
                current_rounds.append(round)
        return current_rounds

    def __str__(self):
        return str(self.name) + ' - ' + str(self.starts) + ' TO ' + str(self.ends)

class Match(models.Model):
    # name = models.CharField(blank=True, null=True, max_length=255)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL)
    teams = models.ManyToManyField(Team, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    division = models.ForeignKey(Division, null=True, blank=True, on_delete=models.SET_NULL)
    tournament_match = models.BooleanField(default=False)

    def winner(self):
        scores = list(MatchScores.objects.filter(match_id=self.id).values_list('score',flat=True))
        print("MAX SCORE", scores)
        return MatchScores.objects.get(score=max(scores), match=self.id).team.name

    def losers(self):
        max_score = MatchScores.objects.filter(match_id=self.id).annotate(maxscore=Max('score')).values('score')
        return MatchScores.objects.filter(match=self.id).exclude(score=max_score)

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""

        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")
        return super(Match, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.round) + " : " + " vs ".join(self.teams.all().values_list('name', flat=True))

class ScoreComponent(models.Model):
    label = models.CharField(blank=True, null=True, max_length=255)
    description = models.TextField(blank=True, null=True)
    weight = models.FloatField(null=True, blank=True)
    db_column_name = models.CharField(blank=True, null=True, max_length=255)

    def __str__(self):
        return str(self.name)

class MatchScores(models.Model):
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    score = models.FloatField(null=True, blank=True)
    match = models.ForeignKey(Match, null=True, blank=True, on_delete=models.SET_NULL)
    quarter = models.IntegerField(null=True, blank=True)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL) # redundant but helpful


    def checkForError(self):
        if self.team not in self.match.teams.all():
            raise Exception("This team is not in this contest. Please choose another team!")

    def score_components(self):
        score_components = MatchScoreComponents.objects.filter(match=self.id).annotate(name=F('component__label'), description=F('component__description')).values('name', 'value', 'description')
        return score_components

    def __str__(self):
        return str(self.team) + ' - ' + str(self.match) + ' - ' + str(self.score)


    # add score components here for more information...
    # this table will likely get updated by MP, everything else feeds off of this.

class MatchScoreComponents(models.Model):
    component = models.ForeignKey(ScoreComponent, null=True, blank=True, on_delete=models.SET_NULL)
    match = models.ForeignKey(MatchScores, null=True, blank=True, on_delete=models.SET_NULL)
    value = models.FloatField(null=True, blank=True)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL)


    # add score components here for more information...
    # this table will likely get updated by MP, everything else feeds off of this.

class TeamOrganizationScores(models.Model):
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    score = models.FloatField(null=True, blank=True)
    match = models.ForeignKey(Match, null=True, blank=True, on_delete=models.SET_NULL)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL)
    volume = models.BigIntegerField(null=True, blank=True)
    impact = models.FloatField(null=True, blank=True)

    def score_components(self):
        score_components = TeamOrganizationScoresComponent.objects.filter(team_organization_score=self.id).annotate(name=F('component__label'), description=F('component__description')).values('name', 'value', 'description')
        return score_components

    class Meta:
        index_together = (
            ('organization', 'team', 'match'),
        )


class TeamOrganizationScoresComponent(models.Model):
    component = models.ForeignKey(ScoreComponent, null=True, blank=True, on_delete=models.SET_NULL)
    value = models.FloatField(null=True, blank=True)
    team_organization_scores = models.ForeignKey(TeamOrganizationScores, null=True, blank=True, on_delete=models.SET_NULL)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL)


class TeamEmployeeScores(models.Model):
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    score = models.FloatField(null=True, blank=True)
    match = models.ForeignKey(Match, null=True, blank=True, on_delete=models.SET_NULL)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL)
    volume = models.BigIntegerField(null=True, blank=True)
    impact = models.FloatField(null=True, blank=True)

    def score_components(self):
        score_components = TeamEmployeeScoresComponent.objects.filter(team_employee_score=self.id).annotate(name=F('component__label'), description=F('component__description')).values('name', 'value', 'description')
        return score_components

    class Meta:
        index_together = (
            ('employee', 'team', 'match'),
        )


class TeamEmployeeScoresComponent(models.Model):
    component = models.ForeignKey(ScoreComponent, null=True, blank=True, on_delete=models.SET_NULL)
    value = models.FloatField(null=True, blank=True)
    team_employee_scores = models.ForeignKey(TeamEmployeeScores, null=True, blank=True, on_delete=models.SET_NULL)
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL)

class SkillTreeDriverTeam(models.Model):
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

class SkillTreePlayerSkills(models.Model):
    skill_level =  models.IntegerField(null=True, blank=True)
    skill_level_max = models.IntegerField(null=True, blank=True)
    skill_level_min = models.IntegerField(null=True, blank=True)
    skill_name = models.TextField(null=True, blank=True)
    tenure_average = models.FloatField(null=True, blank=True)
    value = models.IntegerField(null=True, blank=True)

class SkillTreePlayer(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    team = models.ForeignKey(SkillTreeDriverTeam, null=True, blank=True, on_delete=models.SET_NULL)
    employee_name = models.TextField(null=True, blank=True)
    org_name = models.TextField(null=True, blank=True)
    org_id = models.IntegerField(null=True, blank=True)
    start_date = models.TextField(null=True, blank=True)
    tenure_group = models.TextField(null=True, blank=True)
    skills = models.ManyToManyField(SkillTreePlayerSkills, related_name='skills')


class hh5_drivers(models.Model):
    # employee = models.ForeignKey(Employee, null=True, blank=True, related_name="hh5_driver_employee",  on_delete=models.SET_NULL)
    driver_name = models.CharField(max_length=255, null=True, blank=True)
    org = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    station_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    date_joined = models.DateTimeField(null=True, blank=True)
    registered = models.BooleanField(null=True)
    registered_email = models.EmailField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    registration_time = models.DateTimeField(null=True, blank=True)
    reward_type = models.CharField(max_length=255, null=True, blank=True)
    registration_group = models.CharField(max_length=255, null=True, blank=True)
    hh5_station_cohort = models.CharField(max_length=255, null=True, blank=True)


    class Meta:
        managed = False
        db_table = 'hh5_drivers'

    @property
    def driver_employee_id(self):
        return self.employee.id

    @property
    def territory(self):
        org_ = self.org
        territory = org_.get_parent_to('Territory')
        return territory.name

    def get_territory(self):
        org_ = self.org
        territory = org_.get_parent_to('Territory')
        return territory.name

    def email_core_hh5_extension_email(self):
        message = render_to_string('campaigns/hh5_extension_email.html', {
            'first_name': self.employee.first_name,
            'last_name': self.employee.last_name,
            # 'domain': settings.FRONT_END_DOMAIN,  # TODO: change the domain
            'employee_id': str(self.employee_id)
        })
        print("SENT INVITE EMAIL TO: ", self.email)
        to_email = self.email
        # to_email = 'jesus.diaz.barriga@thedgcgroup.com'
        mail_subject = "HH5 Program ACA Driver Award Program has been extended!"
        email = EmailMessage(mail_subject, message, 'AAAHolidayHigh5.noreply@wageup.com',
                             to=[to_email, 'help@wageup.com'])
        email.send()

    def email_campaign_invite(self):
        campaigns = {
            'hh5': {'invite': 'campaigns/hh5_invite.html', 'subject': 'Holiday High 5! ACA Driver Award Program',
                    'send_email': 'AAAHolidayHigh5.noreply@wageup.com'},
            'cold_rush1': {'invite': 'campaigns/cold_rush_invite.html',
                           'subject': 'Cold Rush! ACA Driver Award Program',
                           'send_email': 'AAAColdRush.noreply@wageup.com'},
            'cold_rush2': {'invite': 'campaigns/cold_rush_second_invite.html',
                           'subject': 'Cold Rush! ACA Driver Award Program',
                           'send_email': 'AAAColdRush.noreply@wageup.com'},
            'cold_rush3': {'invite': 'campaigns/cold_rush_third_invite.html',
                           'subject': 'Cold Rush! ACA Driver Award Program',
                           'send_email': 'AAAColdRush.noreply@wageup.com'}
        }
        camp = 'cold_rush2'
        message = render_to_string(campaigns[camp]['invite'], {
            'first_name': self.employee.first_name,
            'last_name': self.employee.last_name,
            # 'domain': settings.FRONT_END_DOMAIN,  # TODO: change the domain
            'employee_id': str(self.employee_id)
        })
        print("SENT INVITE EMAIL TO: ", self.email)
        to_email = self.email
        # to_email = 'jesus.diaz.barriga@thedgcgroup.com'
        mail_subject = campaigns[camp]['subject']
        email = EmailMessage(mail_subject, message, campaigns[camp]['send_email'], to=[to_email, 'help@wageup.com'])
        email.send()

    def email_campaign_invite_using_registration_email(self):
        campaigns = {
            'hh5': {'invite': 'campaigns/hh5_invite.html', 'subject': 'Holiday High 5! ACA Driver Award Program', 'send_email': 'AAAHolidayHigh5.noreply@wageup.com'},
            'cold_rush1': {'invite': 'campaigns/cold_rush_invite.html', 'subject': 'Cold Rush! ACA Driver Award Program', 'send_email': 'AAAColdRush.noreply@wageup.com'},
            'cold_rush2': {'invite': 'campaigns/cold_rush_second_invite.html',
                           'subject': 'Cold Rush! ACA Driver Award Program',
                           'send_email': 'AAAColdRush.noreply@wageup.com'},
            'cold_rush3': {'invite': 'campaigns/cold_rush_third_invite.html',
                           'subject': 'Cold Rush! ACA Driver Award Program',
                           'send_email': 'AAAColdRush.noreply@wageup.com'}
        }
        camp = 'cold_rush2' # change this to change email template
        message = render_to_string(campaigns[camp]['invite'], {
            'first_name': self.employee.first_name,
            'last_name': self.employee.last_name,
            # 'domain': settings.FRONT_END_DOMAIN,  # TODO: change the domain
            'employee_id': str(self.employee_id)
        })
        print("SENT INVITE EMAIL TO: ", self.email)
        to_email = self.registered_email
        # to_email = 'jesus.diaz.barriga@thedgcgroup.com'
        mail_subject = campaigns[camp]['subject']
        email = EmailMessage(mail_subject, message, campaigns[camp]['send_email'], to=[to_email, 'help@wageup.com'])
        email.send()


class hh5_drivers_sat_statistics(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True, null=False, blank=False)
    # employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, related_name="hh5_drivers_employee", db_column='employee_id', null=True, blank=False)
    tech_id = models.CharField(db_column='login_id', null=True, blank=True, max_length=255)
    station_name = models.CharField(db_column='station_name', max_length=255, null=True, blank=True)
    registered = models.BooleanField(db_column='registered', null=True, blank=True)
    id_name_helper = models.CharField(db_column='driver_name', max_length=255, null=True, blank=True)
    call_volume = models.IntegerField(db_column='call_volume', null=True, blank=True)


    base_size_sat_overall = models.IntegerField(db_column='base_size_sat_overall', null=True, blank=True)
    count_overall_totly_stsfd = models.IntegerField(db_column='count_overall_totly_stsfd', null=True, blank=True)
    pcnt_overall_totly_stsfd = models.FloatField(db_column='pcnt_overall_totly_stsfd', null=True, blank=True)

    base_size_driver = models.IntegerField(db_column='base_size_driver', null=True, blank=True)
    count_driver_totly_stsfd = models.IntegerField(db_column='count_driver_totly_stsfd', null=True, blank=True)
    pcnt_driver_totly_stsfd = models.FloatField(db_column='pcnt_driver_totly_stsfd', null=True, blank=True)

    pcnt_kept_informed_totly_stsfd = models.FloatField(db_column='pcnt_kept_informed_totly_stsfd', null=True, blank=True)
    pcnt_driver_contct = models.FloatField(db_column='pcnt_driver_contact', null=True, blank=True)

    def get_driver_username(self):
        employee = Employee.objects.get(id=self.employee_id)
        try:
            return employee.user.username
        except:
            return self.tech_id

    def get_driver_territory(self):
        organization = Organization.objects.filter(name=self.station_name)[0]
        territory = organization.get_parent_to('Territory')
        return territory.name

    def registration_group(self):
        driver = hh5_drivers.objects.get(employee_id=self.id)
        return driver.registration_group

    class Meta:
        managed = False
        db_table = 'hh5_driver_sat_statistics'


class hh5_driver_sat_extended(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True, null=False, blank=False)
    # employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, related_name='hh5_employee_sat_ext', null=True, blank=True, db_column='employee_id')
    login_id = models.CharField(db_column='login_id', max_length=255, null=True, blank=True)
    g1_base_size = models.IntegerField(db_column='Nov 9 - Feb 28 group_1_base_size_sat_overall', null=True, blank=True)
    g1_count = models.IntegerField(db_column='Nov 9 - Feb 28 group_1_count_overall_totly_stsfd', null=True, blank=True)
    g1_pcnt = models.IntegerField(db_column='Nov 9 - Feb 28 group_1_pcnt_overall_totly_stsfd', null=True, blank=True)
    g2_base_size = models.IntegerField(db_column='Dec 1 - Feb 28 group_2_base_size_sat_overall', null=True, blank=True)
    g2_count = models.IntegerField(db_column='Dec 1 - Feb 28 group_2_count_overall_totly_stsfd', null=True, blank=True)
    g2_pcnt = models.IntegerField(db_column='Dec 1 - Feb 28 group_2_pcnt_overall_totly_stsfd', null=True, blank=True)
    g3_base_size = models.IntegerField(db_column='Jan 1 - Feb 28 group_3_base_size_sat_overall', null=True, blank=True)
    g3_count = models.IntegerField(db_column='Jan 1 - Feb 28 group_3_count_overall_totly_stsfd', null=True, blank=True)
    g3_pcnt = models.IntegerField(db_column='Jan 1 - Feb 28 group_3_pcnt_overall_totly_stsfd', null=True, blank=True)
    g4_base_size = models.IntegerField(db_column='Feb 1 - Feb 28 group_4_base_size_sat_overall', null=True, blank=True)
    g4_count = models.IntegerField(db_column='Feb 1 - Feb 28 group_4_count_overall_totly_stsfd', null=True, blank=True)
    g4_pcnt = models.IntegerField(db_column='Feb 1 - Feb 28 group_4_pcnt_overall_totly_stsfd', null=True, blank=True)
    dec_group_base = models.IntegerField(db_column='Dec 11 - Dec 31 base_size_sat_overall', null=True, blank=True)
    dec_group_count = models.IntegerField(db_column='Dec 11 - Dec 31 count_overall_totly_stsfd', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'hh5_expansion_driver_sat_statistics_revised'

# Todo: Complete this model (CampaignType)
class CampaignType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class CampaignMetrics(models.Model):
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, null=True, blank=True)
    key_site = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    filter = models.CharField(max_length=255, null=True, blank=True)
    annotate = models.CharField(max_length=255, null=True, blank=True)
    show_on_site_options = models.BooleanField(default=False)
    agg_metric = models.CharField(max_length=255, null=True, blank=True)
    agg_type = models.CharField(max_length=255, null=True, blank=True)
    templated = models.BooleanField(default=False)

    def __str__(self):
        return self.key

class DriverCampaign(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(null=True, blank=True)
    image = models.FileField(null=True, blank=True)
    info_file = models.FileField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True, verbose_name='App Notes')
    rdb_site_notes = models.TextField(null=True, blank=True)
    app_site_notes = models.TextField(null=True, blank=True)
    show_rewards_top_slot = models.BooleanField(default=True)
    show_rewards_bottom_slot = models.BooleanField(default=True)
    rewards_top_slot_title = models.TextField(null=True, blank=True)
    rewards_bottom_slot_title = models.TextField(null=True, blank=True)
    rewards_top_slot_metric = models.ForeignKey(CampaignMetrics, null=True, blank=True, on_delete=models.SET_NULL, related_name='rewards_top_slot_metric')
    rewards_bottom_slot_metric = models.ForeignKey(CampaignMetrics, null=True, blank=True, on_delete=models.SET_NULL, related_name='rewards_bottom_slot_metric')
    metrics = models.ManyToManyField(CampaignMetrics, blank=True, verbose_name='Metrics needed for App', related_name='metrics_for_app')
    site_metrics = models.ManyToManyField(CampaignMetrics, blank=True, verbose_name='Metrics to display in the RDB site', related_name='metrics_for_rdb_site')
    campaign_type = models.ForeignKey(CampaignType, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_type')
    active = models.BooleanField(default=True)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    payment_converter = models.TextField(null=True, blank=True) #json
    payout_converter = models.TextField(null=True, blank=True) #json
    pay_cap = models.IntegerField(db_column='pay_period_cap', default=10000)
    # tremendous_campaign = models.ForeignKey(TremendousCampaign, null=True, blank=True, on_delete=models.SET_NULL, related_name='tremendous_campaign')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify((str(self.id) + '-' + self.title))
        super(DriverCampaign, self).save(*args, **kwargs)

class CampaignEligibility(models.Model):
    campaign = models.ForeignKey(DriverCampaign, null=True, blank=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)

class PayPeriod(models.Model):
    name = models.CharField(max_length=255)
    upload_from_date = models.DateField(null=True, blank=True)
    upload_to_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    campaign = models.ForeignKey(DriverCampaign, on_delete=models.SET_NULL, null=True, blank=True)
    updated = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name

class RegistrationCohort(models.Model):
    name = models.CharField(max_length=255)
    start = models.DateTimeField(null=True, blank=True, verbose_name='Service event Start')
    registration_start = models.DateTimeField(null=True, blank=True, help_text='The start date and time of this cohort. Anyone registering starting at this date and time will be placed on this cohort.')
    end = models.DateTimeField(null=True, blank=True, verbose_name='Registration End Date', help_text='Select the day after the last day of the registration with the time 00:00:00. This means anyone registered UP TO this date and time will be on this cohort.')
    notes = models.TextField(null=True, blank=True)
    campaign = models.ForeignKey(DriverCampaign, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class DriverPayments(models.Model):
    driver = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.DecimalField(max_digits=6, decimal_places=2)
    already_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    paid_on = models.DateTimeField(null=True, blank=True)
    registration_group = models.ForeignKey(RegistrationCohort, null=True, blank=True, on_delete=models.SET_NULL)
    pay_period = models.ForeignKey(PayPeriod, null=True, blank=True, on_delete=models.SET_NULL)
    updated_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        driver = self.driver.display_name
        if self.already_paid:
            return f"{driver}: was paid {self.payment} on {self.paid_on}"
        else:
            return f"{driver}: is expected to be paid {self.payment} for {self.pay_period.name}"

class PaymentFactors(models.Model):
    driver = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    count = models.IntegerField(default=0)
    payment_value = models.FloatField(null=True, blank=True)
    upload_from_date = models.DateField(null=True, blank=True)
    upload_to_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    driver_payment = models.ForeignKey(DriverPayments, on_delete=models.SET_NULL, null=True, blank=True)


class DriverCampaignRegistration(models.Model):
    driver = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    campaign = models.ForeignKey(DriverCampaign, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_payment_method = models.CharField(max_length=100, null=True, blank=True)
    registration_date = models.DateTimeField(null=True, blank=True)
    registration_cohort = models.ForeignKey(RegistrationCohort, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        campaign = self.campaign.title
        driver = self.driver.display_name
        return f"{campaign} : {driver}"

class CampaignRegistrationStatus(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True, null=False, blank=False)
    campaign_title = models.CharField(db_column='title', max_length=255, null=True, blank=True)
    driver_name = models.CharField(db_column='full_name', max_length=255, null=True, blank=True)
    driver = models.ForeignKey(Employee, db_column='driver_employee_id', on_delete=models.SET_NULL, null=True,
                               blank=True)
    raw_data_driver_id = models.IntegerField(db_column='raw_data_driver_id', null=True, blank=True, verbose_name='NE Driver ID')
    organization = models.CharField(db_column='name', max_length=255, null=True, blank=True)
    territory = models.CharField(db_column='territory', max_length=255, null=True, blank=True)
    field_consultant = models.CharField(db_column='field_consultant_name', max_length=255, null=True, blank=True)
    email = models.CharField(db_column='email', max_length=255, null=True, blank=True)
    username = models.CharField(db_column='username', max_length=255, null=True, blank=True)
    date_joined = models.DateField(db_column='date_joined', null=True, blank=True)
    last_login = models.DateField(db_column='last_login', null=True, blank=True)
    is_registered = models.BooleanField(db_column='is_registered', null=True, blank=True)
    registration_date = models.DateField(db_column='registration_date', null=True, blank=True)
    cohort_name = models.CharField(db_column='registration_cohort_name', max_length=255, null=True, blank=True)
    preferred_payment_method = models.CharField(db_column='preferred_payment_method', max_length=255, null=True, blank=True)


    class Meta:
        managed = False
        db_table = 'CampaignRegistrationStatusView'
# class DriverCampaignMetrics(models.Model):
#     campaign = models.ForeignKey(DriverCampaign, on_delete=models.SET_NULL, null=True, blank=True)
#     driver = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
#     title = models.CharField(max_length=255, blank=True, null=True)
#     value = models.CharField(max_length=255, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         # db_table = ''

class DriverCampaignExclusion(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)