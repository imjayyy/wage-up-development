
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from django.utils.timezone import make_aware
from rest_framework.response import Response
from accounts.models import UserActions, UserActionDetails, Organization
from django.db.models import *
from django.db.models.functions import Cast
from itertools import groupby
from datetime import datetime as dt

class UserTracking(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()
    serializer_class = None
    www_authenticate_realm = 'api'

    def post(self, request):
        self.data = request.data
        self.parameters = self.data.get('parameters')
        purpose = self.data.get('purpose', 'get_view_stats')
        self.user_emp = self.request.user.employee()
        self.user_org = self.user_emp.organization

        fac_type__position_type_lookup = {
            'Fleet-Manager': {'facility_type': 'FLEET'},
            'Station-Admin': {'facility_type__in': ['PSP', 'NON-PSP']},
            'Territory-Associate': {'facility_type__in': ['PSP', 'NON-PSP']},
        }

        self.user_fac_type_annot = fac_type__position_type_lookup.get(self.user_emp.position_type, {})
        self.filter_staff = self.data.get('filter_staff', True)

        if self.data.get('slug'):
            self.org = Organization.objects.get(slug=self.data.get('slug'))
            self.actions = UserActions.objects.filter(user__employee__organization =self.org)
        if self.user_org.type == 'Station-State':
            child_orgs = Organization.objects.filter(parent_id=self.user_org.id)
            child_orgs = child_orgs.filter(**self.user_fac_type_annot)
            print('child_orgs', child_orgs)
            self.actions = UserActions.objects.filter(user__employee__organization__in=child_orgs)
            self.org = self.user_org
        elif self.user_org.type not in ('Station-Business', 'Territory'):
            self.org = Organization.objects.get(id=1)
            self.actions = UserActions.objects
        else:
            self.actions = UserActions.objects.filter(user__employee__organization=self.user_org)

        if self.parameters.get('from'):
            self.actions = self.actions.filter(date__gte=self.parameters.get('from'))
        if self.parameters.get('to'):
            self.actions = self.actions.filter(date__lte=self.parameters.get('to'))

        if self.filter_staff:
            self.actions = self.actions.filter(user__is_staff=False).exclude(user__last_name__in=['Mazur', 'Gonier', 'Poole'])

        self.purpose_router = {
            'get_view_stats': self.get_view_stats
        }

        output = self.purpose_router[purpose]()
        return Response(output, status=status.HTTP_200_OK)

    def flatten_data(self, data, group=None):
        '''
        :param data:
        :param group:
        :return:
        [
            {...time_period ... data [ ... metrics ...]}
        ]
        '''

        if group is None and len(data.keys()) == 1:
            group = list(data.keys())[0]
            data = data[group]
            group = [group, "organization_id", self.org_lookup[group]['id'], self.org_lookup[group]['type']]

        time_periods = {}
        out = []
        for metric, time_period in data.items():
            for time, value in time_period.items():
                time_periods[time] = {} if time not in time_periods else time_periods[time]
                time_periods[time]['data'] = [] if 'data' not in time_periods[time] else time_periods[time]['data']
                time_periods[time]['data'].append({
                    "date": time,
                    "label": metric,
                    "value": value,
                    "value_type": "number",
                    "std_val": None
                })
        for time,data in time_periods.items():
            out.append({
                "time_type": self.parameters.get('time_type', 'D'),
                "sc_dt": time,
                "name": group[0],
                "type": group[2],
                "data": data['data'],
                "groupName": "TIMESERIES",
                "id": group[1:]
            })
        out = sorted(out, key=lambda x: x['sc_dt'])

        return out

    def child_timeseries(self, data):
        combined_group = [
                    self.org.name,
                    "organization_id",
                    self.org.id,
                    self.org.type
                ]
        combined_data = self.flatten_data(data['all'], combined_group)
        children = [{k:v} for k,v in data.items() if k != 'all' and k is not None]
        child_out = []
        for l in list(map(self.flatten_data, children)):
            child_out = child_out + l
        out = {
            'self': combined_data,
            'children': child_out,
        }
        return out

    def format_output_to_chart(self, data):
        chart_router = {
            'child_timeseries': self.child_timeseries
        }

        return chart_router[self.data.get('chart_type', 'child_timeseries')](data)

    def mapValue(self, val):

        mapper = {
            "New Login on App" : "My Toolkit Login",
            "New Login on Website": "WU Site Login",
            "New Visit to Scheduler": "Scheduler Login"
        }

        return mapper.get(val, val)


    def processBasicTableData(self, data, sorted_rows):
        default = {
            "title": "Data Table",
            "pdf": False,
            "xls": True,
            "search": True,
            "searchFields": [],
            "data": [],
            "metaData": {},
        }
        rows = []

        for row in data:
            r = {
                "rowLink": '#',
                "data": []
            }

            if len(sorted_rows) == 0:
                sorted_rows = list(row.keys())

            for k in sorted_rows:
                v = row[k]
                print(k)

                if isinstance(v, dt):
                    v = dt.strftime(v, '%Y-%m-%d')

                r['data'].append({
                    "label": k,
                    "value": self.mapValue(v) if k == 'metric' else v
                })



            rows.append(r)
        default['data'] = rows
        return default

    def get_view_stats(self):
        values = ['user_id', 'count', 'name', 'metric', 'dt', 'org', 'org_type', 'org_id', 'parent_org', 'parent_org_type', 'parent_org_id']
        grouping = ['user', 'display', 'dt']
        init_annotation = {"dt":Cast('date', DateField())}
        second_annotation = {
            "count": Count('dt', distinct=True),
            "name": F('user__employee__full_name'),
            "ne_driver_id": F('user__employee__raw_data_driver_id'),
            "metric": F('display'),
            "org": F('user__employee__organization__name'),
            "org_type": F('user__employee__organization__type'),
            "org_id": F('user__employee__organization_id'),
            "parent_org": F('user__employee__organization__parent__name'),
            "parent_org_type": F('user__employee__organization__parent__type'),
            "parent_org_id": F('user__employee__organization__parent_id'),
            "provider_type": F('user__employee__organization__facility_type')
        }
        order_by = []
        if self.data.get('raw_data'):
            second_annotation['last_login'] = F('user__last_login')
            values = ['name', 'metric', 'count', 'provider_type', 'last_login', 'org', 'ne_driver_id', 'parent_org']
            grouping = ['user', 'display']
            order_by = ['-last_login']

        sql_d = self.actions.annotate(**init_annotation)\
                     .values(*grouping)\
                    .annotate(**second_annotation)\

        print(sql_d.filter(user_id=49))
        sql_d = list(sql_d.values(*values).order_by(*order_by))

        # return sql_d
        if self.data.get('raw_data'):
            return self.processBasicTableData(sql_d, sorted_rows=['name', 'org', 'parent_org', 'provider_type', 'ne_driver_id', 'metric', 'count', 'last_login',])


        out = {}
        self.org_lookup = {}
        date_str_d = {
            "Day": "%Y-%m-%d",
            "Week": "%Y-%W-%w",
            "Month": "%Y-%m",

        }

        date_str_parse = {
                "Day": "%Y-%m-%d",
                "Week": "%Y-%W-1",
                "Month": "%Y-%m",

            }

        date_str = date_str_d[self.parameters.get('time_type_filter', 'Day')]
        date_str_parse = date_str_parse[self.parameters.get('time_type_filter', 'Day')]

        possible_dates = set()
        # print([l['dt'].strftime(date_str) for l in sql_d])
        [possible_dates.add(dt.strptime(l['dt'].strftime(date_str_parse), date_str).strftime('%Y-%m-%d')) for l in sql_d]
        print(possible_dates)

        possible_orgs = set()

        org_type = self.parameters.get('child_type', 'Station-Business')
        org_lookup = 'org' if org_type == 'Station-Business' else 'parent_org'

        [possible_orgs.add(l[org_lookup]) for l in sql_d]

        metrics = ["New Login on App", "New Login on Website", "New Visit to Scheduler", ]


        for org in possible_orgs:
            out[org] = {}
            for m in metrics:
                out[org][m] = {}
                for day in possible_dates:
                    out[org][m][day] = 0

        for m in metrics:
            out.setdefault('all', {})
            m_d_list = filter(lambda x: x['metric'] == m, sql_d)
            # print(sql_d)
            print("m", m)
            out['all'].setdefault(m, {})
            m_total = 0
            for org, org_list in groupby(m_d_list, key=lambda x: x[org_lookup]):
                print("org", org)
                ol = next(org_list)
                self.org_lookup[org] = {'id': ol[f'{org_lookup}_id'], 'type': ol[f'{org_lookup}_type']}
                out.setdefault(org, {})
                out[org].setdefault(m, {})
                # for d in sorted(list(possible_dates)):
                #     out['all'][m][d] = 0
                #     out[org][m][d] = 0

                for day, d_list in groupby(org_list, key=lambda x: x['dt'].strftime(date_str_parse)):
                    day_str = dt.strptime(day, date_str).strftime('%Y-%m-%d')
                    # out['all'][m].setdefault(day_str, 0)
                    # out[org][m].setdefault(day_str, 0)
                    d_list = list(d_list)
                    m_count = len(d_list)
                    # print(d_list, m_count, m_total)

                    # if m_count > 0:
                    #     print(d_list, day, m, org)
                    m_total += m_count
                    out['all'][m][day_str] = out['all'][m].get(day_str, 0) + m_count
                    out[org][m][day_str] = out[org][m].get(day_str, 0) + m_count


            out['all'][m]['ytd'] = m_total
        # print(out)
        # raise Exception("Stop")

        return self.format_output_to_chart(out)