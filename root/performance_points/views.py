from xml.dom.domreg import registered

from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from opensearchpy.serializer import TIME_TYPES
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from django.db.models import CharField, F, Value as V, Q
from django.db.models.functions import Concat, Coalesce
from django.utils import timezone
import datetime as dt
import json
from root.utilities import local_now
from .models import *
from root.utilities import queryset_object_values, combine_dicts
from django.db.models.aggregates import StdDev, Avg, Sum, Max
from accounts.serializers import SimpleEmployeeSerializer
from django.forms.models import model_to_dict
from accounts.models import Profile, Employee
from training.models import ModuleOverview, ModuleCompletion, ModuleTag
from dashboard.models import DashboardAggregations
from training.serializers import ShortModuleOverviewSerializer
from .serializers import *
from django.db.models import F
from django.db.models.functions import TruncDate
# from dashboard.models import Std12ERaw
from payments.PaymentMethods import PaymentMethods
from accounts.models import Employee, EmployeeGroup, UserActions
from django.db.models import Case, CharField, Value, When, Subquery

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from accounts.models import Profile, User, StationDriver

from itertools import chain


def update_completed_clips(campaign, employee):
    modules = ModuleOverview.objects.filter(campaign=campaign)
    completed_modules_count = ModuleCompletion.objects.filter(
        module__in=modules,
        employee=employee,
        completed=True
    ).count()

    return completed_modules_count

def update_overall_sat(employee, campaign):
    if not campaign.show_performance_metrics:
        return
    overall_sat = DashboardAggregations.objects.filter(employee_id=employee.id, time_type='M').values('aaa_mgmt_any_overall_sat_avg').first()
    print('overall_sat', overall_sat)
    return overall_sat['aaa_mgmt_any_overall_sat_avg']

def update_call_volume(employee, campaign):
    if not campaign.show_performance_metrics:
        return
    call_volume = DashboardAggregations.objects.filter(employee_id=employee.id, time_type='M').values('all_volume').first()
    print('call_volume', call_volume)
    return call_volume['all_volume']


def update_logins(employee):
    date = timezone.now().date()

    start_of_month = date.replace(day=1)
    end_of_month = timezone.now().replace(day=1) + timezone.timedelta(days=31)
    end_of_month = end_of_month.replace(day=1) - timezone.timedelta(days=1)

    # Count unique daily logins within the month
    unique_logins = (
        UserActions.objects.filter(
            user=employee.user,
            type='App Login',
            date__date__range=(start_of_month, end_of_month)
        )
        .annotate(login_date=TruncDate('date'))  # Truncate the datetime to just the date
        .values('login_date')  # Group by the truncated date
        .distinct()  # Get unique dates
        .count()
    )

    return unique_logins


