import sys
sys.path.insert(0, 'root')
from accounts.models import *
import statistics
import sys
sys.path.insert(0, 'root')
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from accounts.models import *
from .serializers import *
from .models import *
from django.db.models import Avg, Count, Sum, Min, Max
import json
from django.db.models import FloatField
import numpy as np

from django.db.models import *


def generate_biz_rules_annotation(metric_list, surveys, aggregate=True, annotate=False, bypass=[], show_rule_counts=False, prefix=''):
    '''
    NOTE: this assumes you have applied other filters related to organization, and time period
    :param metric_list:
    :return:
    '''


    print("args for biz rules annotations",
          metric_list,
          f'aggregate set to {aggregate}',
          f'annotate set to {annotate}',
          f'rules bypassed {bypass}')

    annotation_d = {}
    for m in metric_list:
        biz_rules = {
            # dont count reroutes when not satisified unless sister reroute
            'reroutes': {
                m: 0,
                'reroute_360': 1,
                'sister_reroute': 0,
            },
            # dont count first_spot_delays when not satisified

            'first_spot_delay': {
                m: 0,
                'first_spot_delay': 1,
            },

            # dont count approved-reroutes when not satisfied

            # 'reroute_appeals': {
            #     m: 0,
            #     'appeals_request__request_data__status': 'Approved-Reroute',
            # },

            ## exclusions

            'duplicate': {
                'duplicate': 1
            },

            # 'distribution': {
            #     'distribution': 'SMS'
            # },

            # 'remove_appeals': {
            #     'appeals_request__request_data__status': 'Approved-Remove'
            # },

            'remove': {
                'remove': 1
            }
        }

        for rule in bypass:
            annotation_d[rule] = {}

        inside_logic = Case(When(
            # Q(**biz_rules['reroutes']) |
            # Q(**biz_rules['first_spot_delay']) |
            # Q(**biz_rules['reroute_appeals']) |
            # Q(**biz_rules['duplicate']) |
            # Q(**biz_rules['distribution']) |
            # Q(**biz_rules['remove_appeals']) |
            Q(**biz_rules['remove']), then=None), default=F(m),
            output_field=FloatField()
        )

        annotation_d[f'{prefix}{m}_avg'] = Avg(m)
        annotation_d[f'{prefix}{m}_sum'] = Sum(m)
        annotation_d[f'{prefix}{m}_count'] = Count(m)

        if show_rule_counts:
            for k,v in biz_rules.items():
                annotation_d[f'{k}_count'] = Sum(Case(When(**v, then=1), default=0, output_field=IntegerField()))

    if aggregate:
        return surveys.aggregate(**annotation_d)
    if annotate:
        print(annotation_d)
        return surveys.annotate(**annotation_d)


class DashboardBase(APIView):

    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()
    # serializer_class = None
    www_authenticate_realm = 'api'
    parser_classes = (JSONParser, MultiPartParser, FormParser)


    def __init__(self):

        # IMPORT UTILITY FUNCTIONS
        # self.importUtilities()

        ### SETTINGS ####
        self.SHOW_MONEY = True
        self.CHECK_ID_DRIVER_VOLUME_PREV_MONTH_THRESHOLD = 90
        self.CHECK_ID_STATION_VOLUME_PREV_MONTH_THRESHOLD = 500
        self.fac_type = None
        self.comp_period = None
        self.comp_start = None
        self.comp_end = None
        self.warning = False
        self.default_upper_limit = 1000
        self.metricMetaData = False
        self.showConditionalFormatting = False

        self.object = None
        self.user = None
        self.purpose_router = {
            'timeseries': self.timeseries,
            'driverScheduler': self.driverScheduler,
            'calendar': self.calendar,
            'calendar_custom': self.calendar_custom,
            'survey_comments': self.survey_comments,
            'maps_logging': self.maps_logging,
            'maps': self.maps,
            'training': self.training,
            'single_survey': self.single_survey,
            'survey_aggregator': self.survey_aggregator,
            'mtk_campaign_survey_month_data': self.mtk_campaign_survey_month_data,
            'battery_aggregator': self.battery_aggregator,
            'new_surveys_check': self.new_surveys_check,
            'timeseries_predictor': self.timeseries_predictor,
            'scheduler_navigate': self.scheduler_navigate,
            'scheduler': self.scheduler,
            'updateUserGoals': self.updateUserGoals,
            'get_cities': self.get_cities,
            'get_skill_level': self.get_skill_level,
            'get_xlsx_schedule_template': self.get_xlsx_schedule_template,
            'upload_xlsx_schedule': self.upload_xlsx_schedule,
            'save_upload_schedule': self.save_upload_schedule,
            'scheduler_utils': self.scheduler_utils,
            # 'dashboard_data': self.get_data
        }
        self.time_type_conversions = {
            'Month': "M",
            'Day': "D",
            'Hour': "H",
            'Week': "W-MON",
            'Prev_week': "W-Mon",
            'MTD_Last_Year': 'mtd_last_year',
            'YTD': 'ytd',
            'Year': 'ytd',
            'Prev_Year': 'ytd',
            'MTD_Prev_3_Months': 'mtd_prev_3_months',
            'This_Calendar_Quarter': 'this_calendar_quarter',
            'prev_month': 'M',
            'Prev_Month': 'M',
            'this_month': 'M',
            'This_Month': 'M',
            'This_Quarter': 'Q',
            'Incentive': 'INCENTIVE',
            'This_Incentive': 'INCENTIVE',
            'Hour_of_Day': 'HOUR_GROUP',
            'Day_of_Week': 'WEEKDAY_GROUP',
            'Day_and_Hour_of_Week': 'WEEKDAY_HOUR_GROUP',
            'Last_Incentive': 'INCENTIVE',
            'Last_N_Surveys': 'Last_N_Surveys',
            'custom': 'D',
            'R12': 'R12',
            'TIMESERIES': False
        }
        self.eligible_months = {
            'std12e': ['Month', 'Week', 'Day', 'Incentive','Hour_of_Day', 'Day_and_Hour_of_Week','Day_of_Week'],
            'ops': ['Month', 'Day', 'Hour', 'Week','Hour_of_Day', 'Day_and_Hour_of_Week','Day_of_Week']
        }
        self.survey_key_converter = {
            'sc_dt': 'Service Date',
            'SC_DT': 'Service Date',
            'outc1': 'overall_sat',
            'sc_svc_prov_type': 'Provider Type',
            'q24': 'response_sat',
            'q26': 'kept_informed_sat',
            'driver5': 'request_service_sat',
            'driver10': 'driver_sat',
            'gte': '>=',
            'lte': '<=',
            'date_updated_surveys': 'data_collection_close_date',
            'recordeddate': 'recorded_date'
        }

        self.prov_type_conversion = {
            # 'C': 'CSN',
            'P': "PSP",
            'F': "Fleet",
            'C': "Non-PSP"
        }





        self.metric_metadata = {}
        self.index_type = None
        self.this_month = dt.date.today().replace(day=1)
        self.yesterday = dt.date.today() - dt.timedelta(days=1)
        self.model_reference = None
        self.object_type = None
        self.employee_types = ['Driver', 'Call-Center-Operator', 'Facility-Rep']
        self.organization_types = ['Club',  'Station-Business', 'Station', 'Grid',
                                   'Call-Center','Club-Facility-Type','Facility-Rep', 'avl_zone', 'Station-State']
        self.survey_vs_ops()
        self.default_from_date = "2019-01-01"

    def tcd_conversion(self, tcd_list):
        out = []
        if '6' in tcd_list:
            out.append('Tow')
        if '3' in tcd_list:
            out.append('Battery')
        if '1' in tcd_list:
            out.append('Light Service')
        return out

    def clean_filter_fields(self, filter_d, prefix=""):
        new_d = {}
        # print('filters display', filter_d)
        for orig_field, orig_val in filter_d.items():
            new_val = orig_val
            new_field = orig_field
            # print(orig_field, "CONVERSION FILTERS")

            if 'directional' in orig_field or 'is_valid_record' in orig_field:
                continue

            if orig_field == 'remove':
                continue

            # if orig_field == 'appeals_request__request_data__status':
            #     orig_field = 'Appealed'

            for k, conv in self.survey_key_converter.items():

                if k in new_field:
                    new_field = new_field.replace(k, conv)
                    # print(new_field)
                    if 'sat' in new_field:
                        new_val = [self.survey_response_mapping(f) for f in orig_val]
                    if 'Provider Type' in new_field:
                        new_val = [self.prov_type_conversion[v] for v in orig_val]

                if 'tcd' in orig_field:
                    # print("TCD in Field List")
                    new_val = self.tcd_conversion(orig_val)
                if 'date_updated_surveys' in orig_field and type('date_updated_surveys') == str:
                    try:
                        new_val = orig_val.strftime("%Y-%m-%d")
                    except:
                        new_val = orig_val[:10]
                if 'fleet_supervisor' in orig_field:
                    new_val = Employee.objects.get(id=orig_val).full_name
                if type(new_val) == bool:
                    if not new_val:
                        continue
                    else: new_val=""
                if type(new_val) == dict:
                    if 'caveat_m' in new_val:
                        new_field = new_field + " UNLESS " + new_val['caveat_m'].upper()
                    if type(new_val.get('with_ts_val')) == str:
                        new_val = new_val.get('with_ts_val')
                    else:
                        new_val = ""
                if type(new_val) == list:
                    new_val = [str(v) for v in new_val]
                    new_val = ",".join(new_val)
            new_d[prefix + new_field.upper().replace('_', ' ').replace('  ', ' ')] = new_val
        return new_d

    def post(self, request, *args, **kwargs):

        if len(request.data) == 0:
            return  Response("System OK. No data was passed in the request.", status=status.HTTP_200_OK)

        data = request.data

        if 'remind_me' in data:
            return Response(self.remind_me_choices(), status=status.HTTP_200_OK)

        if 'max_db_date' in data:
            return Response(self.get_max_db_date(), status=status.HTTP_200_OK)

        self.user = request.user

        self.get_object(data)
        self.purpose = data['purpose']

        if 'parameters' in data:
            self.params=data['parameters']
        allowed = self.check_user_permission()


        if not allowed:
            return Response("USER NOT ALLOWED TO VIEW THIS OBJECT BY PERMISSIONS", status=status.HTTP_403_FORBIDDEN)

        if self.purpose == 'get_goals':
            for parent in self.get_object_chain():
                mygoals = MetricGoals.objects.filter(organization=parent, metric__element__in=data['parameters']['metrics'], employee=self.user.employee())
                goals = MetricGoals.objects.filter(organization=parent, metric__element__in=data['parameters']['metrics'], employee__isnull=True)
                if goals:
                    break
            print(mygoals)
            print(goals)
            return Response(list(mygoals.values('month', 'metric__element', 'target', 'range')) + list(goals.values('month', 'metric__element', 'target', 'range')), status=status.HTTP_200_OK)


        if 'showConditionalFormatting' in data['parameters']:
            if data['parameters']['showConditionalFormatting']:
                self.metricMetaData = self.getMetricMetaData(data['parameters'])
                self.showConditionalFormatting = True

        if 'relation' in data['parameters']:
            if type(data['parameters']['relation']) == list:
                output = {}
                for r in data['parameters']['relation']:
                    params = data['parameters']
                    params['relation'] = r
                    output[r] = self.purpose_router[data['purpose']](params)

                if self.warning:
                    output['warning'] = self.warning

                return Response(output, status=status.HTTP_200_OK)
        if data['purpose'] == 'upload_xlsx_schedule':
            output = self.purpose_router[data['purpose']](request)
            return Response(output, status=status.HTTP_200_OK)
        output = self.purpose_router[data['purpose']](data['parameters'])
        # if data['purpose'] == 'get_csv_schedule_template':
        #     return output

        return Response(output, status=status.HTTP_200_OK)

    def check_user_permission(self):
        if self.params:
            if 'ranking' in self.params or 'skill_name' in self.params:
                return True

        user_permissions = self.user.employee().permission.all()
        print('user permissions', user_permissions.values_list('name', flat=True))

        if ('see-all' in user_permissions.values_list('name', flat=True)):
            return True

        # if it's a driver, build the lineage from teh parent
        lineage = self.get_object_chain()
        eligible_children = self.user.employee().organization.children()
        eligible_siblings = self.user.employee().organization.parent.children()

        related_orgs = self.user.employee().organization.related_orgs
        if related_orgs:
            print(related_orgs)
            related_orgs = json.loads(related_orgs)['related-slug']
            related_org_children = []
            for org in related_orgs:
                this_org = Organization.objects.get(slug=org)
                for child in this_org.children():
                    related_org_children.append(child)
        else:
            related_orgs = []
            related_org_children = []
        # print("other orgs allowed: ", related_orgs)

        is_self = False
        is_sibling = False
        is_children = False
        is_parent = False
        emp_org = self.user.employee().organization

        if self.model_reference == 'Employee':
            object_org = self.object.organization
        else:
            object_org = self.object

        print(object_org.slug, related_orgs, self.object, emp_org, "CHECK PERMISSION")

        if (self.object == emp_org) or (self.object == self.user.employee()) or (object_org.slug in related_orgs):
            is_self = True

        if self.object == self.user.employee().organization.parent:
            is_parent = True

        if any((x.parent() if x.type == 'station' else x) in lineage for x in eligible_siblings):
            is_sibling = True

        if any(x in lineage for x in eligible_children):
            is_children = True

        if any(x in lineage for x in related_org_children):
            is_children = True

        print("LINEAGE", is_children, lineage, (x in lineage for x in eligible_children), eligible_children)

        if ('see-siblings' in user_permissions.values_list('name', flat=True)):
            if is_self or is_sibling or is_children or is_parent:
                return True

        if ('see-children' in user_permissions.values_list('name', flat=True)):
            if is_self or is_children:
                return True

        if ('see-only-self' in user_permissions.values_list('name', flat=True)):
            if is_self:
                return True

        # Don't know if this makes sense but it is specific for scheduler and if the user does not have 'see-all' permission -Jesus
        try:
            if (('scheduler-edit' in user_permissions.values_list('name', flat=True) or
                'scheduler-see-all' in user_permissions.values_list('name', flat=True)) and
                self.object == self.user.employee().organization
            ):
                return True
        except:
            pass

        return False


    def get_max_db_date(self):
        return DashboardUpdateHistory.objects.latest('date_updated').date_updated


    def get_cities(self, parameters):
        filter = {self.get_index_type(self.object_type).lower(): self.object.id}
        if self.index_type != 'Club':
            cities = Std12EReduced.objects.filter(**filter).values_list('bl_near_cty_nm', flat=True).distinct()
        else:
            cities = Std12EReduced.objects.values_list('bl_near_cty_nm', flat=True).distinct()
        print(parameters)
        if 'grids' in parameters:
            if self.index_type != 'Club':
                grids = Std12EReduced.objects.filter(**filter).values_list('grid_id', flat=True).distinct()
            else:
                grids = Std12EReduced.objects.values_list('grid_id', flat=True).distinct()
            return {'cities': cities, 'grids': grids}
        else:
            return cities


    def get_object_chain(self):
        child = self.object
        eligibles = [child, ]
        if type(child) == Employee:
            eligibles.append(child.organization)
            if child.position_type == 'Driver':
                for o in child.organization.children():
                    eligibles.append(o)
            child = child.organization
        while child.parent is not None:
            eligibles.append(child.parent)
            child = child.parent
        return eligibles


    def get_children_to_station_business(self, ob):
        if not ob:
            ob = self.object
            ob_type = object.type
        else:
            ob_type = ob.type
        if ob_type == 'Club':
            return Organization.objects.filter(type='Station-Business')
        if ob_type == 'Club-Region':
            markets = Organization.objects.filter(type="Market", parent_id=ob.id)
            territories = Organization.objects.filter(type='Territory', parent__in=markets)
            return Organization.objects.filter(type='Station-Business').filter(parent__in=territories)
        elif ob_type == 'Market':
            territories = Organization.objects.filter(type='Territory', parent_id=ob.id)
            return Organization.objects.filter(type='Station-Business').filter(parent__in=territories)
        elif ob_type == 'Territory':
            return Organization.objects.filter(type='Station-Business').filter(parent=ob.id)
        elif ob_type == 'Station-Business':
            return [ob]

    def print_sql(self, qs):
        q = qs.query.__str__()
        if settings.DEBUG:
            import sqlparse
            print(sqlparse.format(q, reindent=True, keyword_case='upper'))
        else:
            return q


    def pretty(self, d, indent=0):
        for key, value in d.items():
            if isinstance(value, dict):
                self.pretty(value, indent + 1)
            else:
                print('\t' * (indent + 1) + str(value))


    def getMetricMetaData(self, parameters):
        metricMetaData = False

        metricMetaData = {}
        defaults = {}
        mData = {}
        thisEmployeeData = {}
        self.availableMetricMetaData = set()
        for metric in parameters['metrics']:
            thisEmployeeData[metric] = list(MetricGoals.objects.filter(metric__element=metric,
                                                                       employee=self.user.employee(),
                                                                       organization=self.object.id).values(
                'metric__element',
                'target', 'range',
                'month'))
            metricMetaData[metric] = False
            defaults[metric] = False
            for parent in self.get_object_chain():
                print(parent)
                defaults[metric] = MetricGoals.objects.filter(metric__element=metric,
                                                              organization=parent, month__isnull=True)

                if not metricMetaData[metric]:
                    metricMetaData[metric] = list(MetricGoals.objects.filter(metric__element=metric,
                                                                             organization=parent).values(
                        'metric__element',
                        'target', 'range', 'month'))
                if metricMetaData[metric] and defaults[metric]:
                    break
            if metricMetaData[metric]:

                print(metricMetaData[metric])
                self.availableMetricMetaData.add(metric)
                for period in metricMetaData[metric]:
                    if period['metric__element'] not in mData:
                        mData[period['metric__element']] = {}
                    if period['month'] is None:
                        period['month'] = 'default'
                    mData[period['metric__element']][period['month']] = {'target': period['target'],
                                                                         'range': period['range']}
                for period in thisEmployeeData[metric]:
                    if period['metric__element'] not in mData:
                        mData[period['metric__element']] = {}
                    if period['month'] is None:
                        period['month'] = 'default'
                    mData[period['metric__element']][period['month']] = {'target': period['target'],
                                                                         'range': period['range']}
            for metric, targets in mData.items():
                if 'default' not in mData[metric]:
                    metric_defaults = defaults[metric].filter(metric__element=metric).values('target', 'range')
                    if metric_defaults:
                        mData[metric]['default'] = list(metric_defaults)[0]
                    else:
                        time_range = list(mData[metric].keys())
                        mData[metric]['default'] = mData[metric][time_range[-1]]

        return mData


    def get_object(self, data):
        print(data)
        # type is the type of indexing id i.e. Region, Territory, Grid, Driver etc.
        self.index_type = data['type']

        if self.index_type == 'Territory-Facility-Type' and 'fleetType' in data['slug']:
            print(data['slug'])
            data['slug'] = data['slug'].replace('-fleetType', '')
            data['type'] = 'Territory'
            self.index_type = 'Territory'
            print(data['slug'], "NEW SLUG")

        # if we get an id, then we are done and can return the object.
        # its not necessary to return the variable, since we can access it via self anyway...

        if 'organization_id' in data:
            self.object = Organization.objects.get(id=data['organization_id'])
            self.object_type = self.object.type
            self.queryset = DashboardAggregations.objects.filter(organization_id=self.object.id)
            return self.object

        elif 'employee_id' in data:
            self.object = Employee.objects.get(id=data['employee_id'])
            self.object_type = self.object.position_type
            self.queryset = DashboardAggregations.objects.filter(employee_id=self.object.id)
            return self.object

        self.employee_types = ['Driver', 'Call-Center-Operator', 'Facility-Rep']
        self.organization_types = ['Club',  'Station-Business', 'Station', 'Grid',
                                   'Call-Center','Club-Facility-Type','Facility-Rep', 'avl_zone', 'Station-State']
        if data['type'] in self.organization_types:
            self.model_reference = 'Organization'
            if 'id' in data:
                self.object = Organization.objects.get(id=data['id'], type=data['type'])
            elif 'slug' in data:
                self.object = Organization.objects.get(slug=data['slug'], type=data['type'])
            self.object_type = self.object.type
            self.queryset = DashboardAggregations.objects.filter(organization_id=self.object.id)

        elif data['type'] in self.employee_types:
            self.model_reference = 'Employee'
            if 'id' in data:
                self.object = Employee.objects.get(id=data['id'], position_type=data['type'])
            elif 'slug' in data:
                self.object = Employee.objects.get(slug=data['slug'], position_type=data['type'])
            self.object_type = self.object.position_type
            self.queryset = DashboardAggregations.objects.filter(employee_id=self.object.id)
            # print(self.object.name)
        else:
            print(data['type'], "COULD NOT FIND")
            raise Exception("Type improperly specified, cannot find.")
        self.index_db_type = self.get_index_type(self.index_type)
        print(self.object.id)


    def field_name_conversion(self, field):
        field = field.split('_')
        percent_str = ['freq']
        linear_str = ['sum', 'count', 'avg', 'median', 'volume']
        if 'sat' in field and 'avg' in field:
            return 'percentage'
        if any(x in percent_str for x in field):  # and not any(x in percent_str for x in ['count']):
            # print(field, 'percentage')
            return 'percentage'
        elif any(x in linear_str for x in field):
            # print(field, 'number')
            return 'number'
        else:
            # print(field, 'other')
            return 'other'


    def survey_response_mapping(self, numeric_value):
        if numeric_value is None:
            return 'Left Blank'

        converter = {
            0: "Unknown",  # TODO: What is this?
            1: "Totally Satisfied",
            2: 'Satisfied',
            3: 'Neither Satisfied nor Disatisfied',
            4: 'Dissatisfied',
            5: 'Totally Dissatisfied',
            6: 'Left Blank'
        }

        return converter[numeric_value]


    def remind_me_choices(self):
        # TODO: add subCategory
        meta_fields = DashboardAggregations._meta.fields
        # self.survey_vs_ops()
        output = {}
        for field in meta_fields:
            field = str(field).split('.')[-1]
            try:
                field_type = self.metric_metadata[field][1]
            except KeyError:
                field_type = 'other'

            if field_type == 'cost' and not self.SHOW_MONEY:
                continue

            if field_type not in output:
                output[field_type] = {}
            field_dict = {
                'name': field,
                'type': self.field_name_conversion(field),
                'eligible_time_types': self.eligible_months[self.metric_metadata[field][0]] if self.field_name_conversion(
                    field) != 'other' else 'NA'
            }
            if 'metrics' not in output[field_type]:
                output[field_type]['metrics'] = []
            output[field_type]['metrics'].append(field_dict)
        return output


    def clean_parameters(self, parameters, parameter_ideal_list):
        for p in parameter_ideal_list:
            if p in parameters:
                continue
            else:
                parameters[p] = None
        return parameters


    def default_children(self, object_type):
        defaults = {
            'Club': 'ORG_FACILITY_STATE',
            'Station-State': 'ORG_BUSINESS_ID',
            'Station-Business': 'ORG_SVC_FACL_ID',
            'Station': 'EMP_DRIVER_ID',
        }

        other_way = {}
        for k, v in defaults.items():
            other_way[self.get_index_type(k)] = v

        combined_defaults = {**defaults, **other_way}

        # if self.purpose != 'survey_aggregator':
        #     defaults['Territory'] = 'ORG_BUSINESS_ID'

        return combined_defaults[object_type]


    def default_parent(self, object_type):
        defaults = {
            'Driver': 'Station-Business',
            'Station': 'Station-Business',
            'Station-Business': 'Territory',
            'Territory': 'Market',
            'Market': 'Club-Region',
            'Club-Region': 'Club',
            'Club-Region-Facility-Type': 'Club-Facility-Type',
            'Market-Facility-Type': 'Club-Region-Facility-Type',
            'Territory-Facility-Type': 'Market-Facility-Type',
        }
        other_way = {}
        for k, v in defaults.items():
            other_way[self.get_index_type(k)] = v

        combined_defaults = {**defaults, **other_way}

        return combined_defaults[object_type]


    def get_index_type(self, object_type, reverse=False):
        if object_type is None:
            return None

        converter = {
            'Club': 'CLUB',
            'Club-Region': 'ORG_CLUB_REGION',
            'Call-Center-Operator': 'EMP_CALL_CENTER_OPERATOR',
            'Driver': 'EMP_DRIVER_ID',
            'Station-Business': 'ORG_BUSINESS_ID',
            'Call-Center': 'ORG_CALL_CENTER',
            'Call-Center-Group': 'ORG_CALL_CENTER_GROUP',
            'Grid': 'ORG_GRID',
            'Market': 'ORG_MARKET_ID',
            'Station': 'ORG_SVC_FACL_ID',
            # 'Territory': 'ORG_TERRITORY_ID',
            'Club-Facility-Type': 'Club-Facility-Type',
            'Club-Region-Facility-Type': 'Club-Region-Facility-Type',
            'Market-Facility-Type': 'Market-Facility-Type',
            'Territory-Facility-Type': 'Territory-Facility-Type',
            'Fleet-Supervisor': 'FLEET_SUPERVISOR',
            'City': 'bl_near_cty_nm',
            'avl_zone': 'avl_zone',
            'State': 'bl_state_cd',
            # 'Facility-Rep': 'ORG_FACILITY_REP',
            'Station-State': 'ORG_FACILITY_STATE'
        }
        reverse_converter = {v: k for k, v in converter.items()}

        all_converter = {**converter, **reverse_converter}

        if reverse:
            return all_converter[object_type]
        return all_converter[object_type]


    def get_filter_time_type(self, time_type):
        filtered_time_type = time_type.split('_')[1]
        filtered_time_type = filtered_time_type[0].upper()
        return filtered_time_type


    def check_id_eligibility(self, final_output):
        OBJECT_TYPE = final_output[0]['type']
        for f in range(len(final_output)):
            if final_output[f]['groupName'] == "prev_month":
                for d in range(len(final_output[f]['data'])):
                    if final_output[f]['data'][d]['label'] == 'volume':
                        PREV_MONTH_VOLUME = final_output[f]['data'][d]['value']
        if OBJECT_TYPE == 'Driver':
            CUTOFF = self.CHECK_ID_DRIVER_VOLUME_PREV_MONTH_THRESHOLD
        else:
            CUTOFF = self.CHECK_ID_STATION_VOLUME_PREV_MONTH_THRESHOLD

        ELIGIBLE = PREV_MONTH_VOLUME >= CUTOFF
        return {
            "eligible": ELIGIBLE,
            "prev_month_volume": PREV_MONTH_VOLUME,
            "cutoff": CUTOFF
        }


    def applyStdDev(self, formatted, time_type):
        metric_names = [x['groupName'] for x in formatted]
        useGoals = False
        self.warning = ' ** Using Standard Deviation for Conditional Formatting **'
        if self.metricMetaData:
            if any([name in self.availableMetricMetaData for name in metric_names]):
                self.warning = ' ** Using Goals for Conditional Formatting **'
                useGoals = True
                high = {}
                low = {}

        for metric in range(len(formatted)):
            metric_name = formatted[metric]['groupName']
            high = None
            low = None
            goal = None
            if not useGoals:
                metric_vals = []
                for time in range(len(formatted[metric]['data'])):
                    val = formatted[metric]['data'][time]['value']
                    if val is not None:
                        metric_vals.append(val)
                avg = statistics.mean(metric_vals)
                std_dev = statistics.stdev(metric_vals)
                high = avg + 1.5 * std_dev
                low = avg - 1.5 * std_dev
            for time in range(len(formatted[metric]['data'])):
                val = formatted[metric]['data'][time]['value']
                if useGoals and metric_name in self.metricMetaData:
                    goals_dt = formatted[metric]['data'][time]['label'].replace(day=1).date()
                    print(time_type, formatted[metric]['data'][time]['label'], goals_dt)
                    goals_time = goals_dt if time_type in (
                    'Day', 'Month', 'Week') and goals_dt.year >= 2020 and goals_dt.month > 1 else 'default'
                    try:
                        goal = self.metricMetaData[metric_name][goals_time]['target']
                    except KeyError:
                        goals_time = 'default'
                        goal = self.metricMetaData[metric_name][goals_time]['target']
                    if formatted[metric]['data'][time]['value_type'] == 'percentage' and val is not None:
                        if val > 1 and goal < 1:
                            goal = goal * 100
                    goal = round(goal, 1)
                    high = goal + self.metricMetaData[metric_name][goals_time]['range']
                    low = goal - self.metricMetaData[metric_name][goals_time]['range']
                    print(formatted[metric]['data'][time]['value_type'], val, high)
                if val is not None and high is not None and low is not None:
                    formatted[metric]['data'][time]['std_val'] = (1, goal) if val > high else (-1, goal) if val < low else (
                    0, goal) if useGoals else None
        return formatted


    def custom_calendar_sum(self, metric):
        return Sum(metric)


    def weighted_average(self, metric, denom):
        return Sum(metric, output_field=FloatField()) / Sum(denom, output_field=FloatField()) * 100


    def average(self, metric):
        return Avg(metric)


    def get_aggregations(self, metrics):
        aggregations = {}

        print(metrics)
        for m in metrics:
            try:
                aggregations[m + '_agg'] = self.metric_metadata[m][2]
            except:
                print(m)
                raise Exception("BAD METRIC")
        return aggregations


    def reduce_size(self, parameters, queryset):
        if len(queryset) > self.default_upper_limit:
            print("Too Many to return!!")
            if "lower_limit" not in parameters:
                queryset = queryset[0: self.default_upper_limit]
                lower_limit = 0
                upper_limit = self.default_upper_limit
                print(len(queryset))
            else:
                queryset = queryset[parameters['lower_limit']: parameters['upper_limit']]
                lower_limit = parameters['lower_limit']
                upper_limit = parameters['upper_limit']
            self.warning = "Too Many values returned limited returned number to between %s and %s" % (
            lower_limit, upper_limit)

        return queryset

    def rolling_pearsons(self, data, pair, window_size):
        # pair is a tuple of groupName values len 2
        pearsons_lists = {}
        for metric in data[0]:
            pearsons_lists[metric['groupName']] = [d['value'] for d in metric['data']]
        assert len(pair) == 2, "pair should be tuple of length 2"
        length = len(pearsons_lists[pair[0]])
        p_vals = []
        for i in range(length):
            end = i + window_size
            if end > length:
                break
            l1 = pearsons_lists[pair[0]][i:end]
            l2 = pearsons_lists[pair[1]][i:end]
            p = np.corrcoef(l1, l2)[0, 1]
            p_vals.append(p)
        print(p_vals)

    def calculate_deviation(self, out_std, out_avg, m, val, val_type, sc_dt, time_type):
        metricMetaData = self.metricMetaData
        if not self.showConditionalFormatting:
            return None

        if val is None:
            return None
        # print(metricMetaData)
        if metricMetaData:
            useGoals = True
            if m in metricMetaData:
                self.warning = ' ** Using Goals for Conditional Formatting **'
                time = sc_dt.replace(day=1) if time_type in ('M', 'D', 'W-MON') else 'default'
                try:
                    goal = metricMetaData[m][time]['target']
                except KeyError:
                    time = 'default'
                    goal = metricMetaData[m][time]['target']
                if val_type == 'percentage' and val > 1:
                    val = val / 100
                if val_type == 'percentage' and goal > 1:
                    goal = goal / 100

                high = goal + metricMetaData[m][time]['range']
                low = goal - metricMetaData[m][time]['range']

            else:
                return None
        else:
            useGoals = False
            self.warning = ' ** Using Standard Deviation for Conditional Formatting **'
            std = out_std[m + "_std"] if m + "_std" in out_std else None
            avg = out_avg[m + "_avg"] if m + "_avg" in out_avg else None
            if std is None or avg is None:
                return None

            if val_type == 'percentage' and val > 1:
                val = val / 100
            low = avg - (std * 1.5)
            high = avg + (std * 1.5)
            goal = None

        print("std dev", m, val, high, low, val > high)
        goal = round(goal * 100, 1) if goal < 1 else goal
        if val > high:
            print('high val')
            return (1, goal)
        elif val < low:
            print('low val')
            return (-1, goal)
        else:
            print('mid val')
            if useGoals:
                return (0, goal)
            else:
                return None


    def convert_percentage(self, number, type):
        if type == 'percentage':
            if number is None:
                return None
            return round(number * 100, 1)
        else:
            if number is None:
                return None
            return round(number, 2)

    def new_surveys_check(self, parameters):

        # 0 Check if the user is a driver

        print('request parameters', parameters['previous_last_login'])
        employee = Employee.objects.get(user_id=self.request.user.id)
        if employee.position_type == 'Driver':
            surveys = Std12EReduced.objects.filter(date_updated_surveys__gte=parameters['previous_last_login'], emp_driver_id=employee.id)
            return surveys.count()
        else:
            return 'Not a driver'
        # 1 Get the employee of the requesting user

        # 2 Lookup all the surveys for that user std12e raw
            # - filter it emp_driver_id

        # 3 Filter the query set for any date updated survey greater than last login






    def survey_vs_ops(self):
        # time_type is an integer id where...
        # first number is metric_type
        # second number is period
        # third number is agg_method
        self.metric_metadata = {
            'has_tablet_volume': ('ops', 'volume', self.custom_calendar_sum('has_tablet_volume')),
            'check_id_compliant_with_tablet_freq': (
                'ops', 'check_id', self.weighted_average('check_id_compliant_count', 'has_tablet_volume')),
            'dispatch_communicated_count': ('ops', 'kmi'),
            'volume': ('ops', 'volume', self.custom_calendar_sum('volume')),
            'dispatch_communicated_freq': ('ops', 'kmi'),
            'ata_median': ('ops', 'response_time'),
            'ata_minus_pta_median': ('ops', 'response_time'),
            'base_cost_avg': ('ops', 'cost'),
            'base_cost_sum': ('ops', 'cost'),
            'battery_volume': ('ops', 'volume'),
            'batt_test_on_batt_call_count': ('ops', 'battery'),
            'batt_test_on_batt_call_freq': ('ops', 'battery'),
            'call_accepted_count': ('ops', 'call_acceptance_closure'),
            'call_accepted_freq': ('ops', 'call_acceptance_closure'),
            'call_cost_avg': ('ops', 'cost'),
            'call_cost_sum': ('ops', 'cost'),
            'cancelled_count': ('ops', 'call_acceptance_closure'),
            'cancelled_freq': ('ops', 'call_acceptance_closure'),
            'credit_card_spend_avg': ('ops', 'cost'),
            'credit_card_spend_sum': ('ops', 'cost'),
            'dispatch_call_member_count': ('ops', 'kmi'),
            'dispatch_call_member_freq': ('ops', 'kmi'),
            'dispatch_call_out_count': ('ops', 'kmi'),
            'dispatch_call_out_freq': ('ops', 'kmi'),
            'driver_sat_aaa_mgmt_all_avg': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_all_count': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_battery_avg': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_battery_count': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_not_tow_avg': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_not_tow_count': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_tow_avg': ('std12m', 'std12m'),
            'driver_sat_aaa_mgmt_tow_count': ('std12m', 'std12m'),
            'driver_sat_stations_all_avg': ('std12m', 'std12m'),
            'driver_sat_stations_all_count': ('std12m', 'std12m'),
            'driver_sat_stations_battery_avg': ('std12m', 'std12m'),
            'driver_sat_stations_battery_count': ('std12m', 'std12m'),
            'driver_sat_stations_not_tow_avg': ('std12m', 'std12m'),
            'driver_sat_stations_not_tow_count': ('std12m', 'std12m'),
            'driver_sat_stations_tow_avg': ('std12m', 'std12m'),
            'driver_sat_stations_tow_count': ('std12m', 'std12m'),
            'early_count': ('ops', 'response_time'),
            'early_freq': ('ops', 'response_time'),
            'enroute_cost_avg': ('ops', 'cost'),
            'enroute_cost_sum': ('ops', 'cost'),
            'est_response_sat_aaa_mgmt_all_avg': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_all_count': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_battery_avg': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_battery_count': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_not_tow_avg': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_not_tow_count': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_tow_avg': ('std12m', 'std12m'),
            'est_response_sat_aaa_mgmt_tow_count': ('std12m', 'std12m'),
            'est_response_sat_stations_all_avg': ('std12m', 'std12m'),
            'est_response_sat_stations_all_count': ('std12m', 'std12m'),
            'est_response_sat_stations_battery_avg': ('std12m', 'std12m'),
            'est_response_sat_stations_battery_count': ('std12m', 'std12m'),
            'est_response_sat_stations_not_tow_avg': ('std12m', 'std12m'),
            'est_response_sat_stations_not_tow_count': ('std12m', 'std12m'),
            'est_response_sat_stations_tow_count': ('std12m', 'std12m'),
            'est_response_sat_stations_tow_avg': ('std12m', 'std12m'),
            'eta_update_avg': ('ops', 'response_time'),
            'external_call_out_count': ('ops', 'kmi'),
            'external_call_out_freq': ('ops', 'kmi'),
            'g_to_g_count': ('ops', 'call_acceptance_closure'),
            'g_to_g_freq': ('ops', 'call_acceptance_closure'),
            'g_to_ng_count': ('ops', 'call_acceptance_closure'),
            'g_to_ng_freq': ('ops', 'call_acceptance_closure'),
            'heavy_user_count': ('ops', 'check_id'),
            'heavy_user_freq': ('ops', 'check_id'),
            'late_count': ('ops', 'response_time'),
            'late_freq': ('ops', 'response_time'),
            'long_ata_count': ('ops', 'response_time'),
            'long_ata_freq': ('ops', 'response_time'),
            'ng_to_g_count': ('ops', 'call_acceptance_closure'),
            'ng_to_g_freq': ('ops', 'call_acceptance_closure'),
            'ng_to_ng_count': ('ops', 'call_acceptance_closure'),
            'ng_to_ng_freq': ('ops', 'call_acceptance_closure'),
            'not_tow_volume': ('ops', 'volume'),
            'no_service_rendered_count': ('ops', 'call_acceptance_closure'),
            'no_service_rendered_freq': ('ops', 'call_acceptance_closure'),
            'on_time_count': ('ops', 'response_time'),
            'on_time_freq': ('ops', 'response_time'),
            'operator_overall_sat_aaa_mgmt_all_count': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_all_avg': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_battery_count': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_battery_avg': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_not_tow_count': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_not_tow_avg': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_tow_count': ('std12m', 'std12m'),
            'operator_overall_sat_aaa_mgmt_tow_avg': ('std12m', 'std12m'),
            'operator_overall_sat_stations_all_count': ('std12m', 'std12m'),
            'operator_overall_sat_stations_all_avg': ('std12m', 'std12m'),
            'operator_overall_sat_stations_battery_count': ('std12m', 'std12m'),
            'operator_overall_sat_stations_battery_avg': ('std12m', 'std12m'),
            'operator_overall_sat_stations_not_tow_count': ('std12m', 'std12m'),
            'operator_overall_sat_stations_not_tow_avg': ('std12m', 'std12m'),
            'operator_overall_sat_stations_tow_count': ('std12m', 'std12m'),
            'operator_overall_sat_stations_tow_avg': ('std12m', 'std12m'),
            'outside_communicated_count': ('ops', 'kmi'),
            'outside_communicated_freq': ('ops', 'kmi'),
            'overall_sat_aaa_mgmt_all_count': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_all_avg': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_battery_count': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_battery_avg': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_not_tow_count': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_not_tow_avg': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_tow_count': ('std12m', 'std12m'),
            'overall_sat_aaa_mgmt_tow_avg': ('std12m', 'std12m'),
            'overall_sat_stations_all_count': ('std12m', 'std12m'),
            'overall_sat_stations_all_avg': ('std12m', 'std12m'),
            'overall_sat_stations_battery_count': ('std12m', 'std12m'),
            'overall_sat_stations_battery_avg': ('std12m', 'std12m'),
            'overall_sat_stations_not_tow_count': ('std12m', 'std12m'),
            'overall_sat_stations_not_tow_avg': ('std12m', 'std12m'),
            'overall_sat_stations_tow_count': ('std12m', 'std12m'),
            'overall_sat_stations_tow_avg': ('std12m', 'std12m'),
            'pta_median': ('ops', 'response_time'),
            'replaced_batt_on_failed_batt_call_count': ('ops', 'battery'),
            'replaced_batt_on_failed_batt_call_freq': ('ops', 'battery'),
            'response_sat_aaa_mgmt_all_count': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_all_avg': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_battery_count': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_battery_avg': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_not_tow_count': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_not_tow_avg': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_tow_count': ('std12m', 'std12m'),
            'response_sat_aaa_mgmt_tow_avg': ('std12m', 'std12m'),
            'response_sat_stations_all_count': ('std12m', 'std12m'),
            'response_sat_stations_all_avg': ('std12m', 'std12m'),
            'response_sat_stations_battery_count': ('std12m', 'std12m'),
            'response_sat_stations_battery_avg': ('std12m', 'std12m'),
            'response_sat_stations_not_tow_count': ('std12m', 'std12m'),
            'response_sat_stations_not_tow_avg': ('std12m', 'std12m'),
            'response_sat_stations_tow_count': ('std12m', 'std12m'),
            'response_sat_stations_tow_avg': ('std12m', 'std12m'),
            'short_freq': ('ops', 'response_time'),
            'spp_call_member_count': ('ops', 'kmi'),
            'spp_call_member_freq': ('ops', 'kmi'),
            'text_message_count': ('ops', 'kmi'),
            'text_message_freq': ('ops', 'kmi'),
            'tow_cost_avg': ('ops', 'cost'),
            'tow_cost_sum': ('ops', 'cost'),
            'tow_volume': ('ops', 'volume'),
            'truck_call_member_count': ('ops', 'kmi'),
            'truck_call_member_freq': ('ops', 'kmi'),
            'overall_sat_std12_e': ('std12e', 'std12e'),
            'response_sat_std12_e': ('std12e', 'std12e'),
            'kept_informed_sat_std12_e': ('std12e', 'std12e'),
            'request_service_sat_std12_e': ('std12e', 'std12e'),
            'facility_sat_std12_e': ('std12e', 'std12e'),
            'overall_sat_std12_e_tot_sat_count': ('std12e', 'std12e'),
            'response_sat_std12_e_tot_sat_count': ('std12e', 'std12e'),
            'kept_informed_sat_std12_e_tot_sat_count': ('std12e', 'std12e'),
            'request_service_sat_std12_e_tot_sat_count': ('std12e', 'std12e'),
            'facility_sat_std12_e_tot_sat_count': ('std12e', 'std12e'),
            'sample_a_count': ('std12m', 'std12m'),
            'sample_b_count': ('std12m', 'std12m'),
            'volume_pred': ('ops', 'volume'),
            'volume_pred_upper': ('ops', 'volume'),
            'volume_pred_lower': ('ops', 'volume'),
            'check_id_compliant_freq': ('ops', 'check_id'),
            'check_id_compliant_count': ('ops', 'check_id', self.custom_calendar_sum('check_id_compliant_count')),
            'overall_sat_std12_e_count': ('std12e', 'std12e'),
            'overall_sat_std12_m_count': ('std12m', 'std12m'),
            'arc_kmi_avg': ('ops', 'kmi'),
            'overall_sat_count_std12_e_ruled': ('std12e', 'std12_e'),
            'overall_sat_avg_std12_e_ruled': ('std12e', 'std12_e'),
            'check_id_no_scan_showed_id_drivers_license_freq': ('ops', 'check_id'),
            'check_id_no_scan_showed_id_registration_freq': ('ops', 'check_id'),
            'check_id_no_scan_reason_decline_scan_count': ('ops', 'check_id'),
            'check_id_decline_reason_no_id_verify_freq': ('ops', 'check_id'),
            'check_id_alt_id_registration_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_alt_id_registration_count')),
            'check_id_check_fail_freq': (
                'ops', 'check_id', self.weighted_average('check_id_check_fail_count', 'check_id_compliant_count')),
            'check_id_showed_valid_id_count': ('ops', 'check_id'),
            'check_id_manual_freq': ('ops', 'check_id'),
            'check_id_decline_reason_no_valid_id_freq': ('ops', 'check_id'),
            'check_id_decline_run_call_freq': (
                'ops', 'check_id', self.weighted_average('check_id_decline_run_call_count', 'check_id_compliant_count')),
            'check_id_scan_count': ('ops', 'check_id', self.custom_calendar_sum('check_id_scan_count')),
            'check_id_ran_call_with_no_id_freq': ('ops', 'check_id'),
            'check_id_alt_id_passport_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_alt_id_passport_count')),
            'check_id_decline_run_call_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_decline_run_call_count')),
            'check_id_scan_freq': (
                'ops', 'check_id', self.weighted_average('check_id_scan_count', 'check_id_compliant_count')),
            'check_id_no_scan_showed_valid_id_freq': ('ops', 'check_id'),
            'check_id_declined_reason_no_id_match_count': ('ops', 'check_id'),
            'check_id_no_scan_reason_id_check_fail_freq': ('ops', 'check_id', self.weighted_average(
                'check_id_no_scan_reason_id_check_fail_count', 'check_id_compliant_count')),
            'check_id_alt_id_military_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_alt_id_military_count')),
            'check_id_ran_call_no_id_reason_other_freq': ('ops', 'check_id'),
            'check_id_manual_count': ('ops', 'check_id'),
            'check_id_check_fail_count': ('ops', 'check_id', self.custom_calendar_sum('check_id_check_fail_count')),
            'check_id_no_scan_showed_id_military_freq': ('ops', 'check_id'),
            'check_id_ran_call_no_id_reason_safety_freq': ('ops', 'check_id'),
            'check_id_run_call_reason_other_count': ('ops', 'check_id'),
            'check_id_alt_id_other_govt_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_alt_id_other_govt_count')),
            'check_id_alt_id_dl_count': ('ops', 'check_id'),
            'check_id_no_scan_reason_declined_scan_freq': ('ops', 'check_id'),
            'check_id_declined_reason_no_valid_id_count': ('ops', 'check_id'),
            'check_id_run_call_reason_safety_count': ('ops', 'check_id'),
            'check_id_no_scan_reason_scan_fail_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_no_scan_reason_scan_fail_count')),
            'check_id_no_scan_showed_id_passport_freq': ('ops', 'check_id'),
            'check_id_no_scan_reason_scan_failed_freq': ('ops', 'check_id', self.weighted_average(
                'check_id_no_scan_reason_scan_fail_count', 'check_id_compliant_count')),
            'check_id_alt_id_foreign_count': (
                'ops', 'check_id', self.custom_calendar_sum('check_id_alt_id_foreign_count')),
            'check_id_ran_call_bad_id_count': ('ops', 'check_id'),
            'check_id_no_scan_showed_id_other_govt_freq': ('ops', 'check_id'),
            'check_id_no_scan_showed_id_foreign_freq': ('ops', 'check_id'),
            'check_id_declined_reason_no_name_match_count': ('ops', 'check_id'),
            'check_id_declined_reason_gone_on_arrival_count': ('ops', 'check_id'),
            'check_id_declined_reason_no_name_match_freq': ('ops', 'check_id'),
            'check_id_declined_reason_gone_on_arrival_freq': ('ops', 'check_id'),

            'check_id_alt_id_no_dl_count': ('ops', 'check_id'),
            'check_id_alt_id_no_dl_freq': ('ops', 'check_id'),
            'check_id_scan_screen_used_count': ('ops', 'check_id'),
            'check_id_scan_screen_used_freq': ('ops', 'check_id'),

            'aaa_mgmt_any_facility_sat_avg': ('std12e', 'surveys_aaa_mgmt_all_types',
                                              self.weighted_average('aaa_mgmt_any_facility_sat_sum',
                                                                    'aaa_mgmt_any_facility_sat_count')),
            'aaa_mgmt_any_facility_sat_count': (
                'std12e', 'surveys_aaa_mgmt_all_types', self.custom_calendar_sum('aaa_mgmt_any_facility_sat_count')),
            'aaa_mgmt_any_facility_sat_sum': ('std12e', 'surveys_aaa_mgmt_all_types'),
            'aaa_mgmt_any_kept_informed_sat_avg': ('std12e', 'surveys_aaa_mgmt_all_types',
                                                   self.weighted_average('aaa_mgmt_any_kept_informed_sat_sum',
                                                                         'aaa_mgmt_any_kept_informed_sat_count')),
            'aaa_mgmt_any_kept_informed_sat_count': (
                'std12e', 'surveys_aaa_mgmt_all_types', self.custom_calendar_sum('aaa_mgmt_any_kept_informed_sat_count')),
            'aaa_mgmt_any_kept_informed_sat_sum': ('std12e', 'surveys_aaa_mgmt_all_types'),
            'aaa_mgmt_any_overall_sat_avg': ('std12e', 'surveys_aaa_mgmt_all_types',
                                             self.weighted_average('aaa_mgmt_any_overall_sat_sum',
                                                                   'aaa_mgmt_any_overall_sat_count')),
            'aaa_mgmt_any_overall_sat_count': (
                'std12e', 'surveys_aaa_mgmt_all_types', self.custom_calendar_sum('aaa_mgmt_any_overall_sat_count')),
            'aaa_mgmt_any_overall_sat_sum': ('std12e', 'surveys_aaa_mgmt_all_types'),
            'aaa_mgmt_any_request_service_sat_avg': ('std12e', 'surveys_aaa_mgmt_all_types',
                                                     self.weighted_average('aaa_mgmt_any_request_service_sat_sum',
                                                                           'aaa_mgmt_any_request_service_sat_count')),
            'aaa_mgmt_any_request_service_sat_count': (
                'std12e', 'surveys_aaa_mgmt_all_types', self.custom_calendar_sum('aaa_mgmt_any_request_service_sat_count')),
            'aaa_mgmt_any_request_service_sat_sum': ('std12e', 'surveys_aaa_mgmt_all_types'),
            'aaa_mgmt_any_response_sat_avg': ('std12e', 'surveys_aaa_mgmt_all_types',
                                              self.weighted_average('aaa_mgmt_any_response_sat_sum',
                                                                    'aaa_mgmt_any_response_sat_count')),
            'aaa_mgmt_any_response_sat_count': (
                'std12e', 'surveys_aaa_mgmt_all_types', self.custom_calendar_sum('aaa_mgmt_any_response_sat_count')),
            'aaa_mgmt_any_response_sat_sum': ('std12e', 'surveys_aaa_mgmt_all_types'),
            'aaa_mgmt_battery_facility_sat_avg': ('std12e', 'surveys_aaa_mgmt_battery',
                                                  self.weighted_average('aaa_mgmt_battery_facility_sat_sum',
                                                                        'aaa_mgmt_battery_facility_sat_count')),
            'aaa_mgmt_battery_facility_sat_count': (
                'std12e', 'surveys_aaa_mgmt_battery', self.custom_calendar_sum('aaa_mgmt_battery_facility_sat_count')),
            'aaa_mgmt_battery_facility_sat_sum': ('std12e', 'surveys_aaa_mgmt_battery'),
            'aaa_mgmt_battery_kept_informed_sat_avg': ('std12e', 'surveys_aaa_mgmt_battery',
                                                       self.weighted_average('aaa_mgmt_battery_kept_informed_sat_sum',
                                                                             'aaa_mgmt_battery_kept_informed_sat_count')),
            'aaa_mgmt_battery_kept_informed_sat_count': (
                'std12e', 'surveys_aaa_mgmt_battery', self.custom_calendar_sum('aaa_mgmt_battery_kept_informed_sat_count')),
            'aaa_mgmt_battery_kept_informed_sat_sum': ('std12e', 'surveys_aaa_mgmt_battery'),
            'aaa_mgmt_battery_overall_sat_avg': ('std12e', 'surveys_aaa_mgmt_battery',
                                                 self.weighted_average('aaa_mgmt_battery_overall_sat_sum',
                                                                       'aaa_mgmt_battery_overall_sat_count')),
            'aaa_mgmt_battery_overall_sat_count': (
                'std12e', 'surveys_aaa_mgmt_battery', self.custom_calendar_sum('aaa_mgmt_battery_overall_sat_count')),
            'aaa_mgmt_battery_overall_sat_sum': ('std12e', 'surveys_aaa_mgmt_battery'),
            'aaa_mgmt_battery_request_service_sat_avg': ('std12e', 'surveys_aaa_mgmt_battery', self.weighted_average(
                'aaa_mgmt_battery_request_service_sat_sum', 'aaa_mgmt_battery_request_service_sat_count')),
            'aaa_mgmt_battery_request_service_sat_count': ('std12e', 'surveys_aaa_mgmt_battery',
                                                           self.custom_calendar_sum(
                                                               'aaa_mgmt_battery_request_service_sat_count')),
            'aaa_mgmt_battery_request_service_sat_sum': ('std12e', 'surveys_aaa_mgmt_battery'),
            'aaa_mgmt_battery_response_sat_avg': ('std12e', 'surveys_aaa_mgmt_battery',
                                                  self.weighted_average('aaa_mgmt_battery_response_sat_sum',
                                                                        'aaa_mgmt_battery_response_sat_count')),
            'aaa_mgmt_battery_response_sat_count': (
                'std12e', 'surveys_aaa_mgmt_battery', self.custom_calendar_sum('aaa_mgmt_battery_response_sat_count')),
            'aaa_mgmt_battery_response_sat_sum': ('std12e', 'surveys_aaa_mgmt_battery'),
            'aaa_mgmt_not_tow_facility_sat_avg': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                  self.weighted_average('aaa_mgmt_not_tow_facility_sat_sum',
                                                                        'aaa_mgmt_not_tow_facility_sat_count')),
            'aaa_mgmt_not_tow_facility_sat_count': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                    self.custom_calendar_sum('aaa_mgmt_not_tow_facility_sat_count')),
            'aaa_mgmt_not_tow_facility_sat_sum': ('std12e', 'surveys_aaa_mgmt_light_service'),
            'aaa_mgmt_not_tow_kept_informed_sat_avg': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                       self.weighted_average('aaa_mgmt_not_tow_kept_informed_sat_sum',
                                                                             'aaa_mgmt_not_tow_kept_informed_sat_count')),
            'aaa_mgmt_not_tow_kept_informed_sat_count': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                         self.custom_calendar_sum(
                                                             'aaa_mgmt_not_tow_kept_informed_sat_count')),
            'aaa_mgmt_not_tow_kept_informed_sat_sum': ('std12e', 'surveys_aaa_mgmt_light_service'),
            'aaa_mgmt_not_tow_overall_sat_avg': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                 self.weighted_average('aaa_mgmt_not_tow_overall_sat_sum',
                                                                       'aaa_mgmt_not_tow_overall_sat_count')),
            'aaa_mgmt_not_tow_overall_sat_count': (
                'std12e', 'surveys_aaa_mgmt_light_service', self.custom_calendar_sum('aaa_mgmt_not_tow_overall_sat_count')),
            'aaa_mgmt_not_tow_overall_sat_sum': ('std12e', 'surveys_aaa_mgmt_light_service'),
            'aaa_mgmt_not_tow_request_service_sat_avg': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                         self.weighted_average(
                                                             'aaa_mgmt_not_tow_request_service_sat_sum',
                                                             'aaa_mgmt_not_tow_request_service_sat_count')),
            'aaa_mgmt_not_tow_request_service_sat_count': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                           self.custom_calendar_sum(
                                                               'aaa_mgmt_not_tow_request_service_sat_count')),
            'aaa_mgmt_not_tow_request_service_sat_sum': ('std12e', 'surveys_aaa_mgmt_light_service'),
            'aaa_mgmt_not_tow_response_sat_avg': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                  self.weighted_average('aaa_mgmt_not_tow_response_sat_sum',
                                                                        'aaa_mgmt_not_tow_response_sat_count')),
            'aaa_mgmt_not_tow_response_sat_count': ('std12e', 'surveys_aaa_mgmt_light_service',
                                                    self.custom_calendar_sum('aaa_mgmt_not_tow_response_sat_count')),
            'aaa_mgmt_not_tow_response_sat_sum': ('std12e', 'surveys_aaa_mgmt_light_service'),
            'aaa_mgmt_tow_facility_sat_avg': ('std12e', 'surveys_aaa_mgmt_tow',
                                              self.weighted_average('aaa_mgmt_tow_facility_sat_sum',
                                                                    'aaa_mgmt_tow_facility_sat_count')),
            'aaa_mgmt_tow_facility_sat_count': (
                'std12e', 'surveys_aaa_mgmt_tow', self.custom_calendar_sum('aaa_mgmt_tow_facility_sat_count')),
            'aaa_mgmt_tow_facility_sat_sum': ('std12e', 'surveys_aaa_mgmt_tow'),
            'aaa_mgmt_tow_kept_informed_sat_avg': ('std12e', 'surveys_aaa_mgmt_tow',
                                                   self.weighted_average('aaa_mgmt_tow_kept_informed_sat_sum',
                                                                         'aaa_mgmt_tow_kept_informed_sat_count')),
            'aaa_mgmt_tow_kept_informed_sat_count': (
                'std12e', 'surveys_aaa_mgmt_tow', self.custom_calendar_sum('aaa_mgmt_tow_kept_informed_sat_count')),
            'aaa_mgmt_tow_kept_informed_sat_sum': ('std12e', 'surveys_aaa_mgmt_tow'),
            'aaa_mgmt_tow_overall_sat_avg': ('std12e', 'surveys_aaa_mgmt_tow',
                                             self.weighted_average('aaa_mgmt_tow_overall_sat_sum',
                                                                   'aaa_mgmt_tow_overall_sat_count')),
            'aaa_mgmt_tow_overall_sat_count': (
                'std12e', 'surveys_aaa_mgmt_tow', self.custom_calendar_sum('aaa_mgmt_tow_overall_sat_count')),
            'aaa_mgmt_tow_overall_sat_sum': ('std12e', 'surveys_aaa_mgmt_tow'),
            'aaa_mgmt_tow_request_service_sat_avg': ('std12e', 'surveys_aaa_mgmt_tow',
                                                     self.weighted_average('aaa_mgmt_tow_request_service_sat_sum',
                                                                           'aaa_mgmt_tow_request_service_sat_count')),
            'aaa_mgmt_tow_request_service_sat_count': (
                'std12e', 'surveys_aaa_mgmt_tow', self.custom_calendar_sum('aaa_mgmt_tow_request_service_sat_count')),
            'aaa_mgmt_tow_request_service_sat_sum': ('std12e', 'surveys_aaa_mgmt_tow'),
            'aaa_mgmt_tow_response_sat_avg': ('std12e', 'surveys_aaa_mgmt_tow',
                                              self.weighted_average('aaa_mgmt_tow_response_sat_sum',
                                                                    'aaa_mgmt_tow_response_sat_count')),
            'aaa_mgmt_tow_response_sat_count': (
                'std12e', 'surveys_aaa_mgmt_tow', self.custom_calendar_sum('aaa_mgmt_tow_response_sat_count')),
            'aaa_mgmt_tow_response_sat_sum': ('std12e', 'surveys_aaa_mgmt_tow'),
            'comp_any_facility_sat_avg': ('std12e', 'surveys_compensation_all_types',
                                          self.weighted_average('comp_any_facility_sat_sum',
                                                                'comp_any_facility_sat_count')),
            'comp_any_facility_sat_count': (
                'std12e', 'surveys_compensation_all_types', self.custom_calendar_sum('comp_any_facility_sat_count')),
            'comp_any_facility_sat_sum': ('std12e', 'surveys_compensation_all_types'),
            'comp_any_kept_informed_sat_avg': ('std12e', 'surveys_compensation_all_types',
                                               self.weighted_average('comp_any_kept_informed_sat_sum',
                                                                     'comp_any_kept_informed_sat_count')),
            'comp_any_kept_informed_sat_count': (
                'std12e', 'surveys_compensation_all_types', self.custom_calendar_sum('comp_any_kept_informed_sat_count')),
            'comp_any_kept_informed_sat_sum': ('std12e', 'surveys_compensation_all_types'),
            'comp_any_overall_sat_avg': ('std12e', 'surveys_compensation_all_types',
                                         self.weighted_average('comp_any_overall_sat_sum',
                                                               'comp_any_overall_sat_count')),
            'comp_any_overall_sat_count': (
                'std12e', 'surveys_compensation_all_types', self.custom_calendar_sum('comp_any_overall_sat_count')),
            'comp_any_overall_sat_sum': ('std12e', 'surveys_compensation_all_types'),
            'comp_any_request_service_sat_avg': ('std12e', 'surveys_compensation_all_types',
                                                 self.weighted_average('comp_any_request_service_sat_sum',
                                                                       'comp_any_request_service_sat_count')),
            'comp_any_request_service_sat_count': (
                'std12e', 'surveys_compensation_all_types', self.custom_calendar_sum('comp_any_request_service_sat_count')),
            'comp_any_request_service_sat_sum': ('std12e', 'surveys_compensation_all_types'),
            'comp_any_response_sat_avg': ('std12e', 'surveys_compensation_all_types',
                                          self.weighted_average('comp_any_response_sat_sum',
                                                                'comp_any_response_sat_count')),
            'comp_any_response_sat_count': (
                'std12e', 'surveys_compensation_all_types', self.custom_calendar_sum('comp_any_response_sat_count')),
            'comp_any_response_sat_sum': ('std12e', 'surveys_compensation_all_types'),
            'comp_battery_facility_sat_avg': ('std12e', 'surveys_compensation_battery',
                                              self.weighted_average('comp_battery_facility_sat_sum',
                                                                    'comp_battery_facility_sat_count')),
            'comp_battery_facility_sat_count': (
                'std12e', 'surveys_compensation_battery', self.custom_calendar_sum('comp_battery_facility_sat_count')),
            'comp_battery_facility_sat_sum': ('std12e', 'surveys_compensation_battery'),
            'comp_battery_kept_informed_sat_avg': ('std12e', 'surveys_compensation_battery',
                                                   self.weighted_average('comp_battery_kept_informed_sat_sum',
                                                                         'comp_battery_kept_informed_sat_count')),
            'comp_battery_kept_informed_sat_count': (
                'std12e', 'surveys_compensation_battery', self.custom_calendar_sum('comp_battery_kept_informed_sat_count')),
            'comp_battery_kept_informed_sat_sum': ('std12e', 'surveys_compensation_battery'),
            'comp_battery_overall_sat_avg': ('std12e', 'surveys_compensation_battery',
                                             self.weighted_average('comp_battery_overall_sat_sum',
                                                                   'comp_battery_overall_sat_count')),
            'comp_battery_overall_sat_count': (
                'std12e', 'surveys_compensation_battery', self.custom_calendar_sum('comp_battery_overall_sat_count')),
            'comp_battery_overall_sat_sum': ('std12e', 'surveys_compensation_battery'),
            'comp_battery_request_service_sat_avg': ('std12e', 'surveys_compensation_battery',
                                                     self.weighted_average('comp_battery_request_service_sat_sum',
                                                                           'comp_battery_request_service_sat_count')),
            'comp_battery_request_service_sat_count': ('std12e', 'surveys_compensation_battery',
                                                       self.custom_calendar_sum(
                                                           'comp_battery_request_service_sat_count')),
            'comp_battery_request_service_sat_sum': ('std12e', 'surveys_compensation_battery'),
            'comp_battery_response_sat_avg': ('std12e', 'surveys_compensation_battery',
                                              self.weighted_average('comp_battery_response_sat_sum',
                                                                    'comp_battery_response_sat_count')),
            'comp_battery_response_sat_count': (
                'std12e', 'surveys_compensation_battery', self.custom_calendar_sum('comp_battery_response_sat_count')),
            'comp_battery_response_sat_sum': ('std12e', 'surveys_compensation_battery'),
            'comp_not_tow_facility_sat_avg': ('std12e', 'surveys_compensation_light_service',
                                              self.weighted_average('comp_not_tow_facility_sat_sum',
                                                                    'comp_not_tow_facility_sat_count')),
            'comp_not_tow_facility_sat_count': ('std12e', 'surveys_compensation_light_service',
                                                self.custom_calendar_sum('comp_not_tow_facility_sat_count')),
            'comp_not_tow_facility_sat_sum': ('std12e', 'surveys_compensation_light_service'),
            'comp_not_tow_kept_informed_sat_avg': ('std12e', 'surveys_compensation_light_service',
                                                   self.weighted_average('comp_not_tow_kept_informed_sat_sum',
                                                                         'comp_not_tow_kept_informed_sat_count')),
            'comp_not_tow_kept_informed_sat_count': ('std12e', 'surveys_compensation_light_service',
                                                     self.custom_calendar_sum('comp_not_tow_kept_informed_sat_count')),
            'comp_not_tow_kept_informed_sat_sum': ('std12e', 'surveys_compensation_light_service'),
            'comp_not_tow_overall_sat_avg': ('std12e', 'surveys_compensation_light_service',
                                             self.weighted_average('comp_not_tow_overall_sat_sum',
                                                                   'comp_not_tow_overall_sat_count')),
            'comp_not_tow_overall_sat_count': (
                'std12e', 'surveys_compensation_light_service', self.custom_calendar_sum('comp_not_tow_overall_sat_count')),
            'comp_not_tow_overall_sat_sum': ('std12e', 'surveys_compensation_light_service'),
            'comp_not_tow_request_service_sat_avg': ('std12e', 'surveys_compensation_light_service',
                                                     self.weighted_average('comp_not_tow_request_service_sat_sum',
                                                                           'comp_not_tow_request_service_sat_count')),
            'comp_not_tow_request_service_sat_count': ('std12e', 'surveys_compensation_light_service',
                                                       self.custom_calendar_sum(
                                                           'comp_not_tow_request_service_sat_count')),
            'comp_not_tow_request_service_sat_sum': ('std12e', 'surveys_compensation_light_service'),
            'comp_not_tow_response_sat_avg': ('std12e', 'surveys_compensation_light_service',
                                              self.weighted_average('comp_not_tow_response_sat_sum',
                                                                    'comp_not_tow_response_sat_count')),
            'comp_not_tow_response_sat_count': ('std12e', 'surveys_compensation_light_service',
                                                self.custom_calendar_sum('comp_not_tow_response_sat_count')),
            'comp_not_tow_response_sat_sum': ('std12e', 'surveys_compensation_light_service'),
            'comp_tow_facility_sat_avg': ('std12e', 'surveys_compensation_tow',
                                          self.weighted_average('comp_tow_facility_sat_sum',
                                                                'comp_tow_facility_sat_count')),
            'comp_tow_facility_sat_count': (
                'std12e', 'surveys_compensation_tow', self.custom_calendar_sum('comp_tow_facility_sat_count')),
            'comp_tow_facility_sat_sum': ('std12e', 'surveys_compensation_tow'),
            'comp_tow_kept_informed_sat_avg': ('std12e', 'surveys_compensation_tow',
                                               self.weighted_average('comp_tow_kept_informed_sat_sum',
                                                                     'comp_tow_kept_informed_sat_count')),
            'comp_tow_kept_informed_sat_count': (
                'std12e', 'surveys_compensation_tow', self.custom_calendar_sum('comp_tow_kept_informed_sat_count')),
            'comp_tow_kept_informed_sat_sum': ('std12e', 'surveys_compensation_tow'),
            'comp_tow_overall_sat_avg': ('std12e', 'surveys_compensation_tow',
                                         self.weighted_average('comp_tow_overall_sat_sum',
                                                               'comp_tow_overall_sat_count')),
            'comp_tow_overall_sat_count': (
                'std12e', 'surveys_compensation_tow', self.custom_calendar_sum('comp_tow_overall_sat_count')),
            'comp_tow_overall_sat_sum': ('std12e', 'surveys_compensation_tow'),
            'comp_tow_request_service_sat_avg': ('std12e', 'surveys_compensation_tow',
                                                 self.weighted_average('comp_tow_request_service_sat_sum',
                                                                       'comp_tow_request_service_sat_count')),
            'comp_tow_request_service_sat_count': (
                'std12e', 'surveys_compensation_tow', self.custom_calendar_sum('comp_tow_request_service_sat_count')),
            'comp_tow_request_service_sat_sum': ('std12e', 'surveys_compensation_tow'),
            'comp_tow_response_sat_avg': ('std12e', 'surveys_compensation_tow',
                                          self.weighted_average('comp_tow_response_sat_sum',
                                                                'comp_tow_response_sat_count')),
            'comp_tow_response_sat_count': (
                'std12e', 'surveys_compensation_tow', self.custom_calendar_sum('comp_tow_response_sat_count')),
            'comp_tow_response_sat_sum': ('std12e', 'surveys_compensation_tow'),
        }

