import sys
sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from dashboard.models import *
from django.db.models import F, Case, When, Value, CharField, Max, Min, Value as V
from django.db.models.functions import Extract, Concat
import pytz
utc=pytz.UTC
from django.db.models.fields import DateField
from itertools import groupby
from django.db.models.functions import ExtractMonth, ExtractYear, ExtractWeek
from payments.models import *
from root.utilities import combine_dicts, flatten_list_of_lists, list_of_dicts_key_order, Round


class Usage(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()
    # serializer_class = None
    www_authenticate_realm = 'api'

    def product_usage_agg(self):
        from_date = self.parameters.get('from', (dt.date.today() - dt.timedelta(days=15)).strftime('%Y-%m-%d'))
        to_date = self.parameters.get('to', dt.date.today().strftime('%Y-%m-%d'))

        print(from_date, to_date)

        time_type = self.parameters.get('time_type', 'day')
        time_annotation = {
            'date_day': Cast('date', DateField()),
            'day_only': Cast(Cast('date', DateField()), CharField())
        }
        if time_type == 'month':
            time_annotation = {
                'date_day': Concat(ExtractYear('date'), ExtractMonth('date'), V('01'), output_field=CharField()),
                'day_only': Cast(Cast('date', DateField()), CharField())

            }
        if time_type == 'week':
            time_annotation = {
                'date_day': Concat(ExtractYear('date'), ExtractWeek('date'), output_field=CharField()),
                'day_only': Cast(Cast('date', DateField()), CharField())

            }

        grouping = self.parameters.get('grouping', 'user__employee__position_type')
        group_list = ['type', 'group', 'date_day']
        print('grouping is', grouping)

        filter = {"date__range": (from_date, to_date)}
        filter.update(self.parameters.get('filter', {}))

        if self.parameters.get('user_day', True):
            activity_count_params = {
                "activity_count": Count(Concat('user', 'day_only'), distinct=True)
            }

        else:
            activity_count_params = {
                "activity_count": Count('user', distinct=True)
            }


        activity = UserActions.objects \
            .filter(**filter)\
            .annotate(**time_annotation)\
            .annotate(group=F(grouping))\
            .values(*group_list).annotate(**activity_count_params).order_by('-date_day')\
            .values(*group_list + ['activity_count'])
        drivers = [a for a in activity if a['group'] == 'Driver' and a['type']=='App Login']
        print(activity[0])
        print(drivers)
        today = dt.datetime.today()

        def set_date(date):
            if type(date) == str:
                if time_type == 'week':
                    if len(date) == 5:
                        date = f"{date[:4]}-W0{date[4]}"
                    else:
                        date = f"{date[:4]}-W{date[4:]}"
                    if "W52" in date and today.year == int(date[:4]) and today.month != 12:
                        # print(date)
                        date = date.replace(str(today.year), str(today.year -1))
                    return dt.datetime.strptime(date + '-1', "%G-W%V-%u").strftime('%Y-%m-%d')
                else:
                    if len(date) == 7:
                        date = f"{date[:4]}-0{date[4]}-{date[5:]}"
                        # print(date)
                    else:
                        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                    return dt.datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
            else:
                return date.strftime('%Y-%m-%d')


        [a.update({'date_day': set_date(a['date_day'])}) for a in activity]
        combined = {}
        byGroup = {}
        byDate = {}

        for activityType, activityGroup in groupby(sorted(activity, key=lambda x: x['type']), lambda x: x['type']):
            total = 0
            activityGroup = sorted(list(activityGroup), key=lambda x: x['group'] if x['group'] is not None else 'None')
            byGroup[activityType] = {}
            byDate[activityType] = {}
            for grouping, activitySubGroup in groupby(activityGroup, lambda x: x['group'] if x['group'] is not None else 'None'):
                byGroupTotal = 0
                byDate[activityType][grouping] = {}
                for el in sorted(list(activitySubGroup), key=lambda x: x['date_day']):
                    byGroupTotal += el['activity_count']
                    total += el['activity_count']
                    if el['date_day'] not in byDate[activityType][grouping]: byDate[activityType][grouping][el['date_day']] = 0
                    byDate[activityType][grouping][el['date_day']] += el['activity_count']
                byGroup[activityType][grouping] = byGroupTotal
            combined[activityType] = total
        # print(byDate)
        # print(byGroup)
        # print(combined)
        return {
            "byDate": byDate,
            "byGroup": byGroup,
            "combined": combined
        }



        # for date, values in output.items():
        #     values['date'] = date
        #     out.append(values)
        #
        #
        # return out

    def post(self, request):
        self.user = request.user
        self.data = request.data
        self.purpose = self.data.get('purpose', 'product_usage_agg')
        self.parameters = self.data.get('parameters', {})

        self.purpose_router = {
            "product_usage_agg": self.product_usage_agg
        }

        output = self.purpose_router[self.purpose]()
        return Response(output, status=status.HTTP_200_OK)