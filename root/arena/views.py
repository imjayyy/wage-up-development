from django.shortcuts import render
import sys

sys.path.insert(0, 'root')
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework_simplejwt import serializers as jwt_serializers
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .serializers import *
from django.contrib.auth.models import User
import datetime as dt
from rest_framework.parsers import JSONParser
from .models import *
from django.db.models import Q

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render
from django.db.models import Avg, Count, Sum, Min, Max
from dashboard.models import Std12EReduced, DashboardAggregations
from accounts.models import Organization
from django.db.models import F, ExpressionWrapper, FloatField
from dashboard.dashboardUtilities import generate_biz_rules_annotation
import random
import itertools
from dateutil import parser
from collections import defaultdict
from root.utilities import combine_dicts
import json
from .campaign_metrics import CampaignMetricsHelper

# Create your views here.

class Arena(generics.GenericAPIView):
    """
        Take as post input:
        :type - i.e. driver, employee, market, grid etc.
        slug - what is the slug of the object. i.e. devin-gonier, vadc
        purpose - what function should be called -- i.e. line_graph, scatterplot etc.
    """

    permission_classes = (IsAuthenticated,)

    serializer_class = None

    www_authenticate_realm = 'api'

    def __init__(self):
        self.user_team = None
        self.user = None
        self.parameters = None
        self.data = None
        self.user_team_data = None
        self.request = None
        self.purpose_router = {
            'get_schedule': self.get_schedule,
            'get_team': self.get_team,
            'get_match_history': self.get_match_history,
            'org_player_scores': self.get_org_player_scores,
            'get_bracket': self.get_bracket,
            'skill_tree_add_player_to_team': self.skill_tree_add_player_to_team,
            'skill_tree_get_team_players': self.skill_tree_get_team_players,
            'campaign': self.driver_campaign,
            'campaign_registration': self.campaign_registration,
            'registration_check': self.registration_check,
            'campaign_list': self.campaign_list,
            'get_campaign': self.get_campaign,
            'get_campaign_orgs': self.get_campaign_orgs,
            'get_registration_driver_list': self.get_registration_driver_list,
            'get_registered_data_with_payperiod': self.get_registered_data_with_payperiod
        }
        self.campaign_views = ['campaign', 'campaign_registration', 'registration_check', 'get_campaign']

    def post(self, request, *args, **kwargs):
        data = request.data
        self.data = request.data
        self.parameters = self.data['parameters']
        self.user = self.request.user
        self.request = request
        print(self.data['purpose'])

        if self.data.get('purpose') not in self.campaign_views:
            if self.user.employee().permission.filter(name="see-arena").count() == 0:
                return Response("NOT ALLOWED", status=status.HTTP_403_FORBIDDEN)

        if self.data['purpose'] == 'get_teams':
            return Response(self.get_team(), status=status.HTTP_200_OK)

        output = self.purpose_router[self.data['purpose']]()

        return Response(output, status=status.HTTP_200_OK)

    def get_team(self):
        if self.data['purpose'] == 'get_teams':
            if "division" in self.data['parameters']:
                teams = Team.objects.filter(division__name=self.data['parameters']['division'])
                return TeamSerializer(teams, many=True).data
            elif "conference" in self.data['parameters']:
                teams = Team.objects.filter(division__conference__name=self.data['parameters']['conference'])
                return TeamSerializer(teams, many=True).data
            else:
                teams = Team.objects.all()
                return TeamSerializer(teams, many=True).data

        try:
            user_org = self.user.employee().organization
            self.user_team = Team.objects.get(organization_players__in=[user_org])
            self.user_team_data = TeamSerializer(self.user_team).data
            print("USERS TEAM", self.user_team)
            return self.user_team_data
        except:
            print("Generating random team")
            teams = Team.objects.all()
            random_team = random.choice(teams)
            return TeamSerializer(random_team).data

    def get_schedule(self):
        parameters = self.parameters
        if "team_abbreviation" in parameters:
            team = Team.objects.get(abbreviation=parameters['team_abbreviation'].upper())
            print(team)
        else:
            self.get_team()
            team = self.user_team
        if "show_all" not in parameters:
            matches = Match.objects.filter(teams__in=[team]).order_by('round__starts')
        else:
            team = False
            matches = Match.objects.all()

        print(matches)
        output = MatchShortSerializer(matches, many=True).data
        # print(output)
        teams_only = []
        if 'exclude_self' in parameters:
            for round in range(len(output)):
                print("TEAMS", output[round]['teams'])
                for t in range(len(output[round]['teams'])):
                    if team:
                        if (output[round]['teams'][t]['id'] == team.id):
                            output[round]['teams'][t] = "SELF"
                output[round]['teams'] = [x for x in output[round]['teams'] if x != 'SELF']
                teams_only.append(
                    {
                        "round": output[round]['round'],
                        "teams": output[round]['teams']
                    }
                )
        else:
            for round in range(len(output)):
                teams_only.append(
                    {
                        "round": output[round]['round'],
                        "teams": output[round]['teams']
                    }
                )

        if 'minimal' in parameters:
            if team:
                output = {
                    "team": TeamShortSerializer(team).data,
                    "division": output[0]['division']['name'],
                    "schedule": teams_only
                }
            else:
                output = teams_only

        return output

    def get_match_history(self):
        parameters = self.parameters
        team = Team.objects.get(abbreviation=parameters['team_abbreviation'])
        matches = Match.objects.filter(teams__in=[team])
        match_scores = MatchScores.objects.filter(match__in=matches)
        print(match_scores)
        output = MatchScoreShortSerializer(match_scores, many=True).data
        print(output)

        #group by rounds:
        final_out = []
        rounds = {}
        for o in output:
            round_id = o['round']['id']
            winner = o['match']['match_winner']
            team_dict = o['team']
            team_dict['score'] = o['score']
            team_dict['score_component'] = o['score_component']
            round_dict = {
                'starts': o['round']['starts'],
                'ends': o['round']['ends'],
                'quarter': o['quarter'],
                'id': round_id
            }
            if round_id in rounds:
                rounds[round_id]['round'] = round_dict
                rounds[round_id]['teams'].append(team_dict)
            else:
                rounds[round_id] = {}
                rounds[round_id]['round'] = round_dict
                rounds[round_id]['teams'] = []
                rounds[round_id]['teams'].append(team_dict)
                rounds[round_id]['winner'] = winner

        for k, v in rounds.items():
            final_out.append(v)

        return final_out

    def get_bracket(self):
        parameters = self.parameters
        relevant_matches = Match.objects.filter(tournament_match=True)
        print(relevant_matches)
        match_scores = MatchScores.objects.filter(match__in=relevant_matches).annotate(name=F('team__name'),
                                                                                       logo=F('team__logo'),
                                                                                       abbreviation=F('team__abbreviation'),
                                                                                       display_name=F('team__display_name'),
                                                                                       ).values('score', 'round', 'quarter', 'name', 'logo', 'abbreviation', 'display_name', 'match__id')
        if not match_scores:
            return False
        output = {
            'quarterfinals': [],
            'semifinals': [],
            'finals': [],
        }

        quarter = 0

        for match_id, matches in itertools.groupby(match_scores, lambda item: item["match__id"]):
            match_list = list(matches)
            if match_list[0]['round'] == 6:
                output['quarterfinals'].append(match_list)
                quarter = match_list[0]['quarter']
            if match_list[0]['round'] == 7:
                output['semifinals'].append(match_list)
                quarter = match_list[0]['quarter']
            if match_list[0]['round'] == 8:
                output['finals'].append(match_list)
                quarter = match_list[0]['quarter']

        unknown_dict = {
            'score': "--",
            "name": "Unknown",
            "logo": "unknown.png",
            "abbreviation": 'UNK',
            "display_name": "Unknown",
        }

        if not output['semifinals']:
            for i in range(2):
                output['semifinals'].append([unknown_dict, unknown_dict])

        if not output['finals']:
            output['finals'].append([unknown_dict, unknown_dict])

        return [quarter, output]

    def get_org_player_scores(self):
        parameters = self.parameters
        team = Team.objects.get(abbreviation=parameters['team_abbreviation'])
        org_scores = TeamOrganizationScores.objects.filter(team=team).values_list('id', flat=True)
        org_component_scores = TeamOrganizationScoresComponent.objects.filter(
            team_organization_scores_id__in=org_scores).annotate(
            # team_organization_scores_id__in=org_scores).annotate(
            team=F('team_organization_scores__team__name'),
            name=F('team_organization_scores__organization__name'),
            type=F('team_organization_scores__organization__type'),
            slug=F('team_organization_scores__organization__slug'),
            round_name=F('team_organization_scores__round__name'),
            score=F('team_organization_scores__score'),
            # impact=F('team_organization_scores__impact'),
            # volume=F('team_organization_scores__volume'),
            score_component_label=F('component__label'),
            score_component_value=F('value'),
        ).order_by('team_organization_scores_id').values('team', 'name', 'type','slug','round','score','score_component_label','score_component_value', 'team_organization_scores_id')
        emp_scores = TeamEmployeeScores.objects.filter(team=team).values_list('id', flat=True)
        emp_component_scores = TeamEmployeeScoresComponent.objects.filter(
            team_employee_scores_id__in=emp_scores).annotate(
            team=F('team_employee_scores__team__name'),
            name=F('team_employee_scores__employee__full_name'),
            type=F('team_employee_scores__employee__position_type'),
            slug=F('team_employee_scores__employee__slug'),
            round_name=F('team_employee_scores__round__name'),
            score=F('team_employee_scores__score'),
            # impact=F('team_employee_scores__impact'),
            # volume=F('team_employee_scores__volume'),
            score_component_label=F('component__label'),
            score_component_value=F('value')).order_by('team_employee_scores_id').values('team', 'name', 'type', 'slug', 'round', 'score', 'score_component_label', 'score_component_value', 'team_employee_scores_id')

        # flatten arrays
        emp_output = []
        for match_id, matches in itertools.groupby(list(emp_component_scores), lambda item: item["team_employee_scores_id"]):
            m = list(matches)
            object = {
                'team': m[0]['team'],
                'name': m[0]['name'],
                'type': m[0]['type'],
                'slug': m[0]['slug'],
                'score': m[0]['score'],
                'round': m[0]['round']
            }
            # for mat in m:
                # object[mat['score_component_label']] = mat['score_component_value']
            emp_output.append(object)

        org_output = []
        # return org_component_scores
        for match_id, matches in itertools.groupby(org_component_scores, lambda item: item["team_organization_scores_id"]):
            m = list(matches)
            object = {
                'team': m[0]['team'],
                'name': m[0]['name'],
                'type': m[0]['type'],
                'slug': m[0]['slug'],
                'score': m[0]['score'],
                'round': m[0]['round']
            }

            if object["type"] == 'Territory':
                print(object, m)
            # for component in m:
                # print(component['score_component_label'], component['score_component_value'])
                # object[component['score_component_label']] = component['score_component_value']
            org_output.append(object)

        output = list(org_output) + list(emp_output)
        
        return output

    def skill_tree_add_player_to_team(self):
        parameters = self.parameters
        team, created = SkillTreeDriverTeam.objects.get_or_create(
            owner = self.user
        )

        player = SkillTreePlayer.objects.create(
            team = team,
            employee_id = parameters.get("employee_id"),
            employee_name = parameters.get("employee_name"),
            org_name = parameters.get("org_name"),
            org_id = parameters.get("org_id"),
            start_date = parameters.get("start_date"),
            tenure_group=parameters.get("tenure_group"),
            skills = parameters.get("skills")

        )

        # return {
        #     "team": team.id,
        #     "players": SkillTreePlayer.objects.filter(team=team).values("employee__display_name", "employee__position_type")
        # }


        player.save()
        output = SkillTreePlayerSerializer(player).data
        return output

    def skill_tree_get_team_players(self):
        parameters = self.parameters
        team = SkillTreePlayer.objects.filter(team__owner=self.user.id)
        output = SkillTreePlayerSerializer(team, many=True).data
        return output

    def campaign_list(self):
        employee = self.user.employee()
        org = employee.organization
        stations = org.lineage('Station')
        elegible_campaigns = CampaignEligibility.objects.filter(organization__in=stations, campaign__active=True)\
            .values('campaign')\
            .annotate(campaign_id=F('campaign_id'))\
            .values_list('campaign_id', flat=True)
        campaigns = DriverCampaign.objects.filter(active=True, id__in=elegible_campaigns).values('id', 'title', 'slug')

        return campaigns

    def get_campaign_orgs(self):
        campaign = DriverCampaign.objects.get(slug=self.data.get('slug'))
        org_type = self.data.get('org_type', 'org_svc_facl_id')
        orgs = CampaignEligibility.objects.filter(campaign=campaign)

        surveys = Std12EReduced.objects.filter(is_valid_record=True,
                                               sc_dt_surveys__gte=campaign.start,
                                               sc_dt_surveys__lt=campaign.end,
                                               org_svc_facl_id__in=orgs.values_list('organization', flat=True))\
            .filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1))).values(org_type)
        survey = surveys.annotate(
            name=F(f'{org_type}__name'),
            id=F(org_type),
            osat_base = Count('overall_sat'),
            osat = Avg('overall_sat'),
            rt_sat = Avg('response_sat'),
            kmi_sat = Avg('kept_informed_sat')
        )

        ops = DashboardAggregations.objects.filter(sc_dt__gte=campaign.start,
                                                   time_type='D',
                                                   organization_id__in=[x['id'] for x in survey],
                                                   ).values('organization_id')
        ops = ops.annotate(
            id=F('organization_id'),
            ata_median=Avg('ata_median'),
            pta_median=Avg('pta_median'),
            ata_minus_pta_median=Avg('ata_minus_pta_median'),
            long_freq=ExpressionWrapper(Sum('long_ata_count') / Count('long_ata_count'), output_field=FloatField()),
            late_freq=ExpressionWrapper(Sum('late_count') / Count('late_count'), output_field=FloatField())
        )

        self.percentages = ['long_freq', 'late_freq', 'osat', 'rt_sat', 'kmi_sat']
        self.floats = ['ata_median', 'pta_median', 'ata_minus_pta_median']
        self.exclude = ['id', 'org_svc_facl_id', 'organization_id', 'org_business_id', 'emp_driver_id']
        return self.clean_output(combine_dicts([survey, ops], 'id')),


    def clean_output(self, out, percentages=[], floats=[], exclude=[]):
        if type(out) == list:
            return list(map(self.clean_output, out))
        else:
            row = []
            for k, v in out.items():
                if k in self.exclude:
                    continue
                if k in self.percentages:
                    v = round(out[k]*100, 2) if out[k] is not None else None
                if k in self.floats:
                    v = round(out[k], 2) if out[k] is not None else None
                row.append({
                    "label": k,
                    "value": v
                })
            return {'rowLink': '#', 'data': row}

    def get_campaign(self):
        slug = self.data.get('slug')
        campaign = DriverCampaign.objects.get(slug=slug)
        print(campaign.start)
        print(campaign.end)
        self.campaign = campaign
        org = Organization.objects.get(id=self.user.employee().organization_id)
        if org.type != 'Station-Business':
            stations = org.lineage('Station-Business')
            stations = Organization.objects.filter(id__in=stations).values_list('id', flat=True)
        else:
            stations = [org.id]
        registered = DriverCampaignRegistration.objects.filter(campaign_id=campaign.id, driver__organization__id__in=stations)\
            .annotate(username=F('driver__user__username'),
                      drive_namer=F('driver__full_name'),
                      station_name=F('driver__organization__name'),
                      territory=F('driver__organization__parent__name'),
                      registration_group=F('registration_cohort__name'))\
            # .values('username', 'driver_id', 'driver__full_name', 'station_name', 'territory', 'registration_group', 'registration_date', 'registration_cohort__id')

        # for r in registered:
        #     r['station_name'] = Organization.objects.get(id=r['station_name']).children()[0].name
        today = dt.datetime.today()
        pay_periods = PayPeriod.objects.filter(campaign=campaign).values('id', 'name', 'upload_from_date', 'upload_to_date')
        campaign_cohorts = RegistrationCohort.objects.filter(campaign_id=campaign.id).order_by('start')
        reg_drivers_and_metrics = []
        if self.data.get('pay_period'):
            self.pay_period = PayPeriod.objects.get(id=self.data.get('pay_period'))
        else:
            try:
                self.pay_period = PayPeriod.objects.get(upload_from_date__lte=today,
                                                                upload_to_date__gt=today,
                                                                campaign=self.campaign)
            except:
                self.pay_period = PayPeriod.objects.filter(campaign=campaign).last()

        print('pay period is', self.pay_period, self.pay_period.upload_from_date,self.pay_period.upload_to_date,)
        if self.user.employee().position_type != 'Driver':
            for c in campaign_cohorts:
                print(c)
                print(c.start)
                driver_d = ['emp_driver_id', 'username', 'driver_id', 'driver__full_name', 'station_name', 'territory', 'registration_group', 'registration_date', 'registration_cohort__id', 'driver__raw_data_driver_id']
                registered_f = registered.filter(registration_cohort__id = c.id).annotate(emp_driver_id=F('driver_id')).values(*driver_d)
                surveys = Std12EReduced.objects.filter(is_valid_record=True,
                                                       date_updated_surveys__gte=self.pay_period.upload_from_date,
                                                       date_updated_surveys__lt=self.pay_period.upload_to_date,
                                                       sc_dt_surveys__gte=c.start,
                                                       sc_dt_surveys__lt=campaign.end,
                                                       emp_driver_id__in=[x['driver_id'] for x in registered_f]).filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))
                reg_drivers_and_metrics = reg_drivers_and_metrics + combine_dicts([registered_f, self.get_metrics_for_site(surveys, c.start, campaign.end, group_on='emp_driver_id')], 'emp_driver_id')
                # [i.update({'driverMetrics': []}) for i in reg_drivers_and_metrics if 'driverMetrics' not in i]
                # print('rest of cohort', list([x for x in campaign_cohorts if x.id != c.id]))
                # for j in list([x for x in campaign_cohorts if x.id != c.id]):
                j_start_date = c.start.strftime('%b %d')
                j_end_date = (campaign.end - dt.timedelta(days=1)).strftime('%b %d')
                j_need_to_add = self.blank_metrics_for_site(j_start_date, j_end_date)


                [i.update({'driverMetrics': j_need_to_add}) for i in reg_drivers_and_metrics if 'driverMetrics' not in i]

                for i in reg_drivers_and_metrics:
                    if i['registration_cohort__id'] != c.id:
                        [i['driverMetrics'].append(j) for j in j_need_to_add if j not in i['driverMetrics']]
        else:
            reg_driver_one = DriverCampaignRegistration.objects.filter(campaign_id=campaign.id, driver=self.user.employee())\
                .annotate(username=F('driver__user__username'),
                          drive_namer=F('driver__full_name'),
                          station_name=F('driver__organization__name'),
                          territory=F('driver__organization__parent__name'),
                          registration_group=F('registration_cohort__name'))\
                .values('username', 'driver_id', 'driver__full_name', 'station_name', 'territory', 'registration_group', 'registration_date', 'registration_cohort__id', 'driver__raw_data_driver_id')
            print(reg_driver_one)
            if reg_driver_one.count() > 0:
                reg_driver = reg_driver_one[0]
                reg_driver['driverMetrics'] = []
                cohort = RegistrationCohort.objects.get(id=reg_driver['registration_cohort__id'])
                print(cohort.start, cohort.end)
                surveys = Std12EReduced.objects.filter(is_valid_record=True,
                                                       date_updated_surveys__gte=cohort.start,
                                                       date_updated_surveys__lt=campaign.end,
                                                       sc_dt_surveys__gte=cohort.start,
                                                       sc_dt_surveys__lt=campaign.end,
                                                       emp_driver_id=reg_driver['driver_id'])\
                    .filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))
                print(surveys.values('reroute', 'sc_dt_surveys', 'overall_sat'))
                reg_driver['driverMetrics'].append(self.get_metrics_for_site(surveys, cohort.start, campaign.end))
                reg_drivers_and_metrics.append(reg_driver)


        campaign_output = {
            'title': campaign.title,
            'slug': campaign.slug,
            'image': None,
            'info_file': None,
            'notes': campaign.rdb_site_notes,
            'start': campaign.start,
            'end': campaign.end
        }
        if campaign.image:
            campaign_output['image'] = campaign.image.url

        if campaign.info_file:
            campaign_output['info_file'] = campaign.info_file.url

        return {'campaign_details': campaign_output, 'registered_drivers': reg_drivers_and_metrics, 'pay_periods': pay_periods}

    def get_registration_driver_list(self):
        slug = self.data.get('slug')
        campaign = DriverCampaign.objects.get(slug=slug)
        org = Organization.objects.get(id=self.user.employee().organization_id)
        if org.type != 'Station-Business':
            stations = org.lineage('Station-Business')
            stations = Organization.objects.filter(id__in=stations).values_list('name', flat=True)
        else:
            stations = [org.name]

        driver_status = CampaignRegistrationStatus.objects.filter(campaign_title=campaign.title,
                                                                  organization__in=stations) \
            .values('driver_name', 'driver_id', 'organization', 'territory', 'cohort_name', 'registration_date',
                    'username', 'email', 'raw_data_driver_id', 'field_consultant')

        return driver_status

    def get_registered_data_with_payperiod(self):
        slug = self.data.get('slug')
        campaign = DriverCampaign.objects.get(slug=slug)
        self.campaign = campaign
        org = Organization.objects.get(id=self.user.employee().organization_id)
        if org.type != 'Station-Business':
            stations = org.lineage('Station-Business')
            stations = Organization.objects.filter(id__in=stations).values_list('id', flat=True)
        else:
            stations = [org.id]
        # registered = DriverCampaignRegistration.objects.filter(campaign_id=campaign.id,
        #                                                        driver__organization__id__in=stations) \
        #     .annotate(username=F('driver__user__username'),
        #               drive_namer=F('driver__full_name'),
        #               station_name=F('driver__organization__name'),
        #               territory=F('driver__organization__parent__name'),
        #               registration_group=F('registration_cohort__name')) \
        #     .values('username', 'driver_id', 'driver__full_name', 'station_name', 'territory', 'registration_group',
        #             'registration_date', 'registration_cohort__id')
        registered = DriverCampaignRegistration.objects.filter(campaign_id=campaign.id,
                                                               driver__organization__id__in=stations) \
            .annotate(username=F('driver__user__username'),
                      drive_namer=F('driver__full_name'),
                      station_name=F('driver__organization__name'),
                      territory=F('driver__organization__parent__name'),
                      registration_group=F('registration_cohort__name'))

        payp_id = self.data.get('pay_period')
        if payp_id != 0:
            pay_period = PayPeriod.objects.get(id=payp_id)
            self.pay_period = pay_period
            start_date_range = pay_period.upload_from_date
            end_date_range = pay_period.upload_to_date
        campaign_cohorts = RegistrationCohort.objects.filter(campaign_id=campaign.id)

        reg_drivers_and_metrics = []

        for c in campaign_cohorts:
            print(c.name, start_date_range, end_date_range)
            print(len(reg_drivers_and_metrics))
            driver_d = ['emp_driver_id', 'username', 'driver_id', 'driver__full_name', 'station_name', 'territory',
                        'registration_group', 'registration_date', 'registration_cohort__id',
                        'driver__raw_data_driver_id']
            registered_f = registered.filter(registration_cohort__id=c.id).annotate(
                emp_driver_id=F('driver_id')).values(*driver_d)
            self.surveys = Std12EReduced.objects.filter(is_valid_record=True,
                                                   date_updated_surveys__gte=start_date_range,
                                                   date_updated_surveys__lt=end_date_range,
                                                   sc_dt_surveys__gte=c.start,
                                                    sc_dt_surveys__lt=campaign.end,
                                                   emp_driver_id__in=[x['driver_id'] for x in registered_f]).filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))
            rdm = combine_dicts(
                [registered_f, self.get_metrics_for_site(self.surveys, c.start, campaign.end, group_on='emp_driver_id')],
                'emp_driver_id')

            if c.id == 5:
                for reg in reg_drivers_and_metrics:
                    print('july group', reg)

            [i.update({'driverMetrics': []}) for i in reg_drivers_and_metrics if 'driverMetrics' not in i]
            print('rest of cohort', list([x for x in campaign_cohorts if x.id != c.id]))
            j_start_date = c.start.strftime('%b %d')
            j_end_date = (campaign.end - dt.timedelta(days=1)).strftime('%b %d')
            j_need_to_add = self.blank_metrics_for_site(j_start_date, j_end_date)

            [i.update({'driverMetrics': j_need_to_add}) for i in rdm if 'driverMetrics' not in i]

            for i in rdm:
                if i['registration_cohort__id'] != c.id:
                    print('appending stuff to this...', i)
                    [i['driverMetrics'].append(j) for j in j_need_to_add if j not in i['driverMetrics']]

            reg_drivers_and_metrics = reg_drivers_and_metrics + rdm
            print(len(reg_drivers_and_metrics))

        return reg_drivers_and_metrics

    def registration_check(self):
        employee = self.user.employee()

        # For testing
        # test_registered = 25198
        # test_unregistered = 79229
        # employee = Employee.objects.get(id=test_unregistered)

        campaign_available = CampaignEligibility.objects.filter(campaign__active=1, organization__parent_id=employee.organization.id)
        if campaign_available.count() > 0:
            campaign = DriverCampaign.objects.get(id=campaign_available[0].campaign.id)
            registered = DriverCampaignRegistration.objects.filter(campaign_id=campaign.id).values_list('driver_id', flat=True)
            is_registered = employee.id in registered
            return [is_registered, employee, campaign]
        else:
            return {'message': 'Not Eligible'}

    def campaign_registration(self):
        reg_check = self.registration_check()
        try:
            [registered, employee, campaign] = reg_check
        except:
            return reg_check

        if registered:
            return {'message': 'Is already registered'}

        pre_reg_time = self.request.data.get('registration_date')
        reg_time = dt.datetime.strptime(pre_reg_time, '%Y-%m-%d %H:%M:%S')

        preferred_payment_method = self.request.data.get('preferred_payment_method')
        print(reg_time, campaign)
        registration_cohort = RegistrationCohort.objects.get(registration_start__lte=reg_time, end__gt=reg_time, campaign=campaign)
        reg = DriverCampaignRegistration.objects.create(
            registration_cohort=registration_cohort,
            campaign=campaign,
            driver=employee,
            preferred_payment_method=preferred_payment_method,
            registration_date=reg_time
        )
        try:
            for related_employee in employee.get_related_employee():
                related_reg = DriverCampaignRegistration.objects.create(
                    registration_cohort=registration_cohort,
                    campaign=campaign,
                    driver=related_employee,
                    preferred_payment_method=preferred_payment_method,
                    registration_date=reg_time
                )
        except Exception as e:
            print(e)

        return {'registered': True}

    def driver_campaign(self):
        reg_check = self.registration_check()

        self.pending_payment = None
        try:
            [registered, employee, campaign] = reg_check
        except:
            return reg_check

        # campaign = self.request.data.get('campaign_name') # maybe remove

        try:
            self.campaign = DriverCampaign.objects.get(active=True)
        except:
            self.campaign = DriverCampaign.objects.get(title=campaign)

        # self.driver = self.user.employee()
        today= dt.datetime.today()

        # TEST_EMP = 10998
        # if self.driver.position_type != 'Driver' and TEST_EMP:
        #     self.driver = Employee.objects.get(id=TEST_EMP)

        if employee.position_type == 'Driver':
            self.driver = employee

        # get upload params
        if registered is False:
            if campaign.image is not None:
                image = campaign.image.url
            else:
                image = None
            return {'message': 'Driver not registered', 'registrationNotes': campaign.notes, 'campaignImage': image, 'campaignTitle': campaign.title}

        self.reg_group = DriverCampaignRegistration.objects.get(driver=self.driver, campaign=self.campaign)
        self.service_start = self.reg_group.registration_cohort.start

        # upload cutoffs
        # note upload to date is everything BEFORE that date,
        # so choose day after if you want to include it!
        try:
            self.pay_period = PayPeriod.objects.get(upload_from_date__lte=today,
                                                    upload_to_date__gt=today,
                                                    campaign=self.campaign)
        except:
            #TODO: really need a better solution here...
            self.pay_period = PayPeriod.objects.filter(campaign=self.campaign).last()

        print(self.pay_period.upload_from_date,self.pay_period.upload_to_date, self.driver.id, self.service_start)
        self.surveys = Std12EReduced.objects.filter(is_valid_record=True,
                                                    date_updated_surveys__gte=self.pay_period.upload_from_date,
                                                    date_updated_surveys__lt=self.pay_period.upload_to_date,
                                                    sc_dt_surveys__gte=self.service_start,
                                                    sc_dt_surveys__lt=campaign.end,
                                                    emp_driver_id=self.driver).filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))

        print(self.surveys.count())

        if self.campaign.payment_converter:
            self.payment_converter = json.loads(self.campaign.payment_converter)
            print(self.payment_converter)
            # self.get_pending_payment()

        period_notes = f"""
        Showing survey results for events from {self.service_start.strftime('%Y-%m-%d')} through today where surveys were submitted between {self.pay_period.upload_from_date.strftime('%Y-%m-%d')} and {self.pay_period.upload_to_date.strftime('%Y-%m-%d')}. Payments are determined based on $40 for each Totally Satisfied survey from events on the weekend, and $20 for each Totally Satisfied survey from events on the weekday.
        """.strip()

        self.app_note_vars = {
            'service_start': self.service_start.strftime('%Y-%m-%d'),
            'upload_from_date': self.pay_period.upload_from_date.strftime('%Y-%m-%d'),
            'upload_to_date': self.pay_period.upload_to_date.strftime('%Y-%m-%d'),
        }

        period_notes = self.campaign.app_site_notes.format(**self.app_note_vars)

        self.curr_payment_paid = None
        self.campaign_metrics = CampaignMetricsHelper(arena=self)

        top_slot_value, bottom_slot_value = self.campaign_metrics.get_reward_metrics()

        self.metricData = self.campaign_metrics.get_all_metric_data()

        output = {
            'driverName': self.driver.full_name,
            'campaignTitle': self.campaign.title,
            'campaignImage': self.campaign.image.url,
            'campaignEarning': top_slot_value,
            'campaignTotalEarnings': bottom_slot_value,
            'show_rewards_top_slot': self.campaign.show_rewards_top_slot,
            'show_rewards_bottom_slot': self.campaign.show_rewards_bottom_slot,
            'rewards_top_slot_title': self.campaign.rewards_top_slot_title,
            'rewards_bottom_slot_title': self.campaign.rewards_bottom_slot_title,
            'rewardsTopSlotValue': top_slot_value,
            'rewardsBottomSlotValue': bottom_slot_value,
            'period_notes': period_notes,
            'metrics': self.metricData,
        }
        if self.campaign.image:
            output['campaignImage'] = self.campaign.image.url
        else:
            output['campaignImage'] = None
        return output

    def get_pending_payment(self):
        relevant_metrics = [m for m in self.metricData if m['metricTitle'] in list(self.payment_converter.keys())]
        payout = 0.0
        # todo: self.payment_converter and payper_servey_amount (options)
        for m in relevant_metrics:
            print(m)
            payout += self.payment_converter[m['metricTitle']] * m['metricValue']

        cap = self.campaign.pay_cap

        if payout > cap:
            payout = cap

        if self.curr_payment_paid is None:
            self.get_curr_payment_paid()

        if payout + self.curr_payment_paid > cap:
            payout = cap - self.curr_payment_paid

        self.pending_payment = payout
        return payout, relevant_metrics

    def flatten_format(self, data):
        out = []
        # print('flat format data', data)
        for v in self.flatten_d:

            out.append(
                {
                    'metricTitle': f"{v['m_title']} ({self.start:%b %d} - {self.end:%b %d})",
                    'metricValue': data.get(v['m_key'], 0) if data.get(v['m_key'], 0) is not None else 'N/A',
                    'metricType': v['m_type']
                }
            )
        out = {
            self.group_on: data.get(self.group_on),
            'driverMetrics': out
        }
        return out

    def blank_metrics_for_site(self, start, end):
        metrics_list = self.campaign.site_metrics.all()
        print('campaign metric list', metrics_list)
        out = []
        for m in metrics_list:
            out.append({
                'metricTitle': f'{m.name} ({start} - {end})',
                'metricValue': 'N/A',
                'metricType': m.type
            })
        return out


    def get_metrics_for_site(self, surveys, start, end, group_on=False):
        # surveys should already be filtered appropriately
        self.start, self.end = start, end - dt.timedelta(days=1)
        metric_list = self.campaign.site_metrics.all()
        # print('campaign metric list', metric_list)
        self.flatten_d = []
        metric_filters = []
        annotate_decode = {
            'overall_sat': 'overall_sat',
        }
        for m in metric_list:
            self.flatten_d.append({
                'm_title': m.name,
                'm_type': m.type,
                'm_key': m.key_site
            })
            _metric = {}
            if m.filter is not None and m.filter != '':
                fil = json.loads(m.filter)
                _metric['filters'] = {fil[0]['filter']: fil[0]['val']}

            if m.annotate is not None and m.annotate != '':
                _metric['annotate'] = json.loads(m.annotate)
            if _metric != {}:
                metric_filters.append(_metric)


        if group_on:
            surveys = surveys.values(group_on)

            combined = []
            # print(metric_filters)
            for m in metric_filters:
                _prefix = m['annotate'].get('prefix', '')
                # print('survey filter', surveys.filter(**m['filters']))
                # print('survey filter', surveys.filter(**m['filters']))
                queryset = generate_biz_rules_annotation(['overall_sat'], surveys.filter(**m['filters']), annotate=True, aggregate=False, prefix=_prefix)

                if combined == []:
                    combined = queryset
                else:
                    combined = combine_dicts([combined, queryset], group_on)
            # print(surveys.values('overall_sat'))
            all = generate_biz_rules_annotation(['overall_sat'], surveys, annotate=True, aggregate=False, prefix='base_')
            # print('all', all)

            self.group_on = group_on
            # weekday = surveys.filter(sc_dt_surveys__week_day__in=[2,3,4,5,6])
            # weekend = generate_biz_rules_annotation(['overall_sat'], surveys.filter(sc_dt_surveys__week_day__in=[1, 7]), annotate=True, aggregate=False, prefix='weekend_')
            if combined != []:
                # print('combining dicts')
                full_dict = combine_dicts([all, combined], group_on)
                # print(full_dict)
            else:
                full_dict = all
            # print('full_dict', full_dict)
            self.surveys = surveys
            self.curr_payment_paid = None
            extra_metrics = ['variable_pay_per_survey_this_period_earnings', 'variable_pay_per_survey_total_earnings', 'variable_pay_per_survey_amount']
            for m in extra_metrics:
                full_dict = combine_dicts([full_dict, CampaignMetricsHelper(arena=self).rewards_metric_router[m](osat_group=full_dict)], group_on)
            # [d.update({''})]

            return_list = list(map(self.flatten_format, full_dict))
            # print('blank metrics', return_list)
            return return_list


        overall = surveys.aggregate(ts_count=Sum('overall_sat'), base=Count('overall_sat'))
        start_date = start.strftime('%b %d')
        end_date = (end - dt.timedelta(days=1)).strftime('%b %d')
        weekday_osat = surveys.filter(sc_dt_surveys__week_day__in=[2,3,4,5,6])\
            .aggregate(ts_count=Sum('overall_sat'))
        weekend_osat = surveys.filter(sc_dt_surveys__week_day__in=[1, 7])\
            .aggregate(ts_count=Sum('overall_sat'))
        output =  []


        return output

    def get_curr_payment_paid(self, driver_id=None):
        """
        get whats already been paid from driver payments table -- should be useful regardless of campaign
        :return:
        """
        if driver_id is not None:
            self.driver = Employee.objects.get(id=driver_id)
            try:
                self.reg_group = DriverCampaignRegistration.objects.get(driver=self.driver, campaign=self.campaign)
            except:
                self.reg_group = DriverCampaignRegistration.objects.filter(driver=self.driver, campaign=self.campaign)[0]
        # print('current driver', self.driver)
        try:
            curr_payment_paid = DriverPayments.objects.exclude(pay_period=self.pay_period).filter(driver_id=self.driver.id,
                                                              registration_group_id=self.reg_group.registration_cohort.id)\
                .values('driver_id')\
                .annotate(total_earnings=Sum('payment'))\
                .values('total_earnings')
            # print(curr_payment_paid, self.driver.id)
            if curr_payment_paid:
                curr_payment_paid = float(curr_payment_paid[0]['total_earnings'])
            else:
                curr_payment_paid = 0.0
        except ObjectDoesNotExist:
            curr_payment_paid = 0.0
        self.curr_payment_paid = curr_payment_paid

    def get_driver(self, driver_id):
        self.driver = Employee.objects.get(id=driver_id)



        # org_scores = TeamOrganizationScores.objects.filter(team=team).values('id', 'team__name', 'organization__name', 'organization__slug', 'score', 'impact', 'volume', 'organization__type', 'round__name')
        # emp_scores = TeamEmployeeScores.objects.filter(team=team).values('id', 'team__name', 'employee__last_name', 'employee__first_name' ,'employee__slug', 'score', 'impact', 'volume', 'employee__position_type', 'round__name')
        # output_list = []
        # for o in org_scores:
        #
        #     for s in org_component_scores:
        #         o[s['component__label']] = round(s['value'],1)
        #     o['name'] = o.pop('organization__name')
        #     o['team'] = o.pop('team__name')
        #     o['type'] = o.pop('organization__type')
        #     # o['type'] = clean_org_types[o['type']]
        #     o['slug'] = o.pop('organization__slug')
        #     o['round'] = o.pop('round__name')
        #     o['score'] = round(o['score'],1)
        #
        #     del o['id']
        #     # print(output_list[0])
        #     output_list.append(o)
        #
        # for e in emp_scores:
        #     emp_component_scores = TeamEmployeeScoresComponent.objects.filter(team_employee_scores_id=e['id']).values(
        #         'component__label', 'value'
        #     )
        #
        #     for s in emp_component_scores:
        #         e[s['component__label']] = round(s['value'],1)
        #     e['name'] = e.pop('employee__first_name') + " " + e.pop('employee__last_name')
        #     e['team'] = e.pop('team__name')
        #     e['type'] = e.pop('employee__position_type')
        #     # o['type'] = clean_org_types[o['type']]
        #     e['slug'] = e.pop('employee__slug')
        #     e['round'] = e.pop('round__name')
        #     e['score'] = round(e['score'],1)
        #
        #     del e['id']
        #     # print(output_list[0])
        #     output_list.append(e)



        # return list(output_list)
