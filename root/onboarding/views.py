from django.shortcuts import render
import sys
sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from .serializers import *
from accounts.models import *
from dashboard.models import *
from .models import *
from django.forms.models import model_to_dict
from django.template.loader import render_to_string
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from .googleAnalytics import get_user_session_counts
from .googleAnalytics import get_metric as get_metric_ga
from .googleAnalytics import get_user_data as get_user_data_ga
from .googleAnalytics import get_user_list_session_counts as get_user_list_session_counts_ga
from django.db.models import F, Case, When, Value, CharField, Max, Min
from django.db.models import Q
from django.db.models.functions import Extract, Concat
from django.db.models.query import QuerySet
from datetime import datetime, timedelta, date
from django.conf import settings
from django.utils.timezone import make_aware
from django.db.models.functions import (TruncDate, TruncDay, TruncHour, TruncMinute, TruncSecond)
import time
from django.db.models.fields import DateField
from itertools import groupby
from django.db.models.functions import ExtractMonth, ExtractYear
from payments.models import *
from root.utilities import combine_dicts, flatten_list_of_lists, list_of_dicts_key_order, Round



class ProductUsage(generics.GenericAPIView):

    """
    spec:
        given a user how many visits to site and to satapp
        given a user how many visits to maps and scheduler
        include ability to specify a time range, or just a last visit
        return a dict
        working with query sets
            main qa is auth-user (maybe just user)
            from authentication.models import User
        tip: default to return all of this unless otherwise specified
        UserActions.objects.filter(user=self.request.user).values()
    """
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()
    serializer_class = None
    www_authenticate_realm = 'api'



    def __init__(self):
        self.purpose_router = {
            'get_usage': self.get_usage,
        }
        one_day = timedelta(days=1)
        self.today = make_aware(datetime.today())
        self.first_of_this_month = datetime(self.today.year, self.today.month, 1)
        self.first_of_last_month = datetime((self.first_of_this_month - one_day).year, (self.first_of_this_month - one_day).month, 1)
        self.data_points_limits = {
                                       'DAYS': 62,
                                       'WEEKS': 52,
                                       'MONTHS': 24,
                                       'YEARS': 5
                                   }

    def remove_period(self, data_by_period):
        first_period_string = self.start_of_first_period.strftime('%Y-%m-%d 00:00:00')
        to_remove = []

        # find elements to remove
        for i in range(len(data_by_period)):
            if data_by_period[i]['label'] == first_period_string:
                to_remove.append(i)

        # remove elements
        for item in to_remove:
            data_by_period.pop(item)

        return data_by_period

    def format_queryset(self, qs, groupname, time_type, datewise_data_holder):
        fifty_third_week = {"value": 0}
        cleaned_data_by_period = []
        for d in qs:

            # the week numbers work on the iso week system, which means there is sometimes a 53rd week in a year. This if statement accounts for that.
            if 'W53' in d['label']:
                fifty_third_week['value'] += d['value']
                fifty_third_week['label'] = str(datetime.strptime(str(datetime.today().year - 1) + "-W53-1", "%G-W%V-%u"))
                fifty_third_week['anomaly'] = 0
                fifty_third_week['value_type'] = 'number'
                fifty_third_week['date'] = fifty_third_week['label'][:10]

                datewise_data_holder.setdefault(fifty_third_week['label'], {groupname:0})
                datewise_data_holder[fifty_third_week['label']][groupname] = fifty_third_week['value']

            if 'W53' not in d['label'] and d['label'] != "-W":
                d['label'] = str(datetime.strptime(d['label'] + '-1', "%G-W%V-%u"))
                d['anomaly'] = 0
                d['value_type'] = 'number'
                d['date'] = d['label'][:10]
                cleaned_data_by_period.append(d)

                datewise_data_holder.setdefault(d['label'], {groupname:0})
                datewise_data_holder[str(d['label'])][groupname] = d['value']

        if len(fifty_third_week) > 1:
            cleaned_data_by_period.append(fifty_third_week)

        # The first item in cleared_data_by_period _should_ be the first period, which we want to discard by default.
        # This is a check to skip it to avoid publishing incomplete data periods
        # This isnt the best way to do this because we reduce the size of the list that we are iterating over, so unless
        #   we do something hacky like use break we will get an out of bounds error.
        if self.skip_first_period:
            cleaned_data_by_period = self.remove_period(cleaned_data_by_period)

        group_dataset = {
            'groupName': groupname,
            'time_type': time_type,
            'error': False,
            'warning': False,
            'data': cleaned_data_by_period
        }
        return (group_dataset,datewise_data_holder)

    def divide_and_format_datewise_data(self, datewise_data_holder, groupname, timetype, numerator, denominator):

        data_list = []
        sorted_date_list = sorted([i for i in datewise_data_holder],reverse=True)

        for period in sorted_date_list:
            data_dict = {}
            try:
                data_dict['value'] = datewise_data_holder[period][numerator] / datewise_data_holder[period][denominator]
                data_dict['label'] = period
                data_dict['anomaly'] = 0
                data_dict['value_type'] = 'number'
                data_dict['date'] = data_dict['label'][:10]

            except:
                data_dict['value'] = 0
                data_dict['label'] = period
                data_dict['anomaly'] = 0
                data_dict['value_type'] = 'number'
                data_dict['date'] = data_dict['label'][:10]

            data_list.append(data_dict)

        if self.skip_first_period:
            data_list = self.remove_period(data_list)

        group_dataset = {
            'groupName': groupname,
            'time_type': timetype,
            'error': False,
            'warning': False,
            'data': data_list
        }

        return group_dataset


    def format_datewise_data(self, datewise_data_holder, groupname, timetype):

        data_list = []
        sorted_date_list = sorted([i for i in datewise_data_holder],reverse=True)

        for period in sorted_date_list:
            data_dict = {}
            try:
                data_dict['value'] = datewise_data_holder[period][groupname]
                data_dict['label'] = period
                data_dict['anomaly'] = 0
                data_dict['value_type'] = 'number'
                data_dict['date'] = data_dict['label'][:10]

            except:
                data_dict['value'] = 0
                data_dict['label'] = period
                data_dict['anomaly'] = 0
                data_dict['value_type'] = 'number'
                data_dict['date'] = data_dict['label'][:10]

            data_list.append(data_dict)

        if self.skip_first_period:
            data_list = self.remove_period(data_list)

        group_dataset = {
            'groupName': groupname,
            'time_type': timetype,
            'error': False,
            'warning': False,
            'data': data_list
        }

        return group_dataset

    def get_usage(self, parameters):
        result = {}
        print('parameters:', parameters)

        # single employee case
        if "employee_id" in parameters:
            user_stats = ProductUsageUser.objects.filter(employee_id=parameters.get("employee_id"))
            for row in user_stats:
                result[row.action_taken] = {
                    "employee_id": row.employee_id,
                    "total_logins": row.total_logins,
                    "last_login_date": row.last_login_date,
                    "logins_last_14_days": row.logins_last_14_days,
                }
            return result

        # org case
        elif "organization_id" in parameters:
            # set time_type

            if "skip_first_period" in parameters:
                self.skip_first_period = parameters.get("skip_first_period")
                assert isinstance(self.skip_first_period, bool), 'CUSTOM EXCEPTION: skip_first_period must be True or False'
            else:
                self.skip_first_period = True

            if "time_type" in parameters:
                allowable_time_types = ['WEEKS']
                # putting this in for future use
                # allowable_time_types + ['MONTHS', 'WEEKS', 'YEARS']
                time_type = parameters.get("time_type")
                assert time_type in allowable_time_types, 'CUSTOM EXCEPTION: time type not in {}'.format(','.join(allowable_time_types))
            else:
                time_type = 'WEEKS'

            # TODO add logic to get the date for the first instance of any given time type
            if "start_date" in parameters:
                start_date = parameters.get('start_date')
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                except:
                    raise ValueError("Incorrect start date format. Must be YYYY-MM-DD.")
                assert datetime.strptime(start_date, '%Y-%m-%d') <= datetime.today(), 'CUSTOM EXCEPTION: start date cannot be before today.'
            else:
                start_date = datetime.strftime(self.today, "%Y-%m-%d")
            #finally!
            self.start_of_first_period = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=datetime.strptime(start_date, '%Y-%m-%d').weekday())
            print('start_of_first_period: ' + str(type(self.start_of_first_period)))
            # set data points
            if "data_points" in parameters:
                if "end_date" in parameters:
                    raise ValueError("CUSTOM EXCEPTION: Can not pass both end_date AND data_points.")
                data_points = parameters.get('data_points')
                assert type(data_points) == int, 'CUSTOM EXCEPTION: data points not an int'
                assert data_points <= self.data_points_limits[time_type], 'CUSTOM EXCEPTION: too many data points requested for time type {}. Max is {}.'.format(time_type, self.data_points_limits[time_type])
            else:
                data_points = 12
            #finally!
            #TODO generalize this to use any time type
            self.start_of_final_period = self.start_of_first_period - timedelta(**{time_type.lower():data_points})
            print(self.start_of_final_period)



            if "end_date" in parameters:
                if "data_points" in parameters:
                    raise ValueError("CUSTOM EXCEPTION: Can not pass both end_date AND data_points.")
                end_date = parameters.get('end_date')
                try:
                    datetime.strptime(end_date, '%Y-%m-%d')
                except:
                    raise ValueError("Incorrect end date format. Must be YYYY-MM-DD.")

                self.start_of_final_period = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=datetime.strptime(end_date, '%Y-%m-%d').weekday())

                # TODO generalize this for any time type
                data_points = (self.start_of_first_period - self.start_of_final_period).days / 7

                assert data_points <= self.data_points_limits[time_type], f'CUSTOM EXCEPTION: End Date must be {self.data_points_limits[time_type]} or fewer {time_type} away.'

            if "end_date" in parameters and "start_date" in parameters:
                assert start_date > end_date, "CUSTOM EXCEPTION: start_date must be after end_date."


            ##########################################
            organization_id = parameters.get("organization_id")
            assert type(organization_id) == int, 'CUSTOM EXCEPTION: given organization_id is not an int.'
            organization = Organization.objects.get(id=organization_id)
            organization_type = organization.type

            if organization_type == 'Station':
                employees = organization.employees('')
            elif organization_type == 'Station-Business':
                employees = Employee.objects.filter(organization=organization_id)
            elif organization_type == 'Territory':
                employees = Employee.objects.filter(organization__parent__id=organization_id)
            elif organization_type == 'Market':
                employees = Employee.objects.filter(organization__parent__parent__id=organization_id)
            elif organization_type == 'Club-Region':
                employees = Employee.objects.filter(organization__parent__parent__parent__id=organization_id)
            elif organization_type == 'Club':
                employees = Employee.objects.filter(organization__parent__parent__parent__parent__id=organization_id)
            else:
                return(result)

            ##########################################
            # filters

            filter_d = {}

            # user type filter
            allowable_position_types = Employee.objects.values_list('position_type', flat=True).distinct()

            if "user_type" in parameters:
                user_type = parameters.get("user_type")
                assert user_type in allowable_position_types, 'CUSTOM EXCEPTION: user type not in {}'.format(','.join(allowable_position_types))
                employees = employees.filter(position_type__exact=user_type)


            # station volume filter
            if "station_volume" in parameters:
                station_volume = parameters.get('station_volume')
                allowable_volume_ranges = ['lt_500', 'gte_500_lte_1000', 'gt_1000']
                assert station_volume in allowable_volume_ranges, 'CUSTOM EXCEPTION: station_volume parameter not in {}'.format(','.join(allowable_volume_ranges))

                filter_d.update({
                    'index_type': 'ORG_BUSINESS_ID',
                    'time_type': 'M',
                    # always generate volume according to the month before now (self.first_of_last_month).
                    # This way the same orgs will show up for date ranges which overlap, but have different start dates.
                    'sc_dt':self.first_of_last_month
                })

                if station_volume == 'lt_500':
                    filter_d.update({
                        'volume__lt': 500
                    })
                elif station_volume == 'gte_500_lte_1000':
                    filter_d.update({
                        'volume__gte': 500,
                        'volume__lte': 1000,
                    })
                elif station_volume == 'gt_1000':
                    filter_d.update({
                        'volume__gt': 1000
                    })

            # provider type filter
            if 'provider_type' in parameters:
                provider_type = parameters.get('provider_type')
                allowable_provider_types = ['FLEET', 'PSP', 'NON-PSP', 'CSN']

                assert provider_type in allowable_provider_types, 'CUSTOM EXCEPTION: provider_type parameter not in {}'.format(','.join(allowable_provider_types))
                if provider_type == 'CSN':
                    filter_d.update({
                        'organization__facility_type_parent__facility_type__in': ['PSP', 'NON-PSP']
                    })

                else:
                    filter_d.update({
                        'organization__facility_type_parent__facility_type__iexact': provider_type
                    })

            if len(filter_d) > 0:
                filtered_station_businesses = DashboardAggregations.objects.filter(**filter_d).values_list('organization_id', flat=True).distinct()
                filtered_station_businesses_int = [int(i) for i in filtered_station_businesses] # DashboardAggregations returns floats for organization_id. For speed, we want int's.
                employees = employees.filter(organization_id__in=filtered_station_businesses_int)


            # develop stats
            # init variables
            total_new_users = 0
            total_new_drivers = 0
            total_new_driver_users = 0

            datewise_data_holder = {}
            final_output = []

            # querysets
            # check permissions
            scheduler_permission_id_can_see = [18,19]
            scheduler_permission_id_can_edit = [17]

            users = employees.filter(user_id__isnull=False)
            drivers = employees.filter(position_type='Driver')
            driver_users = drivers.filter(user_id__isnull=False)
            scheduler_employees_can_see = employees.filter(permission__in=scheduler_permission_id_can_see)
            scheduler_employees_can_edit = employees.filter(permission__in=scheduler_permission_id_can_edit)

            user_actions = UserActions.objects

            total_users = users.filter(latest_activity_on__lte=start_date).count()
            total_drivers = drivers.filter(latest_activity_on__lte=start_date).count()
            total_driver_users = driver_users.filter(latest_activity_on__lte=start_date).count()

            print("total_drivers: ", total_drivers)
            print("total_users: ", total_users)
            print("total_driver_users: ", total_driver_users)


            # satapp usage

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            drivers_by_period = drivers.filter(latest_activity_on__range=(self.start_of_final_period, start_date))\
                                       .annotate(period=Extract('latest_activity_on', 'week'),year=Extract('latest_activity_on', 'year'))\
                                       .values('year', 'period')\
                                       .annotate(value=Count('period'), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                       .order_by('-year', '-period')\
                                       .values('value', 'label')

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            driver_users_by_period = drivers.filter(user_id__date_joined__range=(self.start_of_final_period, start_date))\
                                            .annotate(period=Extract('user_id__date_joined', 'week'), year=Extract('user_id__date_joined', 'year'))\
                                            .values('year','period')\
                                            .annotate(value=Count('period'), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                            .order_by('-year', '-period')\
                                            .values('value', 'label')

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            distinct_driver_app_users_by_period = UserActions.objects.filter(date__range=(self.start_of_final_period, start_date))\
                                                                     .filter( user_id__in=driver_users.values_list('user_id', flat=True), type='App Login')\
                                                                     .annotate(period=Extract('date', 'week'), year=Extract('date', 'year'))\
                                                                     .values('year', 'period')\
                                                                     .annotate(value=Count('user_id', distinct=True), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                                                     .order_by('-year', '-period')\
                                                                     .values('value', 'label')

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            satapp_views_by_period = UserActions.objects.filter(date__range=(self.start_of_final_period, start_date))\
                                                        .filter(user_id__isnull=False, user_id__in=employees.values_list('user_id', flat=True), type='App Login') \
                                                        .annotate(period=Extract('date', 'week'), year=Extract('date', 'year')) \
                                                        .values('year', 'period') \
                                                        .annotate(value=Count('user_id'), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                                        .order_by('-year', '-period')\
                                                        .values('value', 'label')

            # scheduler usage

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            users_by_period = employees.filter(user_id__date_joined__range=(self.start_of_final_period, start_date))\
                                       .annotate(period=Extract('user_id__date_joined', 'week'), year=Extract('user_id__date_joined', 'year'))\
                                       .values('year','period')\
                                       .annotate(value=Count('period'), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                       .order_by('-year', '-period')\
                                       .values('value', 'label')

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            scheduler_users_can_see_by_period = UserActions.objects.filter(date__range=(self.start_of_final_period, start_date))\
                                                           .filter(user_id__isnull=False, user_id__in=scheduler_employees_can_see.values_list('user_id', flat=True), type='Scheduler') \
                                                           .annotate(period=Extract('date', 'week'), year=Extract('date', 'year')) \
                                                           .values('year', 'period') \
                                                           .annotate(value=Count('user_id', distinct=True), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                                           .order_by('-year', '-period')\
                                                           .values('value', 'label')

            # TODO Generalize the period extraction to get any time type by making the time type user definable
            scheduler_users_can_edit_by_period = UserActions.objects.filter(date__range=(self.start_of_final_period, start_date))\
                                                           .filter(user_id__isnull=False, user_id__in=scheduler_employees_can_edit.values_list('user_id', flat=True), type='Scheduler') \
                                                           .annotate(period=Extract('date', 'week'), year=Extract('date', 'year')) \
                                                           .values('year', 'period') \
                                                           .annotate(value=Count('user_id', distinct=True), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                                           .order_by('-year', '-period')\
                                                           .values('value', 'label')

            # print(scheduler_users_by_period.query)
            # a = 1/0

            # maps usage
            # TODO Generalize the period extraction to get any time type by making the time type user definable
            maps_users_by_period = UserActions.objects.filter(date__range=(self.start_of_final_period, start_date))\
                                                      .filter(user_id__isnull=False, user_id__in=employees.values_list('user_id', flat=True), type='Maps') \
                                                      .annotate(period=Extract('date', 'week'), year=Extract('date', 'year')) \
                                                      .values('year', 'period') \
                                                      .annotate(value=Count('user_id', distinct=True), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                                      .order_by('-year', '-period')\
                                                      .values('value', 'label')

            # rdb usage
            # TODO Generalize the period extraction to get any time type by making the time type user definable
            login_users_by_period = UserActions.objects.filter(date__range=(self.start_of_final_period, start_date))\
                                                       .filter(user_id__isnull=False, user_id__in=employees.values_list('user_id', flat=True), type='Web Login') \
                                                       .annotate(period=Extract('date', 'week'), year=Extract('date', 'year')) \
                                                       .values('year', 'period') \
                                                       .annotate(value=Count('user_id', distinct=True), label=Concat(Cast('year', CharField()), Value('-W'), Cast('period', CharField())))\
                                                       .order_by('-year', '-period')\
                                                       .values('value', 'label')


            print("MAX: ", drivers_by_period.aggregate(Max("latest_activity_on")))
            print("Min: ", drivers_by_period.aggregate(Min("latest_activity_on")))

            base_data, datewise_data = self.format_queryset(drivers_by_period,'drivers_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(driver_users_by_period, 'driver_users_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(distinct_driver_app_users_by_period, 'distinct_driver_app_users_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(satapp_views_by_period, 'satapp_views_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(users_by_period, 'users_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(scheduler_users_can_see_by_period, 'scheduler_users_can_see_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(scheduler_users_can_edit_by_period, 'scheduler_users_can_edit_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(maps_users_by_period, 'maps_users_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            base_data, datewise_data = self.format_queryset(login_users_by_period, 'login_users_by_period', time_type, datewise_data_holder)
            final_output.append(base_data)
            datewise_data_holder = datewise_data

            # We are only able to get new drivers and users each period, not a running total
            # the following look calculates each period's total by subtracting backwards

            sorted_date_list = sorted([i for i in datewise_data_holder],reverse=True)
            print(sorted_date_list)

            new_drivers_this_period = 0
            new_driver_users_this_period = 0
            new_users_this_period = 0
            for period in sorted_date_list:

                datewise_data_holder[period]['cume_users'] = max(total_users - total_new_users, 0)
                datewise_data_holder[period]['cume_drivers'] = max(total_drivers - total_new_drivers, 0)
                datewise_data_holder[period]['cume_driver_users'] = max(total_driver_users - total_new_driver_users, 0)

                try:
                    new_drivers_this_period = datewise_data_holder[period]['drivers_by_period']
                except:
                    new_drivers_this_period = new_drivers_this_period

                try:
                    new_driver_users_this_period = datewise_data_holder[period]['driver_users_by_period']
                except:
                    new_driver_users_this_period = new_driver_users_this_period

                try:
                    new_users_this_period = datewise_data_holder[period]['users_by_period']
                except:
                    new_users_this_period =new_users_this_period

                total_new_users += new_users_this_period
                total_new_drivers += new_drivers_this_period
                total_new_driver_users += new_driver_users_this_period

            final_output.append(self.format_datewise_data(datewise_data_holder, 'cume_users', time_type))
            final_output.append(self.format_datewise_data(datewise_data_holder, 'cume_drivers', time_type))
            final_output.append(self.format_datewise_data(datewise_data_holder, 'cume_driver_users', time_type))

            final_output.append(self.divide_and_format_datewise_data(datewise_data_holder, 'pcnt_drivers_with_user_acnts', time_type, 'cume_driver_users', 'cume_drivers'))
            final_output.append(self.divide_and_format_datewise_data(datewise_data_holder, 'pcnt_drivers_with_user_acnts_using_app', time_type, 'distinct_driver_app_users_by_period', 'cume_driver_users'))
            final_output.append(self.divide_and_format_datewise_data(datewise_data_holder, 'pcnt_scheduler_users_can_see_by_period', time_type,  'scheduler_users_can_see_by_period', 'cume_users'))
            final_output.append(self.divide_and_format_datewise_data(datewise_data_holder, 'pcnt_scheduler_users_can_edit_by_period', time_type, 'scheduler_users_can_edit_by_period', 'cume_users'))
            final_output.append(self.divide_and_format_datewise_data(datewise_data_holder, 'pcnt_users_using_maps', time_type, 'maps_users_by_period', 'cume_users'))
            final_output.append(self.divide_and_format_datewise_data(datewise_data_holder, 'pcnt_users_using_rdb', time_type, 'login_users_by_period', 'cume_users'))

            # print('final_output: ', final_output)
            return final_output

        else:
            final_output = 'Please specify the employee or facility'
        return final_output

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            output = self.purpose_router[data['purpose']](data['parameters'])
            return Response(output, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            if 'CUSTOM EXCEPTION' in str(e):
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)




class Feedback(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()
    serializer_class = None
    www_authenticate_realm = 'api'


    def email_feedback(self):

        if 'tech_id' in self.data:
            t_id=self.data['tech_id']
        else:
            t_id=''

        message = render_to_string('onboarding/feedback_email.html', {
            'first_name': self.data['first_name'],
            'last_name': self.data['last_name'],
            'user': self.user,
            'email': self.data['email'],
            'tech_id': t_id,
            'explanation': self.data['explanation']
        })
        print("SENT INVITE EMAIL TO: ", self.email)
        mail_subject = "[AAA NE] Contact Form Message from" + self.data['first_name'] + ' ' + self.data['last_name']
        email = EmailMessage(mail_subject, message, 'feedback-aaane@wageup.com', to=self.email)
        email.send()

    def log_error(self):
        obj = {
            'error': self.data['error']
        }

        if self.data['context']:
            obj['context'] = self.data['context']

        if not self.user.is_anonymous:
            obj['user'] = self.user

        ErrorLog.objects.create(**obj)
        return Response("ERROR LOGGED", status=status.HTTP_201_CREATED)

    def post(self, request):
        data = request.data
        if request.user:
            self.user = request.user
            self.user_id = self.user.id
            print(self.user)
        else:
            self.user = None
            self.user_id = None

        data['user'] = self.user_id

        self.data = data

        if 'errorLog' in data:
            return self.log_error()

        self.email = ['help@wageup.com']
        self.email_feedback()
        serializer = FeedbackSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response("SUCCESS", status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.error_messages, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class Onboarding(generics.GenericAPIView):
    """
        Take as post input:
        purpose - what function should be called
        parameters - options for the function i.e. element, page etc.
    """

    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'


    def __init__(self):
        self.purpose_router = {
            'get_document': self.get_document,
            'demo': self.demo,
            'watched_demo': self.watched_demo,
            'show_demo': self.show_demo,

        }

    def post(self, request, *args, **kwargs):
        data = request.data
        self.user = self.request.user
        output = self.purpose_router[data['purpose']](data['parameters'])
        return Response(output, status=status.HTTP_200_OK)

    def get_document(self, parameters):
        document = Documentation.objects.get(element=parameters['element'])
        serializer = DocumentSerializer(document)
        data = serializer.data
        related_elements = []
        for elem in data['related_elements']:
            related_elements.append({
                'link': '/' + elem['element'],
                'title': elem['element'].replace('_', ' ').upper()
            })
        # html_content = render_to_string('onboarding/document.html', {
        #     'title': data['element'].replace('_', ' ').upper(),
        #     'element_type': data['element_type'],
        #     'related_element': related_elements,
        # })
        # data['html_content'] = html_content.replace('\n', '<br>')
        return data

    def watched_demo(self, parameters):
        try:
            page = DemoPage.objects.get(name=parameters['page'])
        except ObjectDoesNotExist:
            return "BAD PAGE PARAMETER"
        try:
            history = UserDemoHistory(user=self.user, page=page)
            history.seen = True
            history.save()
        except ObjectDoesNotExist:
            UserDemoHistory(user=self.user, page=page, seen=True).save()
        return "SUCCESS!"


    def show_demo(self, parameters):
        try:
            page = DemoPage.objects.get(name=parameters['page'])
        except ObjectDoesNotExist:
            return "BAD PAGE PARAMETER"

        if UserDemoHistory.objects.filter(user=self.user, page=page).exists():
            return False
        else:
            demo = DemoPageSerializer(page).data
            # UserDemoHistory(user=self.user, page=page, seen=True).save()
            return demo




    def demo(self, parameters):
        try:
            page = DemoPage.objects.get(name=parameters['page'])
        except ObjectDoesNotExist:
            return "BAD PAGE PARAMETER"
        try:
            user_history = UserDemoHistory.objects.get(user=self.user, page=page)
            if user_history.seen:
                return False
            else:
                user_history.seen=True
                user_history.save()
        except ObjectDoesNotExist:
            UserDemoHistory(user=self.user, page=page, seen=True).save()
            user_history = UserDemoHistory.objects.get(user=self.user, page=page)
        print(user_history)
        data = UserDemoHistorySerializer(user_history).data
        new_content = {}
        for c in data['page']['content']:
            new_content[c['object_id']] = {
                    "content": c['html_content'],
                    "object_id": c['object_id'],
                    "order": c['order'],
                    "include": c['include']}
        data['page']['content'] = new_content
        return new_content

class GoogleAnalytics(generics.GenericAPIView):
    """
        Take as post input:
        purpose - what function should be called
        parameters - options for the function i.e. element, page etc.
    """

    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'


    def __init__(self):
        self.purpose_router = {
            'get_user_history': self.get_user_history,
            'get_metric': self.get_metric,
            'get_user_data': self.get_user_data,
            'get_user_list_session_counts': self.get_user_list_session_counts,
            'all_user_history': self.all_user_history
        }

    def post(self, request, *args, **kwargs):
        data = request.data
        self.user = self.request.user
        output = self.purpose_router[data['purpose']](data['parameters'])
        return Response(output, status=status.HTTP_200_OK)

    def get_user_history(self, parameters):
        return get_user_session_counts(parameters['user'])

    def get_metric(self, parameters):
        return get_metric_ga(parameters['metric'])

    def get_user_data(self, parameters):
        return get_user_data_ga(parameters['user'])

    def get_user_list_session_counts(self, parameters):
        users = Employee.objects.filter(user_id__isnull=False)
        users = users.filter(**parameters).values()
        print(len(users))
        print(users.values("user__last_login", "user__username", "position_type"))
        return get_user_list_session_counts_ga(list(users))

    def get_fast_app_usage(self):
        payments = PaymentLog.objects.filter(payment_from__user_id__isnull=False, reward_status='SUCCEEDED').values('payment_from').annotate(fast_app_payment_sum=Sum('payment_amount'), user=F('payment_from__user_id')).values('user', 'fast_app_payment_sum')
        budgets = ManagerBudget.objects.filter(manager__user_id__isnull=False).annotate(user=F('manager__user_id'), fast_app_budget=F('amount')).values('user', 'fast_app_budget')
        out = combine_dicts([payments, budgets], 'user')
        [o.update({'id': o['user']}) for o in out]
        return out

    def all_user_history(self, parameters):
        if 'org_id' in parameters:
            print(parameters['org_id'], "ORG ID")
            # q = GaUserTracking.objects.filter(org_parent_id=parameters['org_id'])
            org_query = Organization.objects.get(id=parameters['org_id'])

            try:
                organization_list = org_query.lineage('Territory')
            except:
                organization_list = org_query.children().values_list('id', flat=True)
            if organization_list is None:
                organization_list = []

            if parameters.get('org_id') == 1:
                q = GaUserTracking.objects.all()
            elif org_query.type == 'Station' or org_query.type =='Station-Business':
                q = GaUserTracking.objects.filter(organization=org_query.name)
            else:
                q = GaUserTracking.objects.filter(Q(org_parent_id__in=organization_list) | Q(org_parent_id=parameters['org_id']))

            # child_query = GaUserTracking.objects.filter(org_parent_id=q)
            print('This is the qa query', org_query)
            print('org list', organization_list)
            print('This is q', q)

            if not q:
                q = GaUserTracking.objects.all()
        else:
            q = GaUserTracking.objects.all()

        if 'search_field' in parameters:
            if type(parameters['search_field']) != dict:
                parameters['search_field'] = {
                    parameters['search_field']: parameters['search_value']
                }
            for field, search_value in parameters['search_field'].items():
                if field == 'org_type':
                    if search_value.lower() == 'fleet':
                        q = q.filter(org_parent__facility_type='Fleet')
                    else:
                        q = q.exclude(org_parent__facility_type='Fleet')
                else:
                    d = {field + '__icontains': search_value}
                    print(d)
                    q = q.filter(**d)

        if 'sort_field' in parameters:
            if parameters['sort_direction'] == 'asc':
                q = q.order_by(parameters['sort_field'])
            else:
                q = q.order_by('-' + parameters['sort_field'])
        else:
            q = q.order_by('-last_login')

        out = q.annotate(str_last_login=TruncDate('last_login'),
                         last_scheduler_view_date=TruncDate('last_scheduler_view'),
                         total_logins=F('sessions'),
                         mtk_logins=F('sat_app_logins'),
                         rdb_logins=F('website_logins'),
                         org_type=Case(
                             When(org_parent__facility_type='Fleet', then=Value('Fleet')),
                             When(organization__icontains='fleet', then=Value('Fleet')),
                             default=Value('CSN'), output_field=CharField()),
                         ).values('first_name', 'last_name','total_logins', 'is_staff',
                                  'str_last_login','username',
                                  'position_type','organization',
                                  'organization_parent',
                                  'org_type', 'id','mtk_logins', 'rdb_logins',
                                  'last_scheduler_view_date', 'scheduler_views', 'map_views')



        # print(fast_app)

        out = combine_dicts([out], 'id')

        # print(out)

        total = len(out)
        if 'upper_limit' in parameters:
            out = out[parameters['lower_limit']: parameters['upper_limit']]

        cols = ['id', 'first_name', 'last_name','username','position_type', 'is_staff', 'organization',
                'organization_parent','mtk_logins','rdb_logins', 'total_logins',
                'str_last_login', 'scheduler_views', 'last_scheduler_view_date',
                  'map_views','org_type', 'fast_app_budget', 'fast_app_payment_sum']
        final_out = []
        for d in out:
            row = []

            if 'username' not in d:
                continue

            for k in cols:
                if k in ['fast_app_budget', 'fast_app_payment_sum'] and k not in d:
                    v = 0
                else:
                    v = d[k]
                if k == 'id':
                    link_id = v
                    continue
                if k == 'login_count':
                    if v == 0:
                        v = 1
                if k == 'username':
                    username = v
                if k == 'str_last_login':
                    k = 'last_login'
                if d['position_type'] == 'Executive':
                    print('executive info', k, v)
                row.append({
                    "label": k,
                    "value": v
                })
            final_out.append({
                "rowLink": '/user-mgmt/?user=' + str(link_id) + '&username=' + username,
                "data": row
            })
        print(len(final_out))
        return [final_out, total]

class DocumentationView(generics.GenericAPIView):
    """
        Take as post input:
        purpose - what function should be called
        parameters - options for the function i.e. element, page etc.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = None
    www_authenticate_realm = 'api'

    def __init__(self):
        self.purpose_router = {
            'get_all': self.get_all,
            'ehancements': self.enhancements,
            'get_metrics': self.get_metrics,
            'get_categorized_metrics': self.get_categorized_metrics,
            'get_goals': self.get_goals,
            'set_goals': self.set_goals,
        }

    def get_metrics(self, parameters):
        q = Documentation.objects.filter(element_type=parameters['type'])

        values = ['element', 'element_type', 'html_content', 'category__name', 'category__parent__name', 'number_type', 'highGood', 'permission', 'faq', 'formatted_name', 'raw_equation']
        init = q.values(*values)
        out = []
        for el in init:
            category = {'name': el['category__name'], 'parent': None}
            if el['category__parent__name']:
                    category['parent'] = {'name': el['category__parent__name'], 'parent': None}
            out_el = {k: v for k,v in el.items() if k not in ['category__name', 'category__parent__name']}
            out_el['category'] = category
            out.append(out_el)
        return out


    def get_categorized_metrics(self, parameters):
        q = Documentation.objects.filter(element_type='metric', category_id__isnull=False)\
            .annotate(category_name=F('category__name'), category_parent_name=F('category__parent__name'))
        vals = ["id", "element","element_type","html_content","category_name","category_parent_name","number_type","highGood","formatted_name"]
        out = q.values(*vals)
        top_cats = {}
        for metric in out:
            if not metric['category_parent_name']:
                top_cat = metric['category_name']
                if top_cat not in top_cats:
                    top_cats[top_cat] = []
                top_cats[top_cat].append(metric)
            else:
                top_cat = metric['category_parent_name']
                bot_cat = metric['category_name']
                if top_cat not in top_cats:
                    top_cats[top_cat] = {}
                if bot_cat not in top_cats[top_cat]:
                    top_cats[top_cat][bot_cat] = []
                top_cats[top_cat][bot_cat].append(metric)
        return top_cats


    def enhancements(self, parameters):
        print("getting enhancements")
        return DeploymentsSerializer(Deployments.objects.latest('date')).data

    def get_all(self, parameters):
        type = parameters.get('type', 'all')

        serializer_d = {
            'page': PageDocumentSerializer,
            'chart_type': ChartTypeDocumentSerializer,
            'metric': DocumentSerializer
        }

        if type == 'all':
            out = {}
            for type in ['page', 'chart_type', 'metric']:
                queryset = Documentation.objects.filter(element_type=type)
                out[type + 's'] = serializer_d[type](queryset, many=True).data
            return out

        queryset = Documentation.objects.filter(element_type=type)
        if parameters['type'] == 'page':
            serializer = PageDocumentSerializer
        elif parameters['type'] == 'chart_type':
            serializer = ChartTypeDocumentSerializer
        elif parameters['type'] == 'metric':
            queryset = queryset.filter(element__isnull=False, category_id__isnull=False)
            serializer = DocumentSerializer
        return serializer(queryset, many=True).data
        # docs = Documentation.objects.filter(element__isnull=False, category_id__isnull=False, element_type='metric')
        # chart_types = Documentation.objects.filter(element_type='chart_type')
        # metrics = DocumentSerializer(metrics, many=True).data
        # pages = DocumentSerializer(Documentation.objects.filter(element_type='page'), many=True).data
        # chart_types = DocumentSerializer(chart_types, many=True).data
        # out = {"metrics": metrics, "chart_types": chart_types, 'pages': pages}
        # return out

    def get_goals(self, parameters):
        goals = MetricGoals.objects.filter(Q(employee=self.request.user.employee()) | Q(employee__isnull=True))
        print('goals', goals)
        print(parameters)
        if 'organization_id' in parameters:
            org = Organization.objects.get(id=parameters.get('organization_id'))
        elif 'geography' in parameters:
            org = Organization.objects.get(id=parameters['geography'].get('id'))
        else:
            raise ValueError('there is no organization ID that can be used')
        print(org)
        parents = org.get_parent_to('Club', True) #+ [parameters.get('organization_id', 7), 7]
        print(parents)
        goals = goals.filter(organization_id__in=parents)
        print(parents)
        goals = goals.values('organization_id', 'facility_type', 'metric_id', 'metric__formatted_name', 'green', 'yellow', 'start', 'end', 'employee_id', 'organization__type')
        # goals = goals.values('employee_id', 'month', 'organization_id', 'range', 'target')
        out = []
        print(goals)
        ordering = ['Driver', 'Station', 'Station-Business', 'Territory', 'Territory-Facility-Type', 'Market',
                    'Market-Facility-Type', 'Club-Region', 'Club-Region-Facility-Type', 'Club', 'Club-Facility-Type']
        grouped = {}
        for type, group in groupby(goals, lambda x: x['metric_id']):
            grouped[type] = list(group)
        print(grouped)
        for type, group in grouped.items():
            print(type, len(group))
            if len(group) == 1:
                print('adding', type)
                out.append(group[0])
            else:
                idx_list = []
                for i, g in enumerate(group):
                    print(g, ordering.index(g['organization__type']), org.facility_type)
                    if org.facility_type is None or (g['facility_type'] is None
                            and ordering.index(g['organization__type']) < 4) or g['facility_type'].lower() == org.facility_type.lower():
                        idx_list.append({"level": ordering.index(g['organization__type']), "idx": i})
                print(idx_list)

                keep = group[sorted(idx_list, key=lambda x: x['level'])[0]['idx']]
                print(keep, type)
                out.append(keep)
        return out

    def set_goals(self, parameters):

        parameters['employee_id'] = parameters.get('employee_id', self.request.user.employee().id)
        goal_fields = ['organization_id', 'metric_id', 'green', 'yellow', 'start', 'end', 'employee_id']
        goals = {k: v for k,v in parameters.items() if k in goal_fields}
        try:
            obj = MetricGoals.objects.create(**goals)
        except django.db.utils.IntegrityError:
            obj = MetricGoals.objects.filter(metric_id=goals['metric_id'], employee_id=goals['employee_id'], organization_id=goals['organization_id'])
            obj.update(**goals)
            obj = obj[0] #TODO: check this...
        return model_to_dict(obj)


    def post(self, request):
        self.data = request.data
        if request.user:
            self.user = request.user
            self.user_id = self.user.id

        if 'parameters' in self.data:
            parameters = self.data['parameters']
        else:
            parameters = {}

        output = self.purpose_router[self.data['purpose']](parameters)
        return Response(output, status=status.HTTP_200_OK)



class EnhancementsView(generics.GenericAPIView):
    """
        Take as post input:
        purpose - what function should be called
        parameters - options for the function i.e. element, page etc.
    """

    permission_classes = ()
    serializer_class = None
    www_authenticate_realm = 'api'

    def __init__(self):
        self.purpose_router = {
            'enhancements': self.enhancements,
        }

    def enhancements(self, parameters):
        print("getting enhancements")
        return DeploymentsSerializer(Deployments.objects.latest('date')).data


    def post(self, request):
        self.data = request.data
        if request.user:
            self.user = request.user
            self.user_id = self.user.id

        if 'parameters' in self.data:
            parameters = self.data['parameters']
        else:
            parameters = {}

        output = self.purpose_router[self.data['purpose']](parameters)
        return Response(output, status=status.HTTP_200_OK)