class PerformancePoints(APIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()
    # serializer_class = None
    www_authenticate_realm = 'api'

    def __init__(self):
        self.user = None
        self.data = None
        self.parameters = None
        self.purpose = None
        self.purpose_router = {
            'default': None,
            'leaderboard': self.leaderboard,
            'get_teams': self.get_teams,
            'driver_detail_points': self.driver_detail_points,
            'get_points_stats': self.get_points_stats,
            'team_contest_results': self.team_contest_results,
            'team_rankings': self.team_rankings,
            'match_schedule': self.match_schedule,
            'draft': self.draft,
            'skill_tree': self.skill_tree,
            'get_campaign_table_metric_data': self.get_campaign_table_metric_data,
            'leaderboard_filter': self.leaderboard_filter,
            'get_campaigns': self.get_campaigns,
            'get_campaign_points': self.get_campaign_points,
            'get_campaign_metrics': self.get_campaign_metrics,
            'get_campaign_transaction_history': self.get_campaign_transaction_history,
            'get_campaign_points_metrics_transactions': self.get_campaign_points_metrics_transactions,
            'get_campaign_drivers': self.get_campaign_drivers,
            'get_campaign_driver': self.get_campaign_driver,
            'exclude_campaign_groups': self.exclude_campaign_groups,
            'get_all_employee_campaign_data': self.get_all_employee_campaign_data,
            'create_create_campaign_transaction': self.create_create_campaign_transaction,
            'create_bet': self.create_bet,
            'get_bank': self.get_bank,
            'create_bank_action': self.create_bank_action,
            'sign_up_to_campaign': self.sign_up_to_campaign
        }

    def post(self, request):
        self.user = request.user
        self.data = request.data
        self.purpose = self.data.get('purpose', 'default')
        self.parameters = self.data.get('parameters', {})
        self.contest = PPContest.objects.get(id=1)

        output = self.purpose_router[self.purpose]()
        return Response(output, status=status.HTTP_200_OK)

    def create_bet(self):
        bet = Bets.objects.create(
            ratio=self.parameters.get('ratio'),
            points_bet=self.parameters.get('points_bet'),
            target=self.parameters.get('target'),
            metric=self.parameters.get('metric'),
            driver=Employee.objects.get(user=self.request.user)
        )

        return model_to_dict(bet)

    def create_bank_action(self):
        bank_action = Bank.objects.create(
            employee=self.request.user.employee(),
            action=self.parameters['action'],
            bet_allocation=self.parameters['data'].get('bettingPoints', 0),
            pending_payment_amount=self.parameters['data'].get('pending_payment_amount', 0)
        )

        return model_to_dict(bank_action)

    def get_bank(self):
        employee = self.request.user.employee()
        variables = ['cume_arc_kmi_points', 'cume_calls_run_points', 'cume_kept_informed_sat_points',
                     'cume_osat_points', 'cume_total_points']
        period = self.parameters.get('period', 3)  # todo: make this a calculation based on dates, not a setting
        points = PPDriverPoints.objects.filter(driver=employee, config_id=period)
        max_sc_dt = points.aggregate(Max('sc_dt'))['sc_dt__max']
        points = points.filter(sc_dt=max_sc_dt, variable__in=variables).values('variable', 'value')
        fed = Fed.objects.filter(period_id=period).values()[0]
        bank = Bank.objects.filter(employee=employee).values()
        return {'points': points, 'fed': fed, 'bank': bank}

    def default(self):
        return {'message': 'Nothing to see here'}

    def getPointStats(self, points):
        max_sc_dt = points.aggregate(Max('sc_dt'))['sc_dt__max']
        stats = PerformancePointStats.objects.filter(max_dt=max_sc_dt)
        if stats:
            return stats.values('variable', 'avg')
        else:
            stats = points.values('variable').annotate(avg=Avg('value')).values('variable', 'avg')
            [q.update({'max_dt': max_sc_dt}) for q in stats]
            stats = PerformancePointStats.objects.bulk_create([
                PerformancePointStats(**q) for q in stats
            ])
        return stats

    def skill_tree(self):
        variables = ['kmi_sat_points', 'osat_sat_points', 'driver_sat_points', 'total_points']
        if self.parameters.get('employee_slug'):
            driver = Employee.objects.get(slug=self.parameters.get('employee_slug'))
        else:
            driver = Employee.objects.get(user=self.request.user)
        points = PPDriverPoints.objects.filter(sc_dt__gte='2021-07-01', variable__in=variables)
        stats = self.getPointStats(points)
        driver_pts = points.filter(driver=driver)
        driver_stats = driver_pts.values('variable').annotate(avg=Avg('value')).values('variable', 'avg')
        driver_pts = driver_pts.filter(sc_dt__gte='2021-07-01').values().order_by('-sc_dt')

        print('returning skill tree')
        # return {"about": SimpleEmployeeSerializer(driver).data}
        return {"raw": driver_pts, "stats": {"driver": driver_stats, "global": stats},
                "about": SimpleEmployeeSerializer(driver).data}

    def leaderboard(self):
        ''' {
            rank: 1,
            name: '',
            station: '',
            change: 'up/down',
            points: 1234,
            drafted: false
        }
        '''
        today = dt.date.today()
        prev_day = today - dt.timedelta(days=1)

        try:
            prev_day_ranks = PPDriverRanks.objects.filter(date__lt=today).distinct().order_by('-date')[0]
        except:
            prev_day_ranks = None

        print('prev ranks', prev_day_ranks)
        try:
            day_ranks = PPDriverRanks.objects.get(date=today)
        except MultipleObjectsReturned:
            day_ranks = PPDriverRanks.objects.filter(date=today)[0]
            PPDriverRanks.objects.filter(date=today).exclude(id=day_ranks.id).delete()
        except ObjectDoesNotExist:
            day_ranks = PPDriverRanks.objects.create(date=today)

        if prev_day_ranks:
            p_ranks = json.loads(prev_day_ranks.list)
        else:
            p_ranks = None

        print(p_ranks)
        driver_list = PPDriverCurrent.objects.all().annotate(driver_name=F('driver__full_name'),
                                                             station_name=F('station_business__name'),
                                                             level=F('driver__pp_driver_level__level')).order_by(
            '-points', 'driver_name').values()
        rank_list = {}
        # print(driver_list)
        skip_id = [
            '80190-3',
            '80229-3',
            '80448-3',
            '80575-3',
            '80536-3',
            '80612-3',
            '80571-3',
            '80543-3',
            '80562-3',
            '80649-3',
            '80446-3',
            '80611-3',
            '80544-3',
            '80161-3',
            '80591-3',
            '80551-3',
            '80633-3',
            '80569-3',
            '80634-3',
            '80664-3',
            '80550-3',
            '80546-3',
            '80560-3',
            '80628-3',
            '80573-3',
            '80542-3',
            '80547-3',
            '80613-3',
            '80548-3',
            '80553-3',
            '80651-3',
            '80659-3',
            '80581-3',
            '80618-3',
            '80615-3',
            '80683-3',
            '80583-3',
            '80656-3',
            '80681-3',
            '80594-3',
            '80745-3',
            '80597-3',
            '80696-3',
            '80576-3',
            '80688-3',
            '80712-3',
            '80682-3',
            '80715-3',
            '80572-3',
            '80642-3',
            '80616-3',
            '80641-3',
            '80752-3',
            '80587-3',
            '80590-3',
            '80580-3',
            '80657-3',
            '80744-3',
            '80707-3',
            '80595-3',
            '80724-3',
            '80570-3',
            '80585-3',
            '80790-3',
            '80635-3',
            '80687-3',
            '80665-3',
            '80713-3',
            '80648-3',
            '80582-3',
            '80626-3',
            '80652-3',
            '80754-3',
            '80566-3',
            '80588-3',
            '80685-3',
            '80549-3',
            '80716-3',
            '80720-3',
            '80723-3',
            '80614-3',
            '80684-3',
            '80686-3',
            '80565-3',
            '80755-3',
            '80638-3',
            '80753-3',
            '80706-3',
            '80782-3',
            '80538-3',
            '80778-3',
            '80780-3',
            '80552-3',
            '80697-3',
            '80789-3',
            '80617-3',
            '80719-3',
            '80574-3',
            '80805-3',
            '80699-3',
            '80627-3',
            '80559-3',
            '80561-3',
            '80584-3',
            '80717-3',
            '80680-3',
            '80702-3',
            '80798-3',
            '80310-3',
            '80586-3',
            '80799-3',
            '80749-3',
            '80760-3',
            '80802-3',
            '80568-3',
            '80690-3',
            '80701-3',
            '80757-3',
            '80726-3',
            '80747-3',
            '80804-3',
            '80800-3',
            '80653-3',
            '80661-3',
            '80663-3',
            '80705-3',
            '80762-3',
            '80545-3',
            '80592-3',
            '80639-3',
            '80650-3',
            '80654-3',
            '80658-3',
            '80660-3',
            '80698-3',
            '80714-3',
            '80748-3',
            '80761-3',
            '80791-3',
            '80537-3',
            '80539-3',
            '80554-3',
            '80567-3',
            '80593-3',
            '80636-3',
            '80640-3',
            '80655-3',
            '80689-3',
            '80691-3',
            '80703-3',
            '80722-3',
            '80727-3',
            '80751-3',
            '80779-3',
            '80781-3',
            '80783-3',
            '80788-3',
            '80792-3',
            '80794-3',
            '80806-3',
            '80540-3',
            '80558-3',
            '80637-3',
            '80662-3',
            '80700-3',
            '80704-3',
            '80718-3',
            '80746-3',
            '80750-3',
            '80756-3',
            '80758-3',
            '80784-3',
            '80793-3',
            '80803-3',
            '80807-3'
        ]
        driver_ranks = []
        current_rank_placement = 0
        prev_rank_points = 0
        for idx, driver in enumerate(driver_list):
            if driver['id'] not in skip_id:
                try:
                    if 'filter_on' not in self.parameters:
                        if str(driver['driver_id']) in p_ranks:
                            current_rank = idx + 1 if prev_rank_points != driver['points'] else current_rank_placement
                            current_rank_placement = idx + 1 if prev_rank_points != driver[
                                'points'] else current_rank_placement
                            change = 'none' if current_rank == p_ranks[str(driver['driver_id'])] else (
                                'up' if current_rank < p_ranks[str(driver['driver_id'])] else 'down')
                        else:
                            current_rank = idx + 1 if prev_rank_points != driver['points'] else idx + 1
                            change = 'none'
                        rank_list[driver['driver_id']] = current_rank
                        prev_rank_points = driver['points']
                    else:
                        current_rank = day_ranks[str(driver['driver_id'])]
                        if str(driver['driver_id']) in p_ranks:
                            change = 'none' if current_rank == p_ranks[str(driver['driver_id'])] else (
                                'up' if current_rank < p_ranks[str(driver['driver_id'])] else 'down')
                        else:
                            change = 'none'

                    rank = self.lb_table_format(current_rank, driver, change)
                    driver_ranks.append(rank)
                except:
                    print(driver['id'])

        if 'filter_on' not in self.parameters:
            day_ranks.list = json.dumps(rank_list)
        day_ranks.save()

        return {'message': rank_list, 'rank': driver_ranks}

    def lb_table_format(self, rank, driver, change):
        return {
            'rank': rank,
            'name': driver['driver_name'],
            'driver_id': driver['driver_id'],
            'station': driver['station_name'],
            'change': change,
            'points': driver['points'],
            'level': driver['level']
        }

    def get_points_stats(self):
        # For MTK
        driver = Employee.objects.get(id=self.parameters.get('driver_id'))

        self.today = self.parameters.get('today', dt.datetime.today().strftime('%Y-%m-%d'))

        ### TESTING
        self.today = '2023-05-22'
        ###

        self.today = dt.datetime.strptime(self.today, '%Y-%m-%d')

        self.period_end = self.kwargs.get('end_date', '2023-05-01')
        self.period_end = dt.datetime.strptime(self.period_end, '%Y-%m-%d')

        self.period_start = self.kwargs.get('end_date', '2023-05-31')
        self.period_start = dt.datetime.strptime(self.period_start, '%Y-%m-%d')

        self.remaining_days = (self.period_end - self.today).days
        self.completed_days = (self.today - self.period_start).days

        pp = PPDriverPoints.objects.filter(sc_dt__range=[self.period_start, self.period_end],
                                           variable=self.parameters.get('variable', 'total_points'))

        pp_before_today = pp.filter(sc_dt__range=[self.period_start, self.today])
        global_stats = pp_before_today.aggregate(std=StdDev('value'), mean=Avg('value'))

        driver_stats = pp_before_today.filter(driver=driver).aggregate(std=StdDev('value'), mean=Avg('value'),
                                                                       sum=Sum('value'))

        return {'global_stats': global_stats, 'driver_stats': driver_stats, 'remaining_days': self.remaining_days,
                'completed_days': self.completed_days}

    def driver_detail_points(self):
        # When it goes live
        # today = dt.date.today()
        # today = dt.date(2021, 9, 8) # for testing
        driver_points = PPDriverPoints.objects.filter(driver__id=self.parameters.get('driver_id')).order_by('-sc_dt')
        latest_date = driver_points[0].sc_dt
        driver_points = driver_points.filter(sc_dt=latest_date)
        print(list(driver_points.values()))
        driver_points = list(driver_points.values())
        output = {
            # 'arc_kmi': self.get_value('cume_arc_kmi_points', driver_points),
            'arc_kmi': next((x['value'] for x in driver_points if x['variable'] == 'cume_arc_kmi_points'), 0.0),
            'calls_run': self.get_value('cume_calls_run_points', driver_points),
            'osat': self.get_value('cume_osat_points', driver_points),
            'kept_informed_sat': self.get_value('cume_kept_informed_sat_points', driver_points),
            'total_points': self.get_value('cume_total_points', driver_points)
        }
        return output

    def leaderboard_filter(self):
        level_filter = self.parameters.get('level_filter', 'all')
        min_points = self.parameters.get('min_points', 0)
        max_points = self.parameters.get('max_points', 1000000)

        driver_ranks = PPDriverRanks.objects.last()
        prev_ranks = PPDriverRanks.objects.filter(date__lt=driver_ranks.date).last()

        driver_ranks = json.loads(driver_ranks.list)
        prev_ranks = json.loads(prev_ranks.list)
        print(driver_ranks)
        print(prev_ranks)

        # driver_list = PPDriverCurrent.objects.filter(points__gte=min_points, points__lte=max_points)
        driver_list = PPDriverCurrent.objects.filter(points__range=[min_points, max_points])
        # filter = {
        #
        # }
        if level_filter != 'all':
            driver_list = driver_list.filter(driver__pp_driver_level__level=level_filter)

        driver_list = driver_list.annotate(driver_name=F('driver__full_name'),
                                           station_name=F('station_business__name'),
                                           level=F('driver__pp_driver_level__level')).order_by('-points',
                                                                                               'driver_name').values()
        skip_id = [
            '80190-3',
            '80229-3',
            '80448-3',
            '80575-3',
            '80536-3',
            '80612-3',
            '80571-3',
            '80543-3',
            '80562-3',
            '80649-3',
            '80446-3',
            '80611-3',
            '80544-3',
            '80161-3',
            '80591-3',
            '80551-3',
            '80633-3',
            '80569-3',
            '80634-3',
            '80664-3',
            '80550-3',
            '80546-3',
            '80560-3',
            '80628-3',
            '80573-3',
            '80542-3',
            '80547-3',
            '80613-3',
            '80548-3',
            '80553-3',
            '80651-3',
            '80659-3',
            '80581-3',
            '80618-3',
            '80615-3',
            '80683-3',
            '80583-3',
            '80656-3',
            '80681-3',
            '80594-3',
            '80745-3',
            '80597-3',
            '80696-3',
            '80576-3',
            '80688-3',
            '80712-3',
            '80682-3',
            '80715-3',
            '80572-3',
            '80642-3',
            '80616-3',
            '80641-3',
            '80752-3',
            '80587-3',
            '80590-3',
            '80580-3',
            '80657-3',
            '80744-3',
            '80707-3',
            '80595-3',
            '80724-3',
            '80570-3',
            '80585-3',
            '80790-3',
            '80635-3',
            '80687-3',
            '80665-3',
            '80713-3',
            '80648-3',
            '80582-3',
            '80626-3',
            '80652-3',
            '80754-3',
            '80566-3',
            '80588-3',
            '80685-3',
            '80549-3',
            '80716-3',
            '80720-3',
            '80723-3',
            '80614-3',
            '80684-3',
            '80686-3',
            '80565-3',
            '80755-3',
            '80638-3',
            '80753-3',
            '80706-3',
            '80782-3',
            '80538-3',
            '80778-3',
            '80780-3',
            '80552-3',
            '80697-3',
            '80789-3',
            '80617-3',
            '80719-3',
            '80574-3',
            '80805-3',
            '80699-3',
            '80627-3',
            '80559-3',
            '80561-3',
            '80584-3',
            '80717-3',
            '80680-3',
            '80702-3',
            '80798-3',
            '80310-3',
            '80586-3',
            '80799-3',
            '80749-3',
            '80760-3',
            '80802-3',
            '80568-3',
            '80690-3',
            '80701-3',
            '80757-3',
            '80726-3',
            '80747-3',
            '80804-3',
            '80800-3',
            '80653-3',
            '80661-3',
            '80663-3',
            '80705-3',
            '80762-3',
            '80545-3',
            '80592-3',
            '80639-3',
            '80650-3',
            '80654-3',
            '80658-3',
            '80660-3',
            '80698-3',
            '80714-3',
            '80748-3',
            '80761-3',
            '80791-3',
            '80537-3',
            '80539-3',
            '80554-3',
            '80567-3',
            '80593-3',
            '80636-3',
            '80640-3',
            '80655-3',
            '80689-3',
            '80691-3',
            '80703-3',
            '80722-3',
            '80727-3',
            '80751-3',
            '80779-3',
            '80781-3',
            '80783-3',
            '80788-3',
            '80792-3',
            '80794-3',
            '80806-3',
            '80540-3',
            '80558-3',
            '80637-3',
            '80662-3',
            '80700-3',
            '80704-3',
            '80718-3',
            '80746-3',
            '80750-3',
            '80756-3',
            '80758-3',
            '80784-3',
            '80793-3',
            '80803-3',
            '80807-3'
        ]

        output = []
        for idx, driver in enumerate(driver_list):

            if driver['id'] not in skip_id:
                # try:
                print(driver['driver_id'])
                current_rank = driver_ranks[str(driver['driver_id'])]
                if str(driver['driver_id']) in prev_ranks:
                    change = 'none' if current_rank == prev_ranks[str(driver['driver_id'])] else (
                        'up' if current_rank < prev_ranks[str(driver['driver_id'])] else 'down')
                else:
                    change = 'none'
                rank = self.lb_table_format(driver_ranks[str(driver['driver_id'])], driver, change)
                output.append(rank)
                # except:
                #     print(driver['id'])

        return output

    def get_value(self, variable, list):
        val = 0.0
        for l in list:
            # print(l)
            if l['variable'] == variable:
                val = l['value']
                print(val)
                break
        return val

    def team_rankings(self):
        contest = self.data.get('contest', 1)
        team_ranking_annotation = {
            'team_name': F('team_contest__team__name'),
            'team_slug': F('team_contest__team__slug'),
            'team_transparent_logo': Concat(V('https://wageup-media.s3.us-east-1.amazonaws.com/'),
                                            F('team_contest__team__transparent_logo'), output_field=CharField()),
            'team_territory': F("team_contest__territory__name"),
            'team_small_logo': Concat(V('https://wageup-media.s3.us-east-1.amazonaws.com/'),
                                      F('team_contest__team__small_icon'), output_field=CharField()),
        }

        team_ranking_values = ['team_name', 'team_slug', 'team_transparent_logo', 'team_small_logo', 'wins', 'losses',
                               'rank', 'score', 'team_territory']

        return PPTeamRankings.objects.filter(team_contest__contest_id=contest) \
            .annotate(**team_ranking_annotation) \
            .values(*team_ranking_values)

    def match_schedule(self):
        contest = self.data.get('contest', 1)
        rounds = PPRound.objects.filter(id__lte=8).values()
        [r.update({'matches': {}}) for r in rounds]
        rounds = {r['id']: r for r in rounds}
        all_match_data = PPMatch.objects.filter(round__contest_id=contest, round_id__lte=8).values('id', 'round_id',
                                                                                                   'teams__team__slug',
                                                                                                   'teams__team__name',
                                                                                                   'teams__team__transparent_logo',
                                                                                                   'teams__team__small_icon')
        for match in all_match_data:
            if match['id'] not in rounds[match['round_id']]['matches']:
                rounds[match['round_id']]['matches'][match['id']] = []
            match_d = {
                'team_name': match['teams__team__name'],
                'team_slug': match['teams__team__slug'],
                'team_transparent_logo': f"https://wageup-media.s3.us-east-1.amazonaws.com/{match['teams__team__transparent_logo']}",
                'team_small_logo': f"https://wageup-media.s3.us-east-1.amazonaws.com/{match['teams__team__small_icon']}"

            }
            rounds[match['round_id']]['matches'][match['id']].append(match_d)

        out = []
        for round, round_d in rounds.items():
            round_d['match_list'] = []
            for match_id, match in round_d['matches'].items():
                round_d['match_list'].append(match)
            del round_d['matches']
            out.append(round_d)

        return out

    def team_contest_results(self):
        team_slug = self.data.get('team_slug')
        team = PPTeam.objects.get(slug=team_slug)
        team_contest = PPTeamContest.objects.get(team=team, contest=self.contest)
        matches = PPMatch.objects.filter(teams__in=[team_contest])
        team_assignments = TeamAssignments.objects.filter(team=team_contest)
        team_score_components = PPTeamScoreComponent.objects.filter(team_contest=team_contest)
        team_scores = PPTeamScore.objects.filter(match__in=matches).order_by('match__round__starts')

        team_assignments_annotation = {
            'player_name': F('player__full_name'),
            'player_station': F('player__organization__name'),
            'driver_id': F('player__id')
        }

        team_assignment_values = ['player_name', 'player_station', 'player_type', 'driver_id']

        score_component_annotation = {
            'component_name': F('component__name'),
        }

        score_component_values = ['round_id', 'score', 'component_name']
        rounds = {}
        components = team_score_components.annotate(**score_component_annotation).values(*score_component_values)
        for component in components:
            out_d = {
                'component': component['component_name'],
                'score': component['score']
            }
            if component['round_id'] in rounds:
                rounds[component['round_id']].append(out_d)
            else:
                rounds[component['round_id']] = [out_d, ]

        team_score_annotation = {
            'starts': F('match__round__starts'),
            'ends': F('match__round__ends'),
            'team': F('team_contest__team__name'),
            'round_id': F('match__round_id'),
            'team_logo': F('team_contest__team__transparent_logo'),
            'team_slug': F('team_contest__team__slug')
        }

        team_score_values = ['starts', 'ends', 'team', 'score', 'team_logo', 'team_slug', 'score', 'match_id',
                             'round_id']

        matches = {}
        team_scores = team_scores.annotate(**team_score_annotation).values(*team_score_values)
        for score in team_scores:
            print(score)
            out_d = {
                "score": score['score'],
                "team": score['team'],
                "team_logo": f"https://wageup-media.s3.us-east-1.amazonaws.com/{score['team_logo']}",
                "team_slug": score['team_slug']
            }
            if score['match_id'] in matches:
                matches[score['match_id']]["results"].append(out_d)
            else:
                matches[score['match_id']] = {
                    "starts": score['starts'],
                    "ends": score['ends'],
                    "results": [out_d, ]
                }

        matches_out = []
        for match_id, match in matches.items():
            matches_out.append(match)

        return {
            'my_team': queryset_object_values(team),
            'my_team_players': team_assignments.annotate(**team_assignments_annotation).values(*team_assignment_values),
            'my_team_score_components': rounds,
            'match_history': matches_out
        }
        print('MY TEAM PLAYERS',
              team_assignments.annotate(**team_assignments_annotation).values(*team_assignment_values))
        # return self.default()

    def get_teams(self):
        teams = PPTeam.objects.order_by('name')
        data = list(teams.values())
        print(data)
        return {'teams': data}

    def draft(self):
        drivers = self.parameters.get('preferences')
        print('drivers', drivers)
        captain_id = self.parameters.uget('captain_id')
        team_id = self.parameters.get('team_id')
        team_contest = PPTeamContest.objects.get(team=PPTeam.objects.get(id=team_id),
                                                 contest=self.parameters.get('contest', 1))
        for index, driver in enumerate(drivers):
            preference_row = TeamPreferences(captain_id=captain_id, player_id=driver['driver_id'],
                                             player_level=driver['level'], preference=index + 1, team=team_contest)
            preference_row.save()

        return 'Success!'

    def get_campaigns(self):
        emp = Employee.objects.get(user=self.user)
        if emp.organization.level_index(emp.organization.type) >= 2:
            if (emp.organization.type == 'Station-Business'):
                camps = PPCampaign.objects.filter(active=True, geography_eligiblity__in=[emp.organization.id])
            else:
                camps = PPCampaign.objects.filter(active=True)
            print(camps.values())
            return PPCampaignSerializer(camps, many=True).data
        else:
            return {}

    def get_campaign_points(self):
        annotation = {
            'employee_name': F('employee__display_name'),
            'email': F('employee__user__email'),
            'employee_full_name': Concat('employee__first_name', V(' '), 'employee__last_name'),
            'preferred_email': F('employee__user__profile__campaign_preferred_email'),
            'organization_name': F('employee__organization__name'),
            'organization_id': F('employee__organization__id'),
            'campaign_name': F('campaign__title'),
            'territory': F('employee__organization__parent__name')
        }
        vals = ['employee_name', 'employee_full_name', 'email', 'preferred_email', 'organization_name',
                'organization_id', 'employee_id', 'campaign_name', 'campaign_id',
                'total_points', 'cashed_points', 'cashed_points_dollars', 'not_cashed_points', 'territory']

        is_individual = self.parameters.get('employee_id')
        if is_individual:
            bank = PPCampaignBank.objects.filter(employee_id=self.parameters.get('employee_id'),
                                                 campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        elif self.parameters.get('organization_id'):
            bank = PPCampaignBank.objects.filter(employee__organization_id=self.parameters.get('organization_id'),
                                                 campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)

            self.registered = PPCampaignRegistration.objects.filter(
                employee__organization_id=self.parameters.get('organization_id'),
                campaign_id=self.parameters.get('campaign_id', 1),
            ).annotate(
                display_name=F('employee__display_name'),
                full_name=F('employee__full_name'),
                email=F('employee__user__email'),
                preferred_email=F('employee__profile__campaign_preferred_email'),
                organization_id=F('employee__organization_id'),
                organization_name=F('employee__organization__name'),
                territory=F('employee__organization__parent__name')
            ).values(
                'display_name', 'full_name', 'email', 'preferred_email',
                'organization_id', 'organization_name', 'territory', 'employee_id', 'registration_date'
            )
        else:
            bank = list(PPCampaignBank.objects.filter(campaign_id=self.parameters.get('campaign_id', 1)) \
                .annotate(**annotation).values(*vals))

            self.registered = PPCampaignRegistration.objects\
                .filter(campaign_id=self.parameters.get('campaign_id', 1)).annotate(
                display_name=F('employee__display_name'),
                full_name=F('employee__full_name'),
                email=F('employee__user__email'),
                preferred_email=F('employee__profile__campaign_preferred_email'),
                organization_id=F('employee__organization_id'),
                organization_name=F('employee__organization__name'),
                territory=F('employee__organization__parent__name')
            ).values(
                'display_name', 'full_name', 'email', 'preferred_email',
                'organization_id', 'organization_name', 'territory', 'employee_id', 'registration_date'
            )


        if not bank and is_individual:
            if not self.emp:
                self.emp = self.request.user.employee()

            if not hasattr(self, 'camp'):
                self.camp = PPCampaign.objects.filter(id=self.parameters.get('campaign_id', 1)).values()[0]

            return [{
                'employee_name': self.emp.display_name,
                'employee_full_name': self.emp.full_name,
                'email': self.emp.user.email if self.emp.user else None,
                'preferred_email': Profile.objects.get(
                    user=self.emp.user).campaign_preferred_email or self.emp.user.email if self.emp.user else None,
                'organization_name': self.emp.organization.name,
                'organization_id': self.emp.organization.id,
                'employee_id': self.emp.id,
                'campaign_name': self.camp['title'],
                'campaign_id': self.camp['id'],
                'total_points': 0,
                'cashed_points': 0,
                'cashed_points_dollars': 0,
                'not_cashed_points': 0
            }]

        if not is_individual:
        # elif not bank and self.registered:
        #     bank = []
            for emp in self.registered:
                if not next(iter(filter(lambda x: x['employee_id'] == emp['employee_id'], bank)), None):
                    print('no points yet for', emp['employee_id'])
                    bank.append({
                    'employee_name': emp['display_name'],
                    'employee_full_name': emp['full_name'],
                    'email': emp['email'],
                    'preferred_email': emp['preferred_email'] or emp['email'],
                    'organization_name': emp['organization_name'],
                    'organization_id': emp['organization_id'],
                    'employee_id': emp['employee_id'],
                    'campaign_name': self.camp['title'],
                    'campaign_id': self.camp['id'],
                    'total_points': 0,
                    'cashed_points': 0,
                    'cashed_points_dollars': 0,
                    'territory': emp['territory'] or emp['organization_name'],
                    'not_cashed_points': 0,
                        'registration_date': emp['registration_date']
                    })

            for b in bank:
                if not b['email'] and not b['preferred_email']:
                    # print('no email!', b)
                    try:
                        b['email'] = Employee.objects.get(id=b['employee_id']).get_related_user().email
                    except:
                        print('no email', b)
        return bank

    # def get_campaign_module_completion_history(self):
    #     if not hasattr(self, 'camp'):
    #         self.camp = PPCampaign.objects.filter(id=self.parameters.get('campaign_id', 1)).values()[0]
    #     annotation = {
    #         'module_name': F('module__title')
    #     }
    #     vals = ['employee_id', 'module_name']
    #     if self.parameters.get('employee_id'):
    #         module_history = ModuleCompletion.objects.filter(
    #             employee_id=self.parameters.get('employee_id'),
    #             module__tags__campaign=self.camp['id']) \
    #             .annotate(**annotation).distinct().values(*vals)
    #         print(module_history)
    #     elif self.parameters.get('organization_id'):
    #         module_history = ModuleCompletion.objects.filter(
    #             employee__organization_id=self.parameters.get('organization_id'),
    #             module__tags__campaign=self.camp['id']) \
    #             .annotate(**annotation).distinct().values(*vals)
    #     else:
    #         module_history = ModuleCompletion.objects.filter(
    #             employee__campaign_registration__campaign=self.camp['id'],
    #             module__tags__campaign=self.camp['id']) \
    #             .annotate(**annotation).distinct().values(*vals)
    #     # return module_history
    #     return combine_dicts(module_history, 'employee_id', strict=False,
    #                          concat_same_key=['module_name'])


    def get_campaign_transaction_history(self):
        # ready for deployment
        annotation = {
            'employee_name': F('employee__display_name'),
            'organization_name': F('employee__organization__name'),
            'organization_id': F('employee__organization__id'),
            'campaign_name': F('campaign__title'),
            'transaction_date': F('date'),
            'transaction_points': F('points'),
            'transaction_dollars': F('dollars')
        }
        vals = ['employee_name', 'organization_name', 'organization_id', 'employee_id', 'campaign_name', 'campaign_id',
                'overall_sat', 'overall_sat_threshold', 'totally_satisfied_count', 'transaction_date', 'transaction_points', 'transaction_dollars']

        campaign = PPCampaign.objects.get(id=1)
        campaign_start_date = campaign.start
        print('CAMPAIGN START DATE', campaign_start_date)
        if self.parameters.get('employee_id'):
            transaction_history = PPCampaignBankTransactionLog.objects.filter(
                employee_id=self.parameters.get('employee_id'),
                date__gte=campaign_start_date,
                campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        elif self.parameters.get('organization_id'):
            transaction_history = PPCampaignBankTransactionLog.objects.filter(
                employee__organization_id=self.parameters.get('organization_id'),
                campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        else:
            transaction_history = PPCampaignBankTransactionLog.objects.filter(
                campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        print('TRANSACTION HISTORY', transaction_history)
        combined_dicts = combine_dicts(transaction_history, 'employee_id', strict=False,
                             concat_same_key=['transaction_date', 'transaction_points', 'transaction_dollars',
                                              'overall_sat', 'overall_sat_threshold', 'totally_satisfied_count'])
        print('COMBINED DICTS', combined_dicts)
        return combined_dicts

    def get_campaign_metrics(self):
        # Pushing up merged changes to prod
        '''
        [{'variable': ['driver_sat_points', 'kmi_sat_points', 'osat_sat_points'],
         'employee_id': 80513,
         'campaign_id': 1,
         'value': Decimal('40'),
         'employee_name': 'Christopher Wise ( N.W.OHIO CLUB FLEET )',
         'registration_date': datetime.datetime(2022, 3, 25, 0, 0, tzinfo=<UTC>),
         'organization_name': 'N.W. OHIO CLUB FLEET', 'organization_id': 455, 'campaign_name': 'SpringUp! 202
        2',
        'driver_sat_points': Decimal('40'),
        'kmi_sat_points': Decimal('30'),
        'osat_sat_points': Decimal('40')}]

        :return:
        '''
        annotation = {
            'employee_name': F('employee__display_name'),
            'registration_date': F('employee__campaign_registration__registration_date'),
            'organization_name': F('employee__organization__name'),
            'organization_id': F('employee__organization__id'),
            'campaign_name': F('campaign__title')
        }
        vals = ['employee_name', 'registration_date', 'organization_name', 'organization_id', 'employee_id',
                'campaign_name', 'campaign_id',
                'variable', 'value']

        is_individual = self.parameters.get('employee_id')

        if is_individual:
            point_metrics = PPCampaignPointsBreakdown.objects.filter(
                employee_id=self.parameters.get('employee_id'),
                campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        elif self.parameters.get('organization_id'):
            point_metrics = PPCampaignPointsBreakdown.objects.filter(
                employee__organization_id=self.parameters.get('organization_id'),
                campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        else:
            point_metrics = PPCampaignPointsBreakdown.objects.filter(
                campaign_id=self.parameters.get('campaign', 1)) \
                .annotate(**annotation).values(*vals)
        point_metrics = [d.update({d['variable']: d['value']}) or d for d in point_metrics]
        out = combine_dicts(point_metrics, 'employee_id', strict=False, concat_same_key='variable')
        print('out', out)

        if len(out) == 0:
            variable = PPCampaignPointsBreakdown.objects.filter(
                campaign_id=self.parameters.get('campaign', 1)).values_list('variable', flat=True).distinct()
            print(variable)
            if is_individual:
                new_out = {
                    'variable': variable,
                     'employee_id': self.emp.id,
                     'campaign_id': self.camp['id'],
                     'value': 0,
                     'registration_date': self.emp.campaign_registration.get(campaign_id=self.camp.get('id')).registration_date
                     }
                for v in variable:
                    new_out[v] = 0

                return [new_out]
            elif self.registered:
                out = []
                for emp in self.registered:
                    new_out = {
                        'variable': variable,
                        'employee_id': emp['employee_id'],
                        'campaign_id': self.camp['id'],
                        'value': 0,
                        'registration_date': emp['registration_date']
                    }
                    for v in variable:
                        new_out[v] = 0
                    out.append(new_out)
                return out
            else:
                return []

        else:
            return out
    # def get_campaign_points_metrics_transactions_driver(self, campaign_id, driver_id):
    #     self.parameters['campaign_id'] = campaign_id
    #     self.camp = PPCampaign.objects.filter(id=self.parameters.get('campaign_id')).values()[0]
    #     emp = Employee.objects.get(id=driver_id)
    #     self.emp = emp
    #     self.parameters['employee_id'] = driver_id
    #     self.parameters['campaign'] = campaign_id
    #     bank = self.get_campaign_points()
    #     metrics = self.get_campaign_metrics()
    #     transaction_history = self.get_campaign_transaction_history()
    #
    #     out = combine_dicts([bank, metrics, transaction_history], 'employee_id')
    #     if len(out) == 0:
    #         return []
    #
    #     for i, o in enumerate(out):
    #         print(o)
    #         if o.get('value'):
    #             del o['value']
    #         if o.get('preferred_email'):
    #             o['email'] = o.get('preferred_email')
    #             del o['preferred_email']
    #         elif 'preferred_email' in o:
    #             del o['preferred_email']
    #         o['module_name'] = o.get('module_name', [])
    #         o['transaction_date'] = o.get('transaction_date', [])
    #         o['transaction_points'] = o.get('transaction_points', [])
    #         o['transaction_dollars'] = o.get('transaction_dollars', [])
    def get_campaign_points_metrics_transactions(self):
        print(self.parameters)
        self.parameters['campaign_id'] = self.parameters.get('campaign_id', self.parameters.get('campaign', self.parameters.get('camp_id')))
        self.camp = PPCampaign.objects.filter(id=self.parameters.get('campaign_id')).values()[0]
        emp = Employee.objects.get(user=self.user)


        if emp.organization.type == 'Station-Business':
            self.parameters['organization_id'] = emp.organization.id

        bank = self.get_campaign_points()
        metrics = self.get_campaign_metrics()
        transaction_history = self.get_campaign_transaction_history()
        # modules = self.get_campaign_module_completion_history()

        print('bank', bank)
        print('metrics', metrics)
        print('transaction_history', transaction_history)
        out = combine_dicts([bank, metrics, transaction_history], 'employee_id')
        if (len(out) == 0):
            return []
        for i, o in enumerate(out):
            print(o)
            if o.get('value'):
                del o['value']
            if o.get('preferred_email'):
                o['email'] = o.get('preferred_email')
                del o['preferred_email']
            elif 'preferred_email' in o:
                del o['preferred_email']
            o['module_name'] = o.get('module_name', [])
            o['transaction_date'] = o.get('transaction_date', [])
            o['transaction_points'] = o.get('transaction_points', [])
            o['transaction_dollars'] = o.get('transaction_dollars', [])

        return out

    def create_or_update_campaign_metrics(self, employee, campaign, registration_date):
        start_date = campaign.start
        end_date = campaign.end
        current_date = start_date

        # while current_date <= end_date:
            # Check if the current month is the registration month
        is_registration_month = current_date.year == registration_date.year and current_date.month == registration_date.month
        defaults = {
            'registered': is_registration_month,
            'date': current_date,
            'completed_clips': 0 if is_registration_month else None,
            'overall_sat': None,
            'call_volume': None,
            'logins': None,
        }

        PPCampaignDriverMetricTrackingTable.objects.update_or_create(
            employee=employee,
            campaign=campaign,
            date=current_date,  # Ensure this date is handled as just year and month (first day of each month)
            defaults=defaults
        )

    def sign_up_to_campaign(self):

        # To Do: Check for campaign events to see if they are satisfied

        if self.parameters.get('user_id'):
            self.user = User.objects.get(id=self.parameters.get('user_id'))

        # checklist
        # get campaign
        camp_id = self.parameters.get('id', self.parameters.get('camp_id'))
        campaign = PPCampaign.objects.get(id=camp_id)
        # get employee using self.user
        employee = Employee.objects.get(user=self.user)

        registered_check = PPCampaignRegistration.objects.filter(employee=employee, campaign=campaign)

        if registered_check:
            return 'User already registered'
        # get profile using employee
        profile = Profile.objects.get(user=self.user)

        user_email = self.user.email
        # compare email given to profile email and if it's different then add the new email to campaign_preferred_email field in Profile
        payments_email = self.parameters.get('payments_email', user_email)
        if user_email != payments_email:
            profile.campaign_preferred_email = payments_email
            profile.save()

        if self.parameters.get('override_email'):
            print('were are overriding email')
            user = User.objects.get(id=self.user.id)
            user.email = payments_email
            user.save()
        # create a new CampaignUser using the information above

        # Get opt-in status for communications
        opt_in = self.parameters.get('communication_opt_in')


        new_campaign_user = PPCampaignRegistration.objects.create(
            campaign=campaign,
            employee=employee,
            registration_date=local_now(self.user).strftime('%Y-%m-%d %H:%M:%S'),
            communication_opt_in=opt_in
        )

        start_date = campaign.start
        end_date = campaign.end
        current_date = start_date

        while current_date <= end_date:
            data_for_month = {
                'completed_clips': None,
                'logins': None,
                'overall_sat': None,
                'call_volume': None,
                'registered': current_date.month == timezone.now().month and current_date.year == timezone.now().year
            }



            if data_for_month['registered'] and campaign.show_performance_metrics:
                data_for_month['completed_clips'] = update_completed_clips(campaign, employee)
                data_for_month['logins'] = update_logins(employee)
                data_for_month['overall_sat'] = update_overall_sat(employee, campaign)  # Assume this function exists
                data_for_month['call_volume'] = update_call_volume(employee, campaign)  # Assume this function exists
            print('data_for_month', data_for_month)
            PPCampaignDriverMetricTrackingTable.objects.create(
                employee=employee,
                campaign=campaign,
                date=current_date,
                **data_for_month
            )
            current_date += relativedelta(months=1)
        # self.create_or_update_campaign_metrics(employee, campaign, dt.datetime.today())



        return PPRegistrationSerializer(new_campaign_user).data

    def refresh_campaign_metrics(self, employee, campaign):
        current_month_start = timezone.now().date().replace(day=1)
        next_month_start = current_month_start + timezone.timedelta(days=32)
        next_month_start = next_month_start.replace(day=1)

        with transaction.atomic():
            # Fetch metrics for the current month only or where registered is True
            metrics = PPCampaignDriverMetricTrackingTable.objects.select_for_update().filter(
                employee=employee,
                campaign=campaign,
                date__range=(current_month_start, next_month_start - timezone.timedelta(days=1))
            )

            # Update each metric record with new data if within current month or registered is True
            for metric in metrics:
                if metric.registered or metric.date.year == timezone.now().year and metric.date.month == timezone.now().month:
                    metric.logins = update_logins(employee)
                    metric.completed_clips = update_completed_clips(campaign, employee)
                    metric.overall_sat = update_overall_sat(employee, campaign)  # Assume this function exists
                    metric.call_volume = update_call_volume(employee, campaign)  # Assume this function exists
                    metric.save()

    def get_campaign_table_metric_data(self):
        if self.parameters.get('employee_id'):
            employee = Employee.objects.get(id=self.parameters.get('employee_id'))
        else:
            employee = self.request.user.employee()

        campaign = PPCampaign.objects.get(id=self.parameters.get('campaign_id'))

        # Update metrics in the database
        self.refresh_campaign_metrics(employee, campaign)

        # Fetch updated metrics
        campaign_metrics = PPCampaignDriverMetricTrackingTable.objects.filter(employee=employee, campaign=campaign)
        return PPCampaignDriverMetricTrackingTableSerializer(campaign_metrics, many=True).data

    def get_all_employee_campaign_data(self):
        # THIS IS FOR MY TOOL KIT
        if self.parameters.get('employee_id'):
            self.emp = Employee.objects.get(id=self.parameters.get('employee_id'))
        else:
            self.emp = self.request.user.employee()

        if self.emp.group.filter(id=18).exists():
            return []

        eligible_campaigns = PPCampaign.objects.filter(geography_eligiblity__in=[self.emp.organization], active=True)
        eligible_campaigns = PPCampaignSerializer(eligible_campaigns, many=True).data
        completed_modules = list(ModuleCompletion.objects.filter(employee=self.emp).values_list('module_id', flat=True))
        registered_campaigns = list(
            PPCampaignRegistration.objects.filter(employee=self.emp).values_list('campaign_id', flat=True))
        print('completed_modules', completed_modules)
        print('registered_campaigns', registered_campaigns)
        for campaign in eligible_campaigns:
            print(campaign)
            self.camp = campaign
            required_modules = [m['id'] for m in campaign['registration_requirements']]

            #TODO: This needs to be fixed and then the frontend needs to be updated. See line 39 in my-toolkit
            # campaign/actions uncomment the getCampaignData dispatch

            # if dt.datetime.strptime(campaign.get('start'), '%Y-%m-%d') > dt.datetime.today():
            #     campaign['registered'] = campaign['id'] in registered_campaigns
            #     continue


            if campaign['id'] in registered_campaigns:
                print('REGISTERED', campaign)
                self.parameters['campaign_id'] = campaign['id']
                campaign['performance_data'] = self.get_campaign_points_metrics_transactions()
                campaign['registration_date'] = PPCampaignRegistration.objects.filter(employee=self.emp, campaign_id=campaign['id']).values_list('registration_date', flat=True).first()
                campaign['registered'], campaign['canRegister'], campaign['cantRegisterReason'] = True, True, None
                for i, module in enumerate(campaign['registration_requirements']):
                    campaign['registration_requirements'][i]['completed'] = True
            else:

                print('required_modules', required_modules, completed_modules)

                if all(required in completed_modules for required in required_modules):
                    for i, module in enumerate(campaign['registration_requirements']):
                        campaign['registration_requirements'][i]['completed'] = \
                        campaign['registration_requirements'][i]['id'] in completed_modules
                    campaign['registered'], campaign['canRegister'], campaign['cantRegisterReason'] = False, True, None
                else:
                    for i, module in enumerate(campaign['registration_requirements']):
                        campaign['registration_requirements'][i]['completed'] = \
                        campaign['registration_requirements'][i]['id'] in completed_modules
                    campaign['registered'], campaign['canRegister'], campaign[
                        'cantRegisterReason'] = False, False, "Please Complete Modules to Register"

            # campaign_tags = ModuleTag.objects.filter(campaign_id=campaign['id'], type='campaign')
            # associated_modules = ShortModuleOverviewSerializer(ModuleOverview.objects.filter(tags__in=campaign_tags),
            #                                                    many=True)
            # print('Associated Modules', associated_modules)
            # campaign['associated_modules'] = []
            # for m in associated_modules.data:
            #     m['required'] = m['id'] in required_modules
            #     campaign['associated_modules'].append(m)

        return eligible_campaigns

    def create_create_campaign_transaction(self):

        ####

        SPEND_MINIMUM = 0

        ####

        new_log = {
            "employee_id": self.parameters['employee_id'],
            "campaign_id": self.parameters['campaign_id'],
            "points": self.parameters['not_cashed_points'],
            "dollars": self.parameters['not_cashed_points'],
            # this needs to change to some sort of conversion eventually!
        }

        ### make a fast app payment here...

        if not self.parameters.get('email'):
            return {'status': 'error', 'errorMessage': "Email is required for Payment!"}

        if new_log['dollars'] <= SPEND_MINIMUM:
            return {'status': 'error', 'errorMessage': "Spend is too low to qualify"}

        campaign = PPCampaign.objects.get(id=self.parameters.get('campaign_id'))

        try:
            payments = PaymentMethods(
                user=self.user,
                testing=False,
                payment_limit=1000,  # should this be different?
                payment_amount=self.parameters['not_cashed_points'],
                payment_to=self.parameters['employee_id'],
                tremendous_campaign=campaign.tremendousCampaign,
                ppcampaign=campaign,
                recipient_email=self.parameters.get('email'),
                reason=f'{campaign.title} Campaign Payment',
                notes=f'{campaign.title} Campaign Payment',
            )

            payment_info = payments.create_transaction()
        except Exception as e:
            raise Exception(e)
            return {'status': 'error', 'errorMessage': str(e)}
        print(payment_info)
        new_log['paymentLog_id'] = payment_info['payment_log']['id']

        try:
            created_log = PPCampaignBankTransactionLog.objects.create(**new_log)
            created_log = PPCampaignTransactionlogSerializer(created_log).data
            created_log['status'] = 'completed'
        except Exception as e:
            created_log = {'status': 'error', 'errorMessage': str(e)}
        return created_log

    # def get_campaign_drivers(self):
    #     user_emp = self.user.employee()
    #     # thirty_days_out = dt.datetime.now() - dt.timedelta(days=30)
    #     camp = PPCampaign.objects.get(slug=self.parameters.get('camp_slug'))
    #     print('campaign id', camp.id)
    #     available_drivers = CampaignRegistrationStatusView2023.objects.all().values_list('id', flat=True)
    #     registered_drivers = PPCampaignRegistration.objects.filter(campaign_id=camp.id).values_list('employee_id', flat=True)
    #     field_consultants_list = Organization.objects.filter(parallel_parent_stream='management').values_list('name', flat=True)
    #     # field_consultants = [{'id': f.id, 'name': f.name, 'pp': f.parallel_parents.all()} for f in field_consultants]
    #     # print(field_consultants)
    #     march_range = [dt.datetime(2024, 3, 1, 0, 0, 0), dt.datetime(2024, 3, 31, 23, 59, 59)]
    #     april_range = [dt.datetime(2024, 4, 1, 0, 0, 0), dt.datetime(2024, 4, 30, 23, 59, 59)]
    #     # august_range = [dt.datetime(2023, 8, 1, 0, 0, 0), dt.datetime(2023, 8, 31, 23, 59, 59)]
    #     eligible_drivers = Employee.objects.filter(id__in=available_drivers)
    #     if user_emp.position_type == 'Station-Admin':
    #         eligible_drivers = eligible_drivers.filter(organization_id=user_emp.organization.id)
    #
    #     eligible_drivers = eligible_drivers.exclude(organization__facility_type__icontains='Fleet')\
    #         .annotate(driver_id=F('raw_data_driver_id'))\
    #         .values('driver_id')\
    #         .annotate(station=F('organization__name'),
    #                   employee_id=F('id'),
    #                   username=F('user__username'),
    #                   email=F('user__email'),
    #                   registration_date=Case(When(Q(campaign_registration__campaign_id__id=camp.id), then=F('campaign_registration__registration_date'))),
    #                   field_consultant=F('organization__parallel_parents__name'),
    #                   registered=Case(
    #                       When(id__in=registered_drivers, then=Value('Yes')),
    #                       default=Value('No')),
    #                   mar_overall_sat=Case(When(Q(campaign_bank_log_employee__date__range=march_range), then=F('campaign_bank_log_employee__overall_sat'))),
    #                   mar_totally_sat_survey=Case(When(Q(campaign_bank_log_employee__date__range=march_range), then=F('campaign_bank_log_employee__points') / 5.0)),
    #                   mar_potential_payment=Case(When(Q(campaign_bank_log_employee__date__range=march_range), then=F('campaign_bank_log_employee__points'))),
    #                   mar_actual_payment=Case(When(Q(campaign_bank_log_employee__date__range=march_range), then=F('campaign_bank_log_employee__dollars'))),
    #                   apr_overall_sat=Case(When(Q(campaign_bank_log_employee__date__range=april_range), then=F('campaign_bank_log_employee__overall_sat'))),
    #                   apr_totally_sat_survey=Case(When(Q(campaign_bank_log_employee__date__range=april_range),  then=F('campaign_bank_log_employee__points') / 5.0)),
    #                   apr_potential_payment=Case(When(Q(campaign_bank_log_employee__date__range=april_range), then=F('campaign_bank_log_employee__points'))),
    #                   apr_actual_payment=Case(When(Q(campaign_bank_log_employee__date__range=april_range), then=F('campaign_bank_log_employee__dollars'))),
    #
    #                   )\
    #         .values('id', 'employee_id',
    #                 'organization_id', 'full_name', 'driver_id', 'station',
    #                 'registered', 'registration_date',
    #                 'field_consultant',
    #                 'username', 'email',
    #                 'mar_overall_sat',
    #                 'mar_totally_sat_survey',
    #                 'mar_potential_payment',
    #                 'mar_actual_payment',
    #                 'apr_overall_sat',
    #                 'apr_totally_sat_survey',
    #                 'apr_potential_payment',
    #                 'apr_actual_payment'
    #         )
    #
    #     # transaction_logs = PPCampaignBankTransactionLog.objects.filter(campaign_id=camp.id).annotate(
    #     #               june_overall_sat=Case(When(Q(date__range=march_range), then=F('overall_sat'))),
    #     #               july_overall_sat=Case(When(Q(date__range=april_range), then=F('overall_sat'))),
    #     #               august_overall_sat=Case(When(Q(date__range=august_range), then=F('overall_sat'))),
    #     # )
    #
    #     # [e.update({'june_overall_sat': None}) for e in eligible_drivers if e['employee_id'] not in transaction_logs.values_list('employee_id', flat=True)]
    #     # eligible_drivers = combine_dicts([eligible_drivers, transaction_logs.values()], 'employee_id')
    #     # registered_drivers = [x for x in eligible_drivers if x['registered'] == 'Yes']
    #     # unregistered_drivers = [x for x in eligible_drivers if x['registered'] == 'No']
    #     # reg_drivers_id = [x['id'] for x in registered_drivers]
    #     #
    #     # bank_details = PPCampaignBank.objects.filter(employee_id__in=reg_drivers_id)\
    #     #     .values('employee_id', 'campaign_id', 'total_points', 'cashed_points', 'cashed_points_dollars', 'not_cashed_points')
    #     #
    #     # unregistered_drivers = [
    #     #     {'employee_id': x['employee_id'],
    #     #      'campaign_id': camp.id,
    #     #      'total_points': None,
    #     #      'cashed_points': None,
    #     #      'cashed_points_dollars': None,
    #     #      'not_cashed_points': None} for x in unregistered_drivers]
    #     # all_drivers = combine_dicts([registered_drivers, bank_details, unregistered_drivers], 'employee_id')
    #     # for e in eligible_drivers:
    #     #     if e['registered'] == 'Yes':
    #     #         e['performance_data'] = self.get_campaign_points_metrics_transactions_driver(camp.id, e['id'])
    #     #     else:
    #     #         e['performance_data'] = []
    #     output = [e for e in eligible_drivers if e['field_consultant'] in field_consultants_list]
    #     return {'out': output, 'campaign_details': PPCampaignSerializer(camp).data}

    def get_campaign_drivers(self):
        user_emp = self.user.employee()
        camp = PPCampaign.objects.get(slug=self.parameters.get('camp_slug'))
        print('campaign id', camp.id)
        output = SpringUp2024DriverTable.objects.all().values()

        return {'out': output, 'campaign_details': PPCampaignSerializer(camp).data}

    def get_campaign_driver(self):
        user_emp = self.user.employee()
        camp = PPCampaign.objects.get(slug=self.parameters.get('camp_slug'))
        print('campaign id', camp.id)
        output = SpringUp2024DriverTable.objects.filter(employee_id=user_emp.id).values()

        return {'out': output, 'campaign_details': PPCampaignSerializer(camp).data}

    def get_campaign_driver_payment_details(self, dates, emp):
        pass
    # def get_campaign_drivers(self):
    #     user_emp = self.user.employee()
    #     camp = PPCampaign.objects.get(id=self.parameters['camp_id'])
    #
    #     if user_emp.organization.type == 'Station-Business':
    #         camp_orgs = camp.geography_eligiblity.filter(id=user_emp.organization.id)
    #     elif user_emp.organization.type == 'Territory':
    #         camp_orgs = camp.geography_eligiblity.filter(parent=user_emp.organization)
    #     else:
    #         camp_orgs = camp.geography_eligiblity.all()
    #
    #     reg = PPCampaignRegistration.objects.filter(campaign=camp).values('employee_id', 'registration_date')
    #     cutoff = camp.start - dt.timedelta(days=30)
    #
    #     emps = Employee.objects.filter(
    #         driver_stationDriver__last_sc_dt__gte=cutoff,
    #         organization__in=camp_orgs
    #
    #     ).exclude(group__id__in=[18]).annotate(
    #         organization_name=F('organization__name'),
    #         email=F('user__email'),
    #         last_call=F('driver_stationDriver__last_sc_dt'),
    #         last_login=F('profile__last_activity'),
    #         username=F('user__username'),
    #         territory=F('organization__parent__name'),
    #         campaign_email=F('profile__campaign_preferred_email')
    #     ).values(
    #         'id',
    #         'user_id',
    #         'email',
    #         'username',
    #         'position_type',
    #         'display_name',
    #         'login_id',
    #         'full_name',
    #         'last_call',
    #         'organization_name',
    #         'last_login',
    #         'territory',
    #         'user_id',
    #         'campaign_email'
    #     )
    #     for e in emps:
    #         registered = next((x['registration_date'] for x in reg if x['employee_id'] == e['id']), None)
    #         e['registered'] = registered
    #
    #     return emps

    def exclude_campaign_groups(self):
        g = EmployeeGroup.objects.get(group_name='Campaign Ineligible')
        for e in self.parameters.get('employee_ids'):
            e = Employee.objects.get(id=e)
            e.group.add(g)
            e.save()
    # def get_campaign_raw_records(self):
    #     survey_fields = ['sc_dt_surveys', 'overall_sat', 'keeping_informed_sat']
    #     return Std12ERaw.objects.filter(**self.parameters['filters'])
