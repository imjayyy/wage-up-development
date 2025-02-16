import sys

from .models import DashboardBatteryAggregations, DashboardAggregations

sys.path.insert(0, 'root')
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
import pytz
import copy
from .name_cleanup import name_cleaner
import dateutil.relativedelta as relativedelta
from django.db.models import FloatField, F, DecimalField, IntegerField, BooleanField, Value as V
from django.db.models.functions import Extract, ExtractMonth, ExtractYear, Concat, LPad, ExtractHour, ExtractWeek
from django.db.models import Avg, Count, Sum, Min, Max, ExpressionWrapper, Q
from onboarding.serializers import *
from messaging.models import *
# from .metric_annotations import MetricAnnotationBuilder
from .dashboardDayGrouper import DashboardDayGrouper
from .dashboardUtilities import generate_biz_rules_annotation
import itertools
from django.db.models import Case, CharField, Value, When
from gensim.models import Word2Vec
from functools import reduce
import operator
from .lookups import dashboardLookups
from onboarding.models import Documentation
# from .dashboard_data_raw import RawDashboardData
# utc = pytz.UTC
import statistics
import datetime as dt
from .dashboardShiftGrouper import DashboardShiftGrouper

class DashboardBase(APIView):
    """
    Dashboard Base is inherited by the main class below, it mostly loads key attributes like org/employee identification
    permissions and access, and large lookup variables
    """
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()
    # serializer_class = None
    www_authenticate_realm = 'api'

    def set_variables(self):
        """
        Sets the large lookup variables for the class
        :return:
        """
        dl = dashboardLookups()

        self.grouping = []
        self.group_data = False
        self.original_length = None
        self.time_type_conversions = dl.time_type_conversions
        self.eligible_months = dl.eligible_months
        self.survey_key_converter = dl.survey_key_converter
        self.prov_type_conversion = dl.prov_type_conversion
        self.useful_annotations = dl.useful_annotations
        self.value_type_from_lookup = dl.value_type_from_lookup



    def get_last_update(self):
        #TODO: use etl_state view
        print('getting last update')
        try:
            latest_state = EtlStatus.objects.filter(today=1).latest(
                'datetime'
            )
        except:
            latest_state = False

        if latest_state:
            latest_state = latest_state.progress
        else:
            latest_state = "Jobs Havent Started Yet"

        return {
            'current_state': latest_state,
            'todays_states': EtlStatus.objects.all().values()
        }

    def purpose_router(self):

        if self.data.get('args', {}).get('grouping'):
            self.purpose = 'get_raw_ops_agg_data'

        self.router = {
            'get_data': self.get_data, # this is the generic call that gets made by default
            'get_custom_data': self.get_custom_data, # this is used for custom date range calls
            'get_survey_data': self.get_survey_data, # this is used for survey calls
            'get_last_update': self.get_last_update, # this just sets the last update time,
            'get_raw_ops_agg_data': self.get_raw_ops_agg_data,
        }
        return self.router[self.purpose]()

    def __init__(self):
        print('setting variables')
        self.set_variables()

    def get_index_type(self, object_type, reverse=False):
        """
        This helps us switch words around as needed for lookups in accounts vs. dashboard tables
        :param object_type: <A org/employee type like Club>
        :param reverse: reveerse the converter below so key values switch
        :return:
        """
        if object_type is None:
            return None

        converter = {
            'Club': 'CLUB',
            'Station-State': 'ORG_FACILITY_STATE',
            'Station-State-Facility-Type': 'ORG_FACILITY_STATE',
            'Call-Center-Operator': 'EMP_CALL_CENTER_OPERATOR',
            'Driver': 'EMP_DRIVER_ID',
            'Station-Business': 'ORG_BUSINESS_ID',
            'Call-Center': 'ORG_CALL_CENTER',
            'Call-Center-Group': 'ORG_CALL_CENTER_GROUP',
            'Grid': 'ORG_GRID',
            'Market': 'ORG_MARKET_ID',
            'Station': 'ORG_SVC_FACL_ID',
            'Club-Facility-Type': 'Club-Facility-Type',
            'Fleet-Supervisor': 'FLEET_SUPERVISOR',
            'Facility-Rep': 'ORG_SVC_FACILITY_REP',
            'Facility-Rep-Facility-Type': 'ORG_SVC_FACILITY_REP',
            'City': 'bl_near_cty_nm',
            'avl_zone': 'avl_zone',
            'State': 'bl_state_cd',
            'Breakdown-Location-State': 'ORG_BL_STATE',
            'Hub': 'ORG_HUB',
            'Service-Facility-Rep': 'ORG_SVC_FACL_REP',
        }

        if 'facility-type' in self.object_type.lower():
            converter = {k:v for k,v in converter.items() if 'facility-type' in k.lower() or k in ['Station', 'Station-Business', 'Driver']}
        else:
            converter = {k: v for k, v in converter.items() if 'facility-type' not in k.lower()}

        reverse_converter = {v: k for k, v in converter.items()}

        all_converter = {**converter, **reverse_converter}

        if reverse:
            return all_converter[object_type]
        return all_converter[object_type]

    def get_object(self, data):
        """
        This is where we set the object (e.g. organization or employee)
        :param data:
        :return:
        """
        print(data)
        # type is the type of indexing id i.e. Region, Territory, Grid, Driver etc.

        if not (data.get('id', False) or data.get('slug', False)):
            myOrg = self.request.user.employee().organization
            data['slug'], data['type'] = myOrg.slug, myOrg.type


        self.index_type = data.get('type', data.get('position_type'))
        geo_station = None
        if self.index_type == 'Station-Admin':
            if 'id' in data:
                geo_station = Employee.objects.get(id=data['id'], position_type=self.index_type).organization
            elif 'slug' in data:
                geo_station = Employee.objects.get(slug=data['slug'], position_type=self.index_type).organization

        # if 'fleetType' in data['slug']:
        #     print(data['slug'])
        #     data['slug'] = data['slug'].replace('-fleetType', '')
        #     # self.index_type = 'Station-State'
        #     # self.index_type = 'Station-State'
        #     print(data['slug'], "NEW SLUG")

        # if we get an id, then we are done and can return the object.
        # its not necessary to return the variable, since we can access it via self anyway...

        elif 'organization_id' in data:
            self.object = Organization.objects.get(id=data['organization_id'])
            self.object_type = self.object.type
            print('is battery:', self.data.get('args').get('battery'))

            self.queryset = self.model.objects.filter(organization_id=self.object.id)

            return self.object

        elif 'employee_id' in data:
            self.object = Employee.objects.get(id=data['employee_id'])
            self.object_type = self.object.position_type
            self.queryset = self.model.objects.filter(employee_id=self.object.id)
            if self.is_battery:
                self.queryset = self.queryset.filter(index_type='EMP_DRIVER_ID')

            return self.object

        self.employee_types = ['Driver', 'Call-Center-Operator',]
        self.organization_types = ['Club', 'Station-State',
                                   'Facility-Rep', 'Station-Business', 'Station', 'Booth', 'Grid',
                                   'Call-Center', 'Call-Center-Group', 'Club-Region', 'Club-Facility-Type',
                                   'Club-Facility-Type', 'Station-State-Facility-Type', 'Facility-Rep-Facility-Type',
                                   'avl_zone']

        if geo_station is not None:
            self.model_reference = 'Organization'
            self.object = geo_station
            self.object_type = self.object.type
            self.queryset = self.model.objects.filter(organization_id=self.object.id)

        elif self.index_type in self.organization_types:
            self.model_reference = 'Organization'
            if 'id' in data:
                # print(data)
                self.object = Organization.objects.get(id=data['id'])
            elif 'slug' in data:
                self.object = Organization.objects.get(slug=data['slug'])
            self.object_type = self.object.type
            self.queryset = self.model.objects.filter(organization_id=self.object.id)


        elif self.index_type in self.employee_types:
            self.model_reference = 'Employee'
            if 'id' in data:
                self.object = Employee.objects.get(id=data['id'], position_type=self.index_type)
            elif 'slug' in data:
                self.object = Employee.objects.get(slug=data['slug'], position_type=self.index_type)
            self.object_type = self.object.position_type

            self.queryset = self.model.objects.filter(employee_id=self.object.id)
            if self.is_battery:
                self.queryset = self.queryset.filter(index_type='EMP_DRIVER_ID')
            # print(self.object.name)
        else:
            print(self.index_type, "COULD NOT FIND")
            raise Exception("Type improperly specified, cannot find.")
        self.index_db_type = self.get_index_type(self.index_type)
        print(self.object.id)

    def default_children(self, object_type=None):
        if object_type is None:
            object_type = self.object_type
        # original
        # defaults = {
        #     'Club': 'ORG_CLUB_REGION',
        #     'Club-Region': 'ORG_MARKET_ID',
        #     'Market': 'ORG_TERRITORY_ID',
        #     'Territory': 'ORG_SVC_FACL_ID',
        #     'Station-Business': 'ORG_SVC_FACL_ID',
        #     'Station': 'EMP_DRIVER_ID',
        #     'Call-Center': 'ORG_CALL_CENTER_GROUP',
        #     'Call-Center-Group': 'EMP_CALL_CENTER_OPERATOR',
        #     'Club-Facility-Type': 'Club-Region-Facility-Type',
        #     'Club-Region-Facility-Type': 'Market-Facility-Type',
        #     'Market-Facility-Type': 'Territory-Facility-Type',
        #     'Territory-Facility-Type': 'ORG_BUSINESS_ID',
        #     'Driver': 'EMP_DRIVER_ID',
        # }
        defaults = {
            'Club': 'ORG_FACILITY_STATE',
            'Station-State': 'ORG_SVC_FACL_ID',
            'Station-State-Facility-Type': 'ORG_SVC_FACL_ID',
            'Station-Business': 'EMP_DRIVER_ID',
            'Station': 'EMP_DRIVER_ID',
            'Call-Center': 'ORG_CALL_CENTER_GROUP',
            'Call-Center-Group': 'EMP_CALL_CENTER_OPERATOR',
            'Club-Facility-Type': 'ORG_FACILITY_STATE',
            'Facility-Rep': 'ORG_SVC_FACL_ID',
            'Facility-Rep-Facility-Type': 'ORG_SVC_FACL_ID',
            'Driver': 'EMP_DRIVER_ID',
        }

        if 'facility-type' in self.object_type.lower():
            defaults = {k:v for k,v in defaults.items() if 'facility-type' in k.lower() or k in ['Station', 'Driver', 'Station-Business']}
        else:
            defaults = {k: v for k, v in defaults.items() if 'facility-type' not in k.lower()}

        other_way = {}
        for k, v in defaults.items():
            other_way[self.get_index_type(k)] = v

        combined_defaults = {**defaults, **other_way}

        # if self.purpose != 'survey_aggregator':
        #     defaults['Territory'] = 'ORG_BUSINESS_ID'
        out = combined_defaults[object_type]
        print('default child', out)
        return out

    def sc_dt_lookup(self, time_type):

        """
        This converts Time types like "This Month" into actual date strings for lookup in db
        :param time_type:
        :return:
        """

        today = dt.datetime.today()
        today = dt.datetime(today.year, today.month, today.day)

        if time_type == 'Yesterday':
            yesterday = self.latest_date
            print(yesterday)
        else:
            yesterday = ""

        lookup = {
            'Yesterday': (
                'D', yesterday,
                      'Yesterday'),
                'This_Month': (
            'M', (today - relativedelta.relativedelta(days=self.data.get('start_month_cutoff', 4))).replace(day=1),
                                                                                                    'This_Month'),
        'Prev_Month': ('M', (
                (today - relativedelta.relativedelta(days=self.data.get('start_month_cutoff', 4))).replace(
                    day=1) - relativedelta.relativedelta(months=1)), 'Prev_Month'),
        'Prev_Year': ('Y', (
                (today - relativedelta.relativedelta(days=
                                                     self.data.get('start_month_cutoff', 4)))
                .replace(month=1,day=1) - relativedelta.relativedelta(months=12)),
                      'YTD'),
        'ytd': ('Y',
                (today - relativedelta.relativedelta(days=self.data.get('start_month_cutoff', 4))).replace(month=1,
                                                                                                           day=1),
                'YTD'),
        'YTD': ('Y',
                (today - relativedelta.relativedelta(days=self.data.get('start_month_cutoff', 4))).replace(month=1,
                                                                                                           day=1),
                'YTD'),
        }

        grouping = {
            'Day_of_Week': ['week_day', ],
            'Day_and_Hour_of_Week': ['week_day', Extract('sc_dt', 'hour'), ],
            'Hour': [Extract('sc_dt', 'hour'), ],
            'This_Incentive': ['sc_dt']

        }

        if type(time_type) == dict:
            return time_type

        elif time_type in lookup:
            return lookup[time_type]
        elif time_type in grouping:
            self.group_data = True
            self.grouping.append((time_type, grouping[time_type]))
        else:
            raise Exception("SOMETHING WENT WRONG WITH TIME TYPE ASSIGNMENTS")

    def cleanName(self, m):
        docs = {doc.get('element'): doc.get('formatted_name') for doc in self.docs}
        return docs.get(m, name_cleaner.get(m, m.replace('_', ' ').upper()))

    def post(self, request, *args, **kwargs):

        """
        This is the first call that gets hit when you hit the API.
        :param request:
        :param args:
        :param kwargs:
        :return:
        """

        print('post args', args)
        print('post kwargs', kwargs)
        print('post request.data', request.data)
        self.request = request




        self.data = self.request.data
        agg_as_metrics = []

        self.is_battery = self.data.get('args', {}).get('battery')
        # print(self.data, self.is_battery)
        self.model = DashboardBatteryAggregations if self.is_battery else DashboardAggregations

        if self.data.get('purpose') in ['get_last_update']:
            self.purpose = self.data.get('purpose')
            return Response(self.purpose_router(), status=status.HTTP_200_OK)

        # self.purpose = request.data.get('purpose', 'get_data')

        self.latest_date = self.model.objects.filter(organization_id=1, time_type='D').latest('sc_dt').sc_dt

        self.data_target = self.data.get('dataTarget', 'dashboard_aggregations')
        r = {
            'dashboard_aggregations': 'get_data',
            'std12e_reduced': 'get_survey_data',
        }

        #mostly just initializing here...
        self.purpose = self.data.get('purpose', r[self.data_target])

        self.filters = self.data.get('filters', {})



        self.get_object(self.data.get('geography', {}))

        #### check if allowed #####
        user_emp = self.request.user.employee()
        if user_emp.position_type in ['Driver', 'Station-Admin']:
            deny = False
            if user_emp.position_type == 'Station-Admin':
                try:
                    deny = self.object.organization_id != user_emp.organization_id
                except:
                    deny = self.object.id != user_emp.organization_id
            if deny:
                return Response("No Allowed Here.", status=status.HTTP_403_FORBIDDEN)

        ##########




        self.relations = self.data.get('relation', ['self'])

        self.chart_types = self.data.get('chart_type', {})
        if self.chart_types == {}:
            self.chart_types = self.request.data.get('chart_types', {})

        if self.object_type in ['Station', 'Station-Business', 'Driver'] and 'reroute' not in self.filters and any(['aaa_mgmt' in x for x in self.data.get('metrics')]):
            print('adding filter for reroute')
            self.data['metrics'] = [m.replace('aaa_mgmt', 'comp') for m in self.data.get('metrics')]
            self.filters['reroute'] = True

        # this is mostly for cleaning up metric names and getting metric types (e.g. percent)
        self.metrics = self.data.get('metrics')
        # print(self.data.keys())
        if self.data.get('chart_type') == 'treeMap':
            self.metrics = ['volume'] + self.metrics

        def check_sat_type(m):
            return m
            # if 'aaa_mgmt' in m and self.object.type in ['Driver', 'Station', 'Station-Business']:
            #     _m = m.replace('aaa_mgmt', 'comp')
            # else:
            #     _m = m
            # return _m
        self.original_metrics = [check_sat_type(m) for m in self.data.get('metrics', []) if m not in agg_as_metrics]
        self.aggregation_metrics = [m for m in self.data.get('metrics', []) if m in agg_as_metrics]

        self.metric_value_annotations = {}
        print("METRICS ARE", self.metrics)
        self.docs = Documentation.objects.filter(element__in=self.metrics).values('element', 'formatted_name', 'number_type')

        docs = {doc.get('element'): doc.get('formatted_name') for doc in self.docs}

        for i, m in enumerate(self.metrics):
            if m not in ['parent_id', 'id', '_id']:

                self.metric_value_annotations[name_cleaner.get(m, docs.get(m, m)).replace(' ', '_')] = F(m.replace(' ', '_'))
                self.metrics[i] = docs.get(m, name_cleaner.get(m, m)).replace(' ', '_')

        if self.chart_types == {}:
            [self.chart_types.update({m: 'line'}) for m in self.metrics]
        elif type(self.chart_types) == str:
            t = self.chart_types
            self.chart_types = {}
            [self.chart_types.update({m: t}) for m in self.metrics]

        # filter time
        # if self.params.get('time_type_filter'):
        #     self.time_type = [self.params.get('time_type_filter')[0]] # todo: hacky should fix

        self.timeseries_types = ['D', 'M', 'W-MON', 'TIMESERIES', 'Month', 'Day', 'Week']
        # self.time_types = self.params.get('time_types', ['D'])

        if self.data.get('time_type') == [None]:
            self.data['time_type'] = []

        if self.data.get('args', {}).get('shift'):
            self.purpose = 'get_raw_ops_agg_data'




        if self.purpose not in ['get_custom_data']:

            self.categorical_time_types_sc_dt = [self.sc_dt_lookup(t) for t in self.data.get('time_type', ['D']) if
                                             t not in self.timeseries_types]
            self.time_types = [self.time_type_conversions[t] for t in self.data.get('time_type', ['Day']) if type(t) != dict]

            print(
                f'relations: {self.relations}, time_types:  {self.time_types}, chart_types {self.chart_types}, time_categories: {self.categorical_time_types_sc_dt}')

            try:
                if dt.datetime.strptime(self.filters.get('from')[:10], '%Y-%m-%d') > self.categorical_time_types_sc_dt[0][1]:
                    print('start filter is bad')
                    del self.filters['from']
            except:
                pass

        out = self.purpose_router()


        # if self.data.get('args').get('grouping'):
        #     # this is for creating a column that says tcd instead of having a bunch of metrics
        #     if self.data.get('args').get('grouping') == 'TCD':
        #         series = []
        #         s = out.get('series') if type(out.get('series')[0]) != list else out.get('series')[0]
        #         tow = [m for m in self.metrics if 'tow' in m.lower()]
        #         battery = [m for m in self.metrics if 'battery' in m.lower()]
        #         any = [m for m in self.metrics if 'battery' not in m.lower() and 'tow' not in m.lower() and 'ls' not in m.lower()]
        #         ls = [m for m in self.metrics if 'ls' in m.lower()]
        #         print('tow', tow)
        #         series = series + [{k.replace(f'_(Tow)', ''): v for (k,v) in list(d.items()) + [('TCD', 'Tow')]
        #                             if k not in battery + ls + any}
        #                             for d in s]
        #
        #         series = series + [{k.replace(f'_(Battery)', ''): v for (k,v) in list(d.items()) + [('TCD', 'Battery')]
        #                             if k not in tow + ls + any}
        #                             for d in s]
        #
        #         series = series + [{k: v for (k,v) in list(d.items()) + [('TCD', 'All')]
        #                             if k not in tow + battery + ls}
        #                             for d in s]
        #
        #         out['series'] = series


        return Response(out, status=status.HTTP_200_OK)


class DashboardData(DashboardBase):
    '''
    designed to return data to requests in My Dashboard

    of which there are basically two types:
    * geographic relationships
        * children
        * self
        * siblings --> ranking
    * time relationships
        * discrete time units
        * time series based on groups like this month vs. last month

    * returns the series part of the graph, or table data

    '''

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.labels = []
        self.out = []
        self.column_config = []
        self.default_column_config = {

        }

        self.meta = {}

        self.duplicate_tracker = []

        self.y_axis_default = {
            "seriesName": [],
            "axisTicks": {
                "show": True
            },
            "decimalsInFloat": 1,
            "forceNiceScale": True,
            "axisBorder": {
                "show": True,
            },
        }
        self.y_axis_options = {
            'big_number': copy.deepcopy(self.y_axis_default),
            'small_number': copy.deepcopy(self.y_axis_default),
            'percentage': copy.deepcopy(self.y_axis_default),
        }

        self.y_axis_selection = []

    def parse_label(self, label):
        return f'{label:%Y-%m-%d}'

    def chart_data_router(self, **kwargs):
        """
        This routes the output to the right chart type, and is supposed to be able to handle
        various output conversions for different visualizations (e.g. table vs. linke)
        :param kwargs:
        :return:
        """
        chart_type = kwargs.get('chart_type', self.chart_types[kwargs.get('metric')])

        router = {
            'line': self.line,
            'bar': self.bar,
            'table': self.table,
            'treeMap': self.treeMap,
            'numberHighlights': self.number_highlights  # todo: build numberHighlights function
        }

        return router[chart_type](**kwargs)

    def get_value_type(self, value):

        """
        Set the value type based on input (e.g. identify percentage vs. big number)
        :param value:
        :return:
        """

        if value is None:
            return None
        if type(value) == str:
            return 'string'
        elif isinstance(value, dt.datetime):
            # todo: find a way to tell if the value/type is a date or datetime
            if value.hour == 0 and value.minute == 0:
                return 'date'
            return 'datetime'
        elif isinstance(value, dt.date):
            return 'date'
        elif 1 > value > -1: #TODO: need a better way of dealing with percentage for 1 here...
            return 'percentage'
        elif value > 500:
            return 'big_number'
        elif type(value) == float:
            return 'float'
        else:
            return 'number'

    def format_value(self, value, value_type=None, format_str=None, no_strings=False, metric=None):
        """
        Given a value type, format the output to look good.
        :param value:
        :param value_type:
        :param format_str:
        :param no_strings:
        :param metric:
        :return:
        """

        if value is None:
            return None

        if value_type is None:
            value_type = self.get_value_type(value)

        if value_type == 'string':
            return value.upper().replace('_', " ")
        if value_type == 'float':
            return round(value, 1)
        if value_type == 'number':
            return value
        if value_type == 'big_number':
            if not no_strings:
                return f'{round(value, 0):,}'
            else:
                return round(value, 0)
        if value_type == 'percentage':
            return round(value * 100, 1)
        # todo: find a way to tell if the value/type is a date or datetime
        if value_type == 'date':
            format_str = format_str if format_str is not None else '%Y-%m-%d'
            try:
                return value.strftime(format_str)
            except AttributeError:
                return value
        if value_type == 'datetime':
            format_str = format_str if format_str is not None else '%Y-%m-%d %H:%M'
            # print('datetime value', value.hour, value.minute)
            if value.hour == 0 and value.minute == 0:
                format_str = format_str if format_str is not None else '%Y-%m-%d'
            try:
                return value.strftime(format_str)
            except AttributeError:
                return value
        else:
            return value

    def format_name(self, name):
        return name_cleaner.get(name, name)

    def getYAxisRange(self, data, series_name, return_format_only=False):

        """
        set up ranges for a series, so we have top bottom values etc. Not used as much anymore ...
        :param data:
        :param series_name:
        :param return_format_only:
        :return:
        """

        data = [d for d in data if d is not None]
        if len(data) == 0:
            return
        max_val, min_val = max(data), min(data)
        # print(max_val, min_val, series_name)
        # range = max - min

        if max_val > 10000:
            self.y_axis_options['big_number']['seriesName'].append(series_name)
            self.y_axis_options['big_number']['decimalsInFloat'] = 0
            out = 'number'
        elif max_val <= 1 and min_val >= 0:
            self.y_axis_options['percentage']['seriesName'].append(series_name)
            self.y_axis_options['percentage']['opposite'] = True

            out = 'percentage'
        else:
            self.y_axis_options['small_number']['seriesName'].append(series_name)
            out = 'number'
        # print(self.y_axis_options)
        if not return_format_only:
            self.y_axis_selection = [v for k, v in self.y_axis_options.items() if len(v['seriesName']) > 0]
        else:
            self.y_axis_selection = self.y_axis_default

        return out

    def bar(self, **kwargs):

        """
        converts data into a format the Apex Bar Chart understands...
        Can accept different arguments
        :param kwargs:
        :return:
        """

        metric = kwargs.get('metric')
        org_data_i = kwargs.get('iterations', {}).get('org_data_i')

        if not kwargs.get('grouped_data'):
            print(f'relations: {self.relations} cat_time_types: {self.categorical_time_types_sc_dt} metrics {self.metrics}')
            assert (self.relations != ['self'] and len(self.categorical_time_types_sc_dt) > 1 and len(
                self.metrics) == 1) \
                   or (self.relations != ['self'] and len(self.metrics) > 1 and len(
                self.categorical_time_types_sc_dt) == 1) \
                   or (self.relations == ['self'] and len(self.metrics) > 1 and len(
                self.categorical_time_types_sc_dt) > 1) \
                , "Either relation must be length 1, metrics must be length 1 or categorical time types must be length 1!"

        if self.relations != ['self'] and len(self.categorical_time_types_sc_dt) > 1:
            # print('path a')
            data = kwargs.get('org_data')

            ## grouped by org
            self.labels = [self.format_value(x['sc_dt'], 'date', ) for x in data]  ## categories

            series_data = [d[metric] for d in data]
            number_type = self.getYAxisRange(series_data, self.format_name(metric))
            series_data = [self.format_value(d, number_type) for d in series_data]

            self.out.append({
                # "grouped_by": "relation",
                "name": data[0]['name'],
                "data": series_data
            })
        elif kwargs.get('org_data') and (self.relations != ['self'] and len(self.metrics) > 1 and len(self.categorical_time_types_sc_dt) == 1):
            data = kwargs.get('org_data')
            # print('path b', data[0])
            # self.out = data[0]


            assert data is not None, f"error in bar graph {kwargs}"

            ## grouped by org
            # print(self.labels)
            if data[0]['name'] not in self.labels:
                self.labels.append(data[0]['name'])  ## categories

            try:
                series_data = [d.get(metric) for d in data]
            except Exception as e:
                print(e)
                print(metric, data)
            number_type = self.getYAxisRange(series_data, self.format_name(metric), return_format_only=True)
            series_data = [self.format_value(d, number_type) for d in series_data]

            try:
                d = next(item for item in self.out if item['name'] == self.format_name(metric))
                d['data'].extend(series_data)
            except StopIteration:
                self.out.append({
                    # "grouped_by": "relation",
                    "name": self.format_name(metric),
                    "data": series_data
                })
        else:
            # print('path c')

            # 3 grouped by time
            if org_data_i:
                if org_data_i > 1:  # org data is a loop inside time loop
                    return
            data = kwargs.get('time_type_data')

            if not data:
                data = kwargs.get('grouped_data')

            try:
                print(data[0])
            except Exception as e:
                print(e)
                data = kwargs.get('org_data')

            if 'sc_dt' not in data[0] and 'month_year' in data[0]:
                [d.update({'sc_dt': d['month_year']}) for d in data]

            if 'sc_dt' not in data[0] and 'custom_time_group' in data[0]:
                # print(data[0])
                self.labels = [x['custom_time_group'] for x in data]

            elif len(self.labels) == 0:
                self.labels = [self.format_value(x['sc_dt'], 'date', format_str=kwargs.get('format_str')) for x in
                               data]  ## categories

            series_data = [d[metric] for d in data]
            number_type = self.getYAxisRange(series_data, self.format_name(metric))
            series_data = [self.format_value(d, number_type) for d in series_data]

            self.out.append({
                # "grouped_by": "time",
                "name": self.format_name(metric),
                "data": series_data
            })

    def treeMap(self, **kwargs):
        """
        converts output into tree map format (very similar to table function)
        :param kwargs:
        :return:
        """
        if len(self.metrics) == 1:
            return

        self.exclusions = ['time_type', '_id', 'id']

        metric = kwargs.get('metric')
        org_data = kwargs.get('org_data')
        self.column_config = self.data.get('column_config', {}).get(metric, {})
        out_org_data = []

        if len(self.categorical_time_types_sc_dt) > 0:
            dates = [t[1].strftime('%Y-%m-%d') for t in self.categorical_time_types_sc_dt]
            # print("DATES", dates, org_data[0])
            org_data = filter(lambda x: x['sc_dt'].strftime('%Y-%m-%d') in dates, org_data)

        for i, d in enumerate(org_data):
            # print(i, d)
            out_org_data.append({})
            for k, v in d.items():

                if k == 'id':
                    if d[k] in self.duplicate_tracker:
                        return
                    self.duplicate_tracker.append(d[k])

                if k in self.exclusions:
                    continue
                else:
                    metric_type = next((x for x in self.docs if x['formatted_name'] == k or x['element'] == k), None)
                    out_org_data[i][k] = self.format_value(v, metric_type, no_strings=True)

        # print(self.duplicate_tracker)

        # print(out_org_data)
        data = out_org_data[0]
        if data.get('slug') != self.object.slug:
            self.out.append({
                "size_name": self.metrics[0],
                "color_name": self.metrics[1],
                "size_number": data.get(self.metrics[0]),
                "color_number": data.get(self.metrics[1]),
                "metrics": {m: data.get(k) for m, k in zip(['volume'] + self.original_metrics, self.metrics)},
                "color_min": 0.5,
                "color_max": 1,
                "name": data.get('name'),
                "slug": data.get('slug')
            })

    def line(self, **kwargs):
        '''
        Converts to line format.

        :param kwargs:
        expected_final_output:
        if children
            for each child -- one metric:
                { ...
                data: [1,2,3]
                labels: [2021-01-01, 2021-01-02]
        if self
            for each metric --
                { ...
                data: [1,2,3]
                labels: [2021-01-01, 2021-01-02]
                }

        '''
        org_data = kwargs.get('org_data')
        metric = kwargs.get('metric')

        self.labels = [self.parse_label(o['sc_dt']) for o in org_data]  # x axis
        # print(metric, org_data)
        orig_metric = self.original_metrics[self.metrics.index(metric)]
        series_data = [o.get(metric, o.get(orig_metric)) for o in org_data]
        number_type = self.getYAxisRange(series_data, self.format_name(metric))
        series_data = [self.format_value(d, number_type) for d in series_data]

        if self.relations != ['self']:
            self.out.append({
                "name": org_data[0]['name'],
                "metric": self.format_name(metric),
                "org_name": org_data[0]['name'],
                "type": 'line',
                "grouped_by": "relation",
                "data": series_data
            })
        else:
            self.out.append({
                "name": self.format_name(metric),
                "metric": self.format_name(metric),
                "org_name": org_data[0]['name'],
                "type": 'line',
                "grouped_by": 'metric',
                "data": series_data
            })

    def table(self, **kwargs):

        """
        Converts to table format
        :param kwargs:
        :return:
        """

        self.exclusions = ['time_type', '_id', 'id', 'parent_id']

        metric = kwargs.get('metric')
        org_data = kwargs.get('org_data')
        # print(org_data)
        self.column_config = self.data.get('column_config', {}).get(metric, {})
        # print('column config', self.column_config)
        out_org_data = []

        if len(self.categorical_time_types_sc_dt) > 0:
            dates = [t[1].strftime('%Y-%m-%d') for t in self.categorical_time_types_sc_dt]
            # print("DATES", dates, org_data[0])
            org_data = filter(lambda x: x['sc_dt'].strftime('%Y-%m-%d') in dates, org_data)
        # print(org_data)
        try:
            org_data = sorted(org_data, key=lambda x: x['sc_dt'], reverse=True)
        except:
            pass
        for i, d in enumerate(org_data):

            out_org_data.append({})
            for k, v in d.items():
                if k == 'id':
                    if d[k] in self.duplicate_tracker:
                        return
                    self.duplicate_tracker.append(d[k])

                if k in self.exclusions:
                    continue
                else:
                    format_str = '%Y-%m-%d'
                    # print(k)
                    num_format = self.value_type_from_lookup.get(k.lower())

                    if ('sat' in k.lower() or 'percent' in k.lower()) and not ('count' in k.lower() or 'sum' in k.lower() or 'base' in k.lower()) and type(v) != str:
                        num_format='percentage'
                    if 'id' in k:
                        num_format='number'
                    out_org_data[i][k] = self.format_value(v, num_format, format_str=format_str)
                if kwargs.get('relation') == 'self' and 'children' in self.relations and not self.data.get('child_type'):
                    out_org_data[i][k + '_color'] = {'bg': '#00008b', 'color': 'white'}
        # print(self.duplicate_tracker)

        # print(out_org_data)
        self.out.append(out_org_data)

    def number_highlights(self, **kwargs):
        """
        Covnerts to number highlights format. Needs to get previous data for comparisons
        :param kwargs:
        :return:
        """
        data = kwargs.get('org_data')
        out = []
        # print(self.categorical_time_types_sc_dt)

        tt = self.categorical_time_types_sc_dt[0][0]
        this_month = False
        if self.categorical_time_types_sc_dt[0][2] == 'This_Month':
            this_month = True
            days = DashboardUpdateHistory.objects.aggregate(Max('date_updated'))
            # print(days)
            days = days['date_updated__max'].day - 1

            std_d_days = list(DashboardAggregationMetaData.objects.
                         filter(organization_id=self.object.id, stat_type='std', time_type='D')
                         .annotate(**self.metric_value_annotations).values(*self.metrics))[0]
            avg_d_days = list(DashboardAggregationMetaData.objects.
                         filter(organization_id=self.object.id, stat_type='avg', time_type='D')
                         .annotate(**self.metric_value_annotations).values(*self.metrics))[0]
        std_d = list(DashboardAggregationMetaData.objects.
                     filter(organization_id=self.object.id, stat_type='std', time_type=tt)
                     .annotate(**self.metric_value_annotations).values(*self.metrics))[0]
        avg_d = list(DashboardAggregationMetaData.objects.
                     filter(organization_id=self.object.id, stat_type='avg', time_type=tt)
                     .annotate(**self.metric_value_annotations).values(*self.metrics))[0]
        # print('number highlight stats', std_d, avg_d)

        if type(data) == list:
            if len(data) == 2:
                prev = data[0]
                current = data[1]
            else:
                prev, current = data[0], data[0]

            for k, v in current.items():
                top, bottom, std_diff, avg = 100, 0, 0, v
                try:
                    avg, std = avg_d[k], std_d[k]
                    if this_month and (self.get_value_type(v) == 'big_number' or 'volume' in k.lower()):
                        # print('using days', avg, std)
                        avg, std = avg_d_days[k] * days, std_d_days[k] * days
                        # print('using days', avg, std)
                    top, bottom, std_diff = (avg + std*2), (avg - std*2) , (v - avg)/std
                    # print(k, avg, std, v, self.get_value_type(v))
                except:
                    pass
                if prev[k] == 0:
                    prev[k] = 0.01
                out.append({
                    'name': self.format_name(k),
                    'value': self.format_value(v),
                    'orig_value': v,
                    'top': self.format_value(top),
                    'orig_top': top,
                    'orig_bottom': bottom,
                    'bottom': self.format_value(bottom),
                    'std_diff': std_diff,
                    'show_prev': not (prev[k] == current[k]),
                    'avg': avg,
                    'orig_prev': prev[k],
                    'prev_value': self.format_value(prev[k]),
                    'prev_change': self.format_value(1 - float(v) / float(prev[k])) if self.get_value_type(v) in ['percentage',
                                                                                                    'number', 'float',
                                                                                                    'big_number'] else None,
                    'type': self.get_value_type(v)
                })

        else:
            for k, v in data.items():
                out.append({
                    'name': self.format_name(k),
                    'value': self.format_value(v),
                    'type': self.get_value_type(v)
                })

        self.out = out

    def get_num_denom(self, metric):
        to_replace = 'avg' if 'avg' in metric else 'freq'
        denom, num = metric.replace(to_replace, 'count'), metric.replace(to_replace, 'sum')

        all_volume_denom_metrics = ['lost_call_freq', 'gained_call_freq', 'net_reroute_freq', 'declined_call_freq']

        if metric in all_volume_denom_metrics:
            return 'all_volume', metric.replace(to_replace, 'count')

        volume_denom_metrics =['external_call_out_freq',
                             'text_message_freq',
                             'call_accepted_freq',
                             'early_freq',
                             'late_freq',
                             'on_time_freq',
                             'long_ata_freq',
                             'ata_under_45_freq',
                             'no_service_rendered_freq',
                             'cancelled_freq',
                             'ng_to_g_freq',
                             'g_to_g_freq',
                             'g_to_ng_freq',
                             'ng_to_ng_freq',
                             'outside_communicated_freq',
                             'heavy_user_freq',
                             'call_cost_avg',
                             'credit_card_spend_avg',
                             'base_cost_avg',
                             'enroute_cost_avg',
                             'tow_cost_avg',
                             'short_freq']

        if metric in volume_denom_metrics:
            return 'volume', metric.replace(to_replace, 'count')

        if getattr(self.model, denom, False) and getattr(self.model, num, False):
            return denom, num
        elif not getattr(self.model, denom, False):
            return ExpressionWrapper(
                F(num) / F(metric), output_field=FloatField()), num
        elif not getattr(self.model, num, False):
            return denom, ExpressionWrapper(
                F(denom) * F(metric), output_field=FloatField())

    def get_grouping_annotation(self, metrics):
        annotation = {}
        for m in metrics:

            if 'avg' in m and 'sat' in m:
                annotation[m] = Sum(F('_'.join(m.split('_')[:-1]) + '_sum'), output_field=FloatField()) / Sum(
                    F('_'.join(m.split('_')[:-1]) + '_count'), output_field=FloatField())
            elif 'count' in m or 'sum' in m:
                annotation[m] = Sum(F(m), output_field=FloatField())
            elif 'avg' in m or 'freq' in m:
                denom, num = self.get_num_denom(m)
                annotation[m] = F(num) / F(denom)

        return annotation

    def get_group_labels(self, this_out, time_type):
        base_date = dt.datetime.today().replace(minute=0, second=0)
        time_str = '%Y-%m-%dT%H:%M:%SZ'

        if time_type == 'Day_of_Week':
            base_date = (base_date + dt.timedelta(days=-7 - base_date.weekday()))
            for i, elem in enumerate(this_out):
                # print(elem)
                this_out[i]['sc_dt'] = (base_date + dt.timedelta(days=int(elem['week_day'].split('-')[0])))

        return this_out

    def group_dashboard_data(self, surveys=False):

        """
        Used to create groupings for the bar chart.

        :param surveys:
        :return:
        """

        if not surveys:
            filters = {
                'organization_id': self.object.id
            }
        else:
            filters = {}
        out = []
        for time_type, grouping in self.grouping:
            metric_annotations = self.get_grouping_annotation(self.original_metrics)
            name_annotations = {name_cleaner[m]: v for m, v in metric_annotations.items()}
            filters.update({f'{group}__isnull': False for group in grouping})
            # print(f'grouping {grouping} filters: {filters} name_annotations: {name_annotations}')
            this_out = self.q.filter(**filters).values(*grouping).annotate(**name_annotations).values(
                *self.metrics + grouping)
            this_out = self.get_group_labels(this_out, time_type)
            for metric in self.metrics:
                # print('getting bar', metric)
                self.bar(grouped_data=this_out, metric=metric, format_str='%A')
            out.append(this_out)

        return {'series': self.out, 'labels': self.labels, 'y_axis_options': self.y_axis_selection,
                'column_config': self.column_config}

    def get_data(self):
        """
        main function call (default route. gets data ready for chart output functions
        :return:
        """

        self.q = self.model.objects
        # print('get data filters', self.filters)
        # print('get data time types', self.time_types)
        if self.filters.get('from'):
            self.filters['from'] = self.filters['from'].split('T')[0] if 'T' in self.filters['from'] else self.filters['from']
            self.q = self.q.filter(sc_dt__gte=self.filters.get('from'))
        else:
            if 'D' in self.time_types:
                curr_date = dt.date.today()
                past_date = curr_date - dt.timedelta(days=60)
                self.q = self.q.filter(sc_dt__gte=past_date)
            elif self.time_types[0] in self.timeseries_types:
                curr_date = dt.date.today()
                past_date = f'{curr_date.year}-01-01'
                self.q = self.q.filter(sc_dt__gte=past_date)
        if self.filters.get('to'):
            self.filters['to'] = self.filters['to'].split('T')[0] if 'T' in self.filters['to'] else self.filters['to']

            self.q = self.q.filter(sc_dt__lte=self.filters.get('to'))
        else:
            if 'D' in self.time_types:
                curr_date = dt.date.today()
                curr_date = curr_date - dt.timedelta(days=1)
                self.q = self.q.filter(sc_dt__lte=curr_date)
            elif self.time_types[0] in self.timeseries_types:
                curr_date = dt.date.today()
                curr_date = curr_date - dt.timedelta(days=1)
                self.q = self.q.filter(sc_dt__lte=curr_date)

        if self.group_data:
            return self.group_dashboard_data()
        else:
            self.q = self.q.filter(time_type__in=self.time_types)

        relation_i = 0
        # print(self.metric_value_annotations)

        for relation in self.relations:
            relation_i += 1
            metric_i = 0
            values = ['id', '_id', 'name', 'time_type', 'sc_dt', 'slug']

            relation_qs, extra_fields = self.get_relation_dataset(relation)
            relation_qs = relation_qs.annotate(**self.metric_value_annotations)
            try:
                relation_qs = relation_qs.values(*values + self.metrics + extra_fields)
            except:
                relation_qs = relation_qs.values(*values + self.original_metrics + extra_fields)

            # print(relation, relation_qs)

            if relation == 'children':
                print('children')
                # print(relation_qs[0])
            for metric in self.metrics:
                # print(metric)
                metric_i += 1
                time_type_i = 0
                for time_type, time_type_data in itertools.groupby(relation_qs, lambda x: x['time_type']):
                    time_type_i += 1
                    org_data_i = 0
                    cat_tt = [tt[1].strftime('%Y-%m-%d') for tt in self.categorical_time_types_sc_dt if
                              tt[0].lower() == time_type.lower() or tt[2].lower() == 'ytd']
                    # print('line 1044', self.categorical_time_types_sc_dt, time_type, cat_tt)
                    if len(cat_tt) >= 1:
                        time_type_data = list(filter(lambda x: x['sc_dt'].strftime('%Y-%m-%d') in cat_tt,
                                                     list(time_type_data)))  # why cant I filter here...
                    else:
                        cat_tt_label = None
                    # print(time_type_data)
                    for org, org_data in itertools.groupby(time_type_data, lambda x: x['_id']):
                        org_data_i += 1
                        org_data = list(org_data)
                        # print(org_data[1]['name'])
                        iterations = {"relation_i": relation_i, "time_type_i": time_type_i, "org_data_i": org_data_i,
                                      "metric_i": metric_i}
                        self.chart_data_router(metric=metric,
                                               org_data=org_data,
                                               relation=relation,
                                               time_type_data=time_type_data,
                                               iterations=iterations)
        print('out series', len(self.out))
        return {'series': self.out, 'labels': self.labels, 'y_axis_options': self.y_axis_selection,
                'column_config': self.column_config, 'filters': self.filters}

    def get_relation_dataset(self, relation):
        """
        Handles Child table requests
        :param relation:
        :return:
        """
        q = self.q.all()

        is_driver = self.model_reference.lower() == 'employee' or \
                    relation == 'Driver' or \
                    (self.data.get('child_type') == 'Driver' and relation != 'self') or \
                    (relation=='children' and 'EMP' in self.data.get('child_type', self.default_children()))

        # print('is driver!', is_driver, self.model_reference)

        id_col = 'employee_id' if is_driver else 'organization_id'
        id_name = 'employee__full_name' if is_driver else 'organization__name'
        slug = 'employee__slug' if is_driver else 'organization__slug'
        annotation = {'_id':F(id_col), 'name':F(id_name), 'slug':F(slug)}
        extra_fields = []
        if is_driver:
            annotation['driver_organization'] = F('employee__organization__name')
            annotation['driver_id'] = F('employee__raw_data_driver_id')
            extra_fields.append('driver_organization')
            extra_fields.append('driver_id')
        q = q.annotate(**annotation)
        if relation == 'self' or self.model_reference == 'Employee':
            f = {id_col: self.object.id}
        elif relation == 'children':
            child_index_type = self.data.get('child_type')

            if child_index_type is None:
                child_index_type = self.get_index_type(self.default_children(), reverse=True)
            # print(child_index_type)
            if 'svc_facl' in child_index_type.lower() or 'station' in child_index_type.lower():
                annotation['organization__parent__name'] = F('organization__parent__name')
                extra_fields.append('organization__parent__name')
            lineage = self.object.lineage(child_index_type)
            lineage = [x for x in lineage if x not in [
                1326,15,5112,622,591,560,3521,3520,]]
            f = {f'{id_col}__in': lineage}
            if self.is_battery and is_driver:
                # print('is battery and driver')
                f['index_type'] = 'EMP_DRIVER_ID_STATION' if self.object.type == 'Station' else 'EMP_DRIVER_ID'
        elif relation == 'siblings':
            f = {f'{id_col}__parent_id': self.object.parent.id}  ## get siblings
            sf = {id_col: self.object.id}  # exclude self
            return q.filter(**f).exclude(**sf)
        else:
            f = {f'{id_col}__in': self.object.lineage(relation)}
        print(f)
        return q.filter(**f), extra_fields

    def get_raw_ops_agg_data(self):
        group = self.data.get('args', {}).get('grouping')
        if group:
            f = {
                'sc_dt__gte': '2022-01-01',
                'sc_dt__lte' : self.latest_date,
            }

            if 'facility-type' in self.object_type.lower():
                fac_type = self.object.facility_type
                fac_type = ['psp', 'non-psp'] if fac_type == 'csn' else ['fleet']
                f['org_business_id__facility_type__in'] = fac_type

                self.object = Organization.objects.get(id=self.object.employees_under_id)

            if 'club' not in self.object_type.lower():
                f[self.get_index_type(self.object_type).lower()] = self.object.id

            print(f)
            tt = self.data.get('time_type')
            date = F('sc_dt')
            time_format = ('%Y-%m-%d', '%Y-%m-%d')
            annotation = {}
            out = RawOpsAggSource.objects
            rerouted = False
            if 'Day' in tt or 'D' in tt:
                f['sc_dt__gte'] = dt.datetime.today() - dt.timedelta(days=14)

            if 'W' in tt[0]:
                f['sc_dt__gte'] = dt.datetime.today() - dt.timedelta(days=14*7)
                date = Concat(ExtractYear('sc_dt'), V('-W'), ExtractWeek('sc_dt'), output_field=CharField())
                time_format = ('%Y-W%W-%w', '%Y-%m-%d')
            if 'Month' in tt or 'M' in tt:
                date = Concat(ExtractYear('sc_dt'), V('-'), ExtractMonth('sc_dt'), output_field=CharField())
                time_format = ('%Y-%m', '%Y-%m-01')
            if self.filters.get('reroute'):
                rerouted = True
                print(self.filters.get('reroute'), 'setting reroute biz rule')
                out = out.annotate(reroute_biz=self.useful_annotations['biz_reroute_exclude']).filter(reroute_biz=False)
                del self.filters['reroute']
            else:
                self.filters.pop('reroute', None)


            name = self.object.display_name
            grouping = ['date', group]
            f.update(self.data.get('filter', {}))
            annotation.update({
                'organization': V(name),

                'overall_sat_avg': Avg(F('overall_sat')),
                'response_sat_avg': Avg(F('response_sat')),
                'kept_informed_sat_avg': Avg(F('kept_informed_sat')),

                'driver_sat_avg': Avg(F('facility_sat')),
                'base_size': Count(F('overall_sat')),
                'volume': Count('*'),
                'battery_volume': Count(Case(When(tcd='Battery', then=1), default=None, output_field=IntegerField())),
                'tow_volume': Count(Case(When(tcd='Tow', then=1), default=None, output_field=IntegerField())),
                'light_service_volume': Count(Case(When(tcd='LIGHT_SVC', then=1), default=None, output_field=IntegerField())),
                'ata_avg_(all_calls)': Avg(F('ata')),
                'pta_avg_(all_calls)': Avg(F('pta')),
                'ata_minus_pta': ExpressionWrapper(Avg(F('ata')) - Avg(F('pta')), output_field=FloatField()),
                'ata_less_than_45_freq': ExpressionWrapper(Count(Case(When(ata__lte=45, then=1), default=None, output_field=IntegerField())) / Count('*'),
                                                           output_field=FloatField()),
                'long_call_freq': ExpressionWrapper(Count(Case(When(ata__gt=60, then=1), default=None, output_field=IntegerField())) / Count('*'),
                                                    output_field=FloatField()),

            })

            # todo: need to just create a dictionary with an annotation for the
            #  possible metrics here then reference request self.original metrics to see if its there. this is kind of hacky and done in haste.

            if 'battery_volume' in self.original_metrics:

                del annotation['overall_sat_avg']
                del annotation['response_sat_avg']
                del annotation['driver_sat_avg']
                del annotation['kept_informed_sat_avg']
                del annotation['base_size']
            else:
                del annotation['battery_volume']
                del annotation['tow_volume']
                del annotation['light_service_volume']
                del annotation['ata_less_than_45_freq']
                del annotation['long_call_freq']

            out = out.annotate(date=date).filter(**f).values(*grouping).annotate(**annotation)

            def clean_val(k, v):
                val_type = self.value_type_from_lookup.get(k)
                if k != 'date':
                    if 'ata_minus' in k:
                        val_type = 'float'
                    return self.format_value(v, value_type=val_type)
                elif type(v) == dt.date or type(v) == dt.datetime:
                    return self.format_value(v)
                else:
                    _v = v
                    v = v.split('-')
                    v = f"{v[0]}-{v[1].zfill(2)}"
                    v = v+'-1' if time_format[0] == '%Y-W%W-%w' else v

                    out = dt.datetime.strptime(v, time_format[0])
                    if out > dt.datetime.today(): #split year thinks it last week in december for the next yeear
                        v = _v.split('-')
                        v = f"{int(v[0]) - 1}-{v[1].zfill(2)}"
                        v = v + '-1' if time_format[0] == '%Y-W%W-%w' else v
                        out = dt.datetime.strptime(v, time_format[0])
                    print(v, out)
                    return out.strftime(time_format[1])

            out = [{k: clean_val(k, v) for k, v in x.items()} for x in out]
            if group == 'shift':
                out = sorted(out, key=lambda d: (dt.datetime.strptime(d['date'], time_format[1]), -d[group]), reverse=True) #shift sorting
            else:
                out = sorted(out, key=lambda d: dt.datetime.strptime(d['date'], time_format[1]), reverse=True) #shift sorting

            return {'series': out, 'filters': {'reroute': rerouted}}

    def get_custom_data(self):
        """
        Route for custom time types e.g. from to dates
        :return:
        """
        # if self.data.get('args', {}).get('shift'):
        #     shift = DashboardShiftGrouper(dd=self)
        #     self.out = shift.run()
        #     return {'series': self.out, 'labels': self.labels, 'y_axis_options': self.y_axis_selection,
        #             'column_config': self.column_config}
        # else:

        ddg = DashboardDayGrouper(dd=self)
        ddg.run()
        return ddg.format_chart()

    def generate_incentive_period_filter(self, period):
        filter = {
            'sc_dt_surveys__gte': period.start.strftime("%Y-%m-%d"),
            'sc_dt_surveys__lte': period.end.strftime("%Y-%m-%d"),
            'date_updated_surveys__lte': period.recorded_cutoff_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if period.end < dt.datetime.strptime('2022-01-01', '%Y-%m-%d').date():
            filter['q_chl'] = 'email'

        return filter

    def raw_surveys(self):
        """
        call for raw surveys routing
        :return:
        """
        filters = {}
        exclusions = {
        }
        annotation_filter_list = ['trouble_code__in']
        all_filters = self.data.get('filters', {})
        _order_by = self.data.get('order_by', '-recordeddate')
        base_filters = {}
        annotation_filters = {}
        print('raw surveys filter', all_filters)
        for k in list(all_filters.keys()):
            if k in annotation_filter_list:
                annotation_filters[k] = all_filters[k]
            else:
                base_filters[k] = all_filters[k]
        filters.update(base_filters)
        # annotation_filters = [{k: all_filters[k]} for k in list(all_filters.keys()) if k in annotation_filter_list]
        # filters.update(self.data.get('filters', {}))
        self.q = self.q.filter(**filters).exclude(**exclusions)

        # self.q = self.q.extra(
        #     select={'spot_minutes': "ROUND(TIMESTAMPDIFF(SECOND, FST_SPOT_TIME, LST_SPOT_TIME)/60, 1)"})
        survey_fields = [f.name for f in Std12EReduced._meta.fields]

        annotations = {name_cleaner.get(m, m): self.useful_annotations.get(m, F(m)) for m in self.original_metrics if name_cleaner.get(m, m) not in survey_fields}
        print(annotations)
        if len(self.aggregation_metrics) > 0:
            if 'driver_called' in self.aggregation_metrics:
                annotations.update({
                    'driver_called': Case(When(cm_trk=1, then=Value('Yes')),
                                          When(cm_trk=0, then=Value('No')),
                                          default=Value('No'), output_field=CharField())
                })
        # print(self.q.values())
        print('order by sorting', _order_by)
        data = self.q.annotate(**annotations)
        value_keys = list(annotations.keys())
        data = data.filter(**annotation_filters).order_by(_order_by)
        # data = data.filter(trouble_code__in=['Tow'])
        # print(data.values('spot_minutes'))
        if self.data.get('args', {}).get('page'):
            page=self.data.get('args', {}).get('page')
            rows_per_page = self.data.get('args', {}).get('rows_per_page')
            # print(page, rows_per_page)
            bottom = (page-1) * rows_per_page
            top = page * rows_per_page
            self.original_length = data.count()
            data = data[bottom: top]
            self.meta['pages'] = page
        #print('data before table', data.values())

        # value_keys.insert(5, 'spot_minutes')
        value_keys.append('emp_driver_id')
        print('table keys', value_keys)
        value_keys = value_keys + [m for m in self.original_metrics if name_cleaner.get(m, m) in survey_fields]
        self.table(
            org_data=data.values(*value_keys),
        )

    def survey_aggregator(self):
        """
        used for aggregating survey cards in survey dashboards
        :return:
        """

        if self.data.get('chart_type') == 'numberHighlights':
            operations = {
                'avg': Avg,
                'count': Count,
                'sum': Sum
            }
            annotation = {m: operations[m.split('_')[-1]]('_'.join(m.split('_')[:-1])) for m in self.original_metrics}
            print(annotation)
            results = []

            print("QUERY:", self.q_array[0][0].query)

            for q, start in self.q_array:
                result = q.aggregate(**annotation)
                result['start'] = start
                results.append(result)

            if self.data.get('args', {}).get('comp'):
                tier_data = []
                for r in results[:4]:
                    tier_data.append(self.assign_survey_tier(r))
                print(tier_data)
                self.out.append({
                    'type': 'thresholdComparison',
                    'name': 'tier_overview',
                    'value': tier_data[0],
                    'history': [{'idx': x['tier_index'], 'difference': x['next_level']['Difference'], 'start': x['start']} for x in tier_data]
                })

            for (i, m) in enumerate(self.original_metrics):
                # print(m, results)
                series = [r.get(m) for r in results]
                # print(series)
                try:
                    mean = statistics.mean([s for s in series if s is not None])
                    std = statistics.stdev([s for s in series if s is not None])
                except statistics.StatisticsError:
                    try:
                        mean = [s for s in series if s is not None][0]
                        std = mean / 10
                    except:
                        mean = 0
                        std = 0
                self.out.append({
                    'series': series,
                    'type': 'tinyLine',
                    'labels': [r.get('start') for r in results],
                    'name': self.metrics[i],
                    'avg': mean,
                    'std': std,
                    'variance': (series[0]-mean)/std if series[0] and std != 0 else 0
                })
        else:
            filters = {}

            filters.update(self.data.get('filters', {}))
            self.q = self.q.filter(**filters)
            metric_column_operation = [(m, '_'.join(m.split('_')[:-1]), m.split('_')[-1]) for m in
                                       self.original_metrics]
            annotations = {}

            for metric, column, operation in metric_column_operation:
                operations = {'avg': Avg(column), 'count': Count(column), 'sum': Sum(column)}
                metric = metric.replace('facility_sat', 'driver_sat')
                annotations[metric] = operations[operation]
            if 'children' in self.relations:
                child_type = self.data.get('child_type', self.default_children())
                if self.data_target == 'std12e_reduced':
                    try:
                        child_type = self.get_index_type(child_type.title())
                    except:
                        child_type = child_type.upper()

                annotations.update(
                    {'name': F(f"{child_type.lower()}__{'full_name' if 'EMP' in child_type else 'name'}"),
                     'id': F(f'{child_type.lower()}'),
                    'slug': F(f"{child_type.lower()}__slug")
                     }
                )

                if 'EMP' in child_type and self.object_type in ['Station-Business', 'Station']:
                    annotations['driver_organization'] = V(self.object.name)
                    annotations['driver_id'] = F('emp_driver_id__raw_data_driver_id')
                elif 'EMP' in child_type:
                    annotations['driver_organization'] = F('emp_driver_id__organization__name')
                    annotations['driver_id'] = F('emp_driver_id__raw_data_driver_id')

                # print('max min date', self.q.sc_dt_surveys.max(), self.q.sc_dt_surveys.min())
                self.q = self.q.values(child_type.lower())
                print('annotations', annotations)

                data = self.q.annotate(**annotations).values(*annotations.keys())
                print(data[0])
                if self.data.get('args', {}).get('showTiers'):
                    data = [self.assign_survey_tier(x, True) for x in data]
                self.table(org_data=data)
            else:
                if self.data.get('chart_type', 'numberHighlights') == 'numberHighlights':
                    self.number_highlights(org_data=self.q.aggregate(**annotations))
                elif len(self.categorical_time_types_sc_dt) > 0:
                    self.group_surveys_by_time(annotations)
                    #
                    # self.bar(grouped_data=self.q.aggregate(**annotations))
            # print(f'annotations are {annotations}')

    def group_surveys_by_time(self, aggregation):

        if type(self.categorical_time_types_sc_dt[0]) == dict:
            when_list = []
            lookup_col = 'custom_time_group'
            print('categorical time types', self.categorical_time_types_sc_dt)
            for i, cat in enumerate(self.categorical_time_types_sc_dt):
                date_from, date_to = cat['from'], cat['to']
                when_list.append(When(sc_dt_surveys__gte=date_from, sc_dt_surveys__lte=date_to, then=V(f'{date_from} to {date_to}')))
            self.q = self.q.annotate(custom_time_group=Case(*when_list, default=V('outside_time_frame'), output_field=CharField()))
            surveys = self.q.exclude(custom_time_group='outside_time_frame')
            # print(surveys, 'after filtering')
            # surveys = surveys.values('custom_time_group').annotate(**aggregation)
        else:
            lookup_col = 'month_year'
            self.q = self.q.annotate(month_year=
                                     Concat(ExtractYear('sc_dt_surveys', output_field=CharField()),
                                            V('-'),
                                            LPad(ExtractMonth('sc_dt_surveys', output_field=CharField()), 2, V('0')),
                                            V('-01'),
                                            )
                                     )
            surveys = self.q.filter(month_year__in=[date[1].strftime('%Y-%m-%d') for date in self.categorical_time_types_sc_dt])
        # print(surveys, 'after filtering')
        surveys = surveys.values(lookup_col).annotate(**aggregation)
        grouped_data=list(surveys.values(*list(aggregation.keys()) + [lookup_col]))
        # print(' grouped data', grouped_data)

        for metric in self.original_metrics:
            if len(grouped_data) > 0:
                self.bar(grouped_data = grouped_data, metric=metric)

    def assign_survey_tier(self, scores, basic=False):
        scores['tier'] = 'Below'
        scores['tier_index'] = 0
        scores['sat_threshold'] = 0
        scores['next_level'] = None
        print('assign_survey_tier', scores)
        for i, tier_name in enumerate(['Below', 'Tier-1', 'Tier-2', 'Tier-3']):
            if self.fac_type.lower() == 'fleet' and tier_name == 'Tier-3':
                continue
            tier = next(item for item in self.tiers if item["name"] == tier_name)
            print('assign_survey_tier', tier)
            metrics = tier.get('metrics').split(',') if tier.get('metrics') is not None else None
            score = [scores.get(metric.strip(), 0) for metric in metrics]
            score = round(sum([s*100 if s is not None else 0 for s in score]), 1)
            if basic:
                if score >= tier['bottom'] and score < tier['top']:
                    scores['tier'] = tier['name']
                scores.pop('tier_index', None)
                scores.pop('sat_threshold', None)
                scores.pop('next_level', None)
            else:
                if score >= tier['bottom'] and score < tier['top']:
                        scores['tier'] = tier['name']
                        scores['color'] = {
                            'Below': 'red-10',
                            'Tier-1': 'amber-10',
                            'Tier-2': 'purple-10',
                            'Tier-3': 'green-10'
                        }[tier['name']]
                        scores['sat_threshold'] = score
                        scores['performance_score'] = score
                        scores['perf_metrics_used'] = tier.get('metrics').replace('facility', 'driver').replace(' avg', '').upper().replace('_', ' ')
                        scores['tier_index'] = i

                        if tier['name'] == 'Tier-3' or (self.fac_type.lower() == 'fleet' and tier_name == 'Tier-2'):
                            scores['next_level'] = {
                                'Next Tier': tier.get('name'),
                                'Difference': score - tier['bottom'],
                                'Threshold': tier['bottom'],
                                'score': score
                            }
                elif score < tier['bottom'] and scores['next_level'] is None:
                    scores['next_level'] = {
                        'Next Tier': tier.get('name'),
                        'Difference': score - tier['bottom'],
                        'Threshold': tier['bottom'],
                        'score': score
                    }

        return scores

    def get_survey_data(self):
        """Main survey call"""
        print('get_survey_data')
        # self.baseQ = self.baseQ.filter(IS_VALID_INCLUDES_CANCELED=False)
        # Cancelled Calls
        # self.baseQ = Std12EReduced.objects.filter(is_valid_record=False, IS_VALID_INCLUDES_CANCELED=1)
        #Exclude Cancelled Calls)
        # self.baseQ = Std12EReduced.objects.filter(is_valid_record=True)
        #All Calls (Include Both Cancelled and Non-Cancelled Calls)
        # self.baseQ = Std12EReduced.objects.filter(IS_VALID_INCLUDES_CANCELED=1)
        # print(self.baseQ.query)
        # self.baseQ = Std12EReduced.objects.filter(is_valid_includes_canceled=True)
        # self.baseQ = Std12EReduced.objects.filter(is_valid_includes_canceled=True)

        # self.baseQ = Std12EReduced.objects.filter(is_valid_record=True, is_valid_includes_canceled=1)
        # self.baseQ = Std12EReduced.objects.filter(is_valid_includes_canceled=True)

        # self.baseQ = Std12EReduced.objects.filter(is_valid_record=False, is_valid_includes_canceled=1)


        print('filters', self.filters)
        # 'Is_Valid_Include_Cancelled'
        if self.request.data.get('additional_filters').get('is_valid_includes_canceled'):
            if self.request.data.get('additional_filters').get('is_valid_includes_canceled') == 'all_calls':
                self.baseQ = Std12EReduced.objects.filter(is_valid_includes_canceled=True)
            if self.request.data.get('additional_filters').get('is_valid_includes_canceled') == 'cancelled_calls':
                self.baseQ = Std12EReduced.objects.filter(is_valid_record=False, is_valid_includes_canceled=1)
            if self.request.data.get('additional_filters').get('is_valid_includes_canceled') == 'non_cancelled_calls':
                self.baseQ = Std12EReduced.objects.filter(is_valid_record=True)
        else:
            self.baseQ = Std12EReduced.objects.filter(is_valid_record=True)

        if self.data.get('args', {}).get('comp', False):
            self.filters.pop('sc_dt_surveys__lte', None)
            self.filters.pop('sc_dt_surveys__gte', None)

        if self.filters.get('reroute'):
            print(self.filters.get('reroute'), 'setting reroute biz rule')
            self.baseQ = self.baseQ.annotate(reroute_biz=self.useful_annotations['biz_reroute_exclude']).filter(reroute_biz=False)
            del self.filters['reroute']
        else:
            self.filters.pop('reroute', None)

        # if self.filters.get('order_by'):
        #     self.survey_order_by = self.filters['order_by']
        #     del self.filters['order_by']

        self.q = self.baseQ.filter(**self.filters)


        print(self.object_type)

        if self.object_type != 'Club':
            self.q = self.q.filter(**{self.get_index_type(self.object_type).lower(): self.object.id})

        org = self.object if self.model_reference == 'Organization' else self.object.organization
        self.fac_type = 'fleet' if org.facility_type == 'Fleet' else 'csn'
        if 'fac_type__in' in self.filters or 'sc_svc_prov_type__in' in self.filters:
            self.fac_type = 'fleet' if self.filters.get('sc_svc_prov_type__in') == ['F'] else 'csn'

        # todo: check the tiers for std12etiers
        # self.tiers = list(Std12ETiers.objects.filter(type=self.fac_type, year__gte=dt.datetime.today().year).values())

        self.incentive_periods = \
            Std12ETierTimePeriods.objects.filter(type=self.fac_type, show_until__lte=dt.datetime.today()).order_by('-start')
        self.incentive_period = Std12ETierTimePeriods.objects.filter(type=self.fac_type, show_until__gte=dt.datetime.today()).order_by(
            'start')[0] #this is last time period because of show_until, current is show_until__gte=today [0]
        print('current incentive period', self.incentive_period.start)


        # date filters

        skip_incentive_time_filter = 'last_n' in self.filters \
            or ('sc_dt_surveys__gte' in self.filters or 'sc_dt_surveys__lte' in self.filters) or len(
            self.categorical_time_types_sc_dt) > 0
        self.tiers = list(Std12ETiers.objects.filter(type='csn', year=2023).values())

        if self.data.get('args', {}).get('comp') or not skip_incentive_time_filter:
            # self.tiers = list(Std12ETiers.objects.filter(type=self.fac_type.lower(), year__gte=dt.datetime.today().year).values())

            print('applying incentive filters', self.filters, self.categorical_time_types_sc_dt)

            self.q_array = [(self.q.filter(**self.generate_incentive_period_filter(self.incentive_period)), self.incentive_period.start)] + [(self.q.filter(**self.generate_incentive_period_filter(period)), period.start) for period in
                            self.incentive_periods[:13]]

            self.q = self.q_array[0][0]

            self.meta['dates'] = {
                'start': self.incentive_period.start,
                'end': self.incentive_period.end,
                'upload_start': '2021-01-01',
                'upload_end': self.incentive_period.recorded_cutoff
              }
        else:
            print('filters are', self.filters)
            if 'sc_dt_surveys__gte' in self.filters or 'sc_dt_surveys__lte' in self.filters:
                dt_from = dt.datetime.strptime(self.filters.get('sc_dt_surveys__gte'), '%Y-%m-%d')
                dt_to = dt.datetime.strptime(self.filters.get('sc_dt_surveys__lte',
                                                              dt.datetime.strftime(dt.datetime.today(), '%Y-%m-%d')
                                                              ), '%Y-%m-%d')
                day_span = (dt_to - dt_from).days
                self.q_array = [(self.q, self.filters.get('sc_dt_surveys__gte'))]
                for period in range(1, 13):
                    f_update = {
                        'sc_dt_surveys__gte': (dt_from - dt.timedelta(day_span*period)).strftime('%Y-%m-%d'),
                        'sc_dt_surveys__lte': (dt_to - dt.timedelta(day_span * period)).strftime('%Y-%m-%d'),
                    }
                    filter = dict(self.filters, **f_update)
                    self.q_array.append((self.baseQ.filter(**filter), filter['sc_dt_surveys__gte']))


        # print(self.data)





        routines = {
            'survey_aggregator': self.survey_aggregator,
            'raw_surveys': self.raw_surveys,
            'survey_comments': self.survey_comments,
        }
        routine = self.data.get('args', {'routine': 'survey_aggregator'})['routine']
        routines[routine]()
        out =  {'series': self.out, 'labels': self.labels, 'y_axis_options': self.y_axis_selection,
                'column_config': self.column_config, 'original_length': self.original_length, 'meta': self.meta}

        if 'survey' in routine:
            out['incentive_periods'] = [{"start": self.incentive_period.start, "end": self.incentive_period.end}] + list(self.incentive_periods[:1].values())

        return out

    def survey_comments(self):
        parameters = self.data.get('args')
        relevant_comments = CommentsSurveysE.objects.filter(survey__is_valid_record=True)
        relevant_comments = relevant_comments.filter(survey__q_chl=self.data.get('filters', {}).get('q_chl', 'smsinvite'))
        words_used = None

        if parameters.get('search', []) != []:
            words_used = []
            search_terms = parameters['search']
            model = Word2Vec.load('static/std12e_bigram.model')
            for term in search_terms:
                this_search = [term, ]
                if 'skip_related_words' not in parameters:
                    try:
                        related_words = model.most_similar(positive=[term])
                        related_words = related_words[:3]
                        for r in related_words:
                            this_search.append(r[0])

                    except:
                        print("couldnt find related words")
                relevant_comments = relevant_comments.filter(
                    reduce(operator.or_, (Q(tokenized_comment__contains=x) for x in this_search)))
                words_used.append(this_search)

        if parameters.get('sentiment', {}) != {}:
            relevant_comments = relevant_comments.filter(**parameters['sentiment'])

        # organization
        if self.object.id != 1:  # if its not aca-club
            filter = self.get_index_type(self.object_type)
            filter_query = {'survey__' + filter.lower(): self.object.id}
            relevant_comments = relevant_comments.filter(**filter_query)

        # # dates
        # print("SURVEY COMMENTS", parameters)

        filter_d = {}
        for filter, value in self.data.get('filters', {}).items():
            filter_param = 'survey__' + filter
            filter_d[filter_param] = value

        relevant_comments = relevant_comments.filter(**filter_d)

        if parameters.get('topic', "") != "":
            print("TOPIC IS SET TO", parameters['topic'])
            topic_comments = CommentTopics.objects.filter(topic=parameters['topic']).values('survey_id')
            relevant_comments = relevant_comments.filter(survey_id__in=topic_comments)
            with open('templates/category_words.json', 'r') as f:
                topicJson = json.loads(f.read())
            words_used = [topicJson[parameters['topic']]]

        relevant_comments = relevant_comments.order_by('-survey__sc_dt')[parameters['lower_bound']: parameters['upper_bound']]
        print('getting the metrics', self.original_metrics)
        annotation = {name_cleaner.get(m, m): self.useful_annotations.get(m, F(f'survey__{m}')) for m in self.original_metrics if name_cleaner.get(m, m) not in [f.name for f in CommentsSurveysE._meta.fields]}
        values = list(annotation.keys()) + [m for m in self.original_metrics if name_cleaner.get(m, m) in [f.name for f in CommentsSurveysE._meta.fields]]
        # print(annotation.keys())
        # print(values)
        relevant_comments = relevant_comments\
            .annotate(**annotation).values(*values)
        output = {'data': relevant_comments}

        if words_used:
            output['query_terms_used'] = words_used

        self.out = output
