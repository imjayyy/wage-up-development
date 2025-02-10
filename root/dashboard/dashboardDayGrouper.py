from django.db.models import Avg, Count, Sum, Min, Max
from .models import *
from django.db.models import FloatField, F, ExpressionWrapper, CharField, Value as V
from dateutil.relativedelta import relativedelta
from django.db.models.functions import Extract, Concat
import statistics

class DashboardDayGrouper:
    def __init__(self, **kwargs):
        self.dd = kwargs.get('dd')
        self.custom_time = kwargs.get('custom_time', self.dd.data.get('custom_time'))

    def format_chart(self):
        if self.dd.data.get('chart_type') == 'numberHighlights':
            output = []
            for m in self.dd.metrics:
                print(m)

                series = [
                            period.get(m) for
                            period in self.output
                        ]
                if len([s for s in series if s is not None]) == 0:
                    continue

                try:
                    mean = statistics.mean([s for s in series if s is not None])
                    std = statistics.stdev([s for s in series if s is not None])
                    variance = (series[0] - mean) / std
                except:
                    mean = [s for s in series if s is not None][0]
                    std = mean / 10
                    variance = 0
                output.append(
                    {
                        'series': series,
                        'labels': [period.get('sc_dt') for period in self.output],
                        'name': m,
                        'avg': mean,
                        'std': std,
                        'variance': variance,
                        'filters': self.dd.filters
                    }

                )
            self.output = output

        return self.output

    def run(self):
        annot = {}
        [annot.update(self.annotation_grouper(aggM, newM)) for newM, aggM in
         zip(self.dd.metrics, self.dd.original_metrics)]
        print(annot)
        filter = {'time_type': 'D'}
        if self.custom_time.get('from'):
            filter['sc_dt__gte'] = self.custom_time.get('from')
            filter['sc_dt__lte'] = self.custom_time.get('to')
            self.output = self.dd.queryset \
                .filter(**filter) \
                .aggregate(**annot)
            return self.output
        elif self.custom_time.get('until'):
            until = dt.datetime.strptime(self.custom_time.get('until'), '%Y-%m-%d')
            until = until if until <= dt.datetime.strptime(dt.datetime.strftime(self.dd.latest_date, '%Y-%m-%d'), '%Y-%m-%d') else self.dd.latest_date
            # print('until is', until, self.dd.latest_date, dt.datetime.strptime(dt.datetime.strftime(self.dd.latest_date, '%Y-%m-%d'), '%Y-%m-%d'))

            # if until.day < 4 and self.dd.data['time_type'][0]:
            #     until = until - relativedelta(days=until.day)

            # filter['sc_dt__gte'] = mtd - relativedelta(months=self.custom_time.get('count', 12))
            # filter['sc_dt__day__lte'] = mtd.day



            # generate ranges
            date_array = []
            time_period_defaults = {
                'MTD_SERIES': 'months',
                'LAST_MONTH_SERIES': 'months',
                'YTD_SERIES': 'years',
                'WEEKLY_SERIES': 'weeks',
                'DAILY_SERIES': 'days',

            }
            time_period = self.custom_time.get('period', time_period_defaults.get(self.dd.data['time_type'][0], 'months'))
            default_going_back = {
                'months': 13,
                'weeks': 15,
                'years': 3,
                'days': 20,
            }
            going_back_count = self.custom_time.get('count', default_going_back[time_period])
            going_back_count = range(going_back_count) if time_period != 'days' else range(0, going_back_count)

            if self.dd.data['time_type'][0] == 'LAST_MONTH_SERIES':
                until = until.replace(day=1)
                print('last month', until, going_back_count)

            for dates_back in going_back_count:
                end = until - relativedelta(**{time_period: dates_back})
                if time_period == 'years':
                    start = end.replace(day=1, month=1)
                elif self.dd.data['time_type'][0] == 'LAST_MONTH_SERIES':
                    start = until - relativedelta(**{time_period: dates_back+1})
                elif time_period == 'months':
                    start = end.replace(day=1)
                elif time_period == 'days':
                    start = end
                else:
                    start = end - relativedelta(weeks=1)
                filter['sc_dt__range'] = [start, end]

                # print(dates_back, start, end)

                ma = self.dd.queryset \
                    .filter(**filter) \
                    .aggregate(**annot)
                print(ma)
                ma['sc_dt'] = filter['sc_dt__range'][1]
                date_array.append(ma)

            self.output = date_array
            return self.output
            # .annotate(month_year=Concat(Extract('sc_dt', 'month'), V('-'), Extract('sc_dt', 'year'), output_field=CharField())) \

            # .values(*list(annot.keys()) + ['month_year'])\
            # .order_by('-month_year')

    def get_num_denom(self, metric):
        print('metric changes', metric)
        to_replace = 'avg' if 'avg' in metric else 'freq'
        denom, num = metric.replace(to_replace, 'count'), metric.replace(to_replace, 'sum')

        all_volume_denom_metrics = ['lost_call_freq', 'gained_call_freq', 'net_reroute_freq', 'declined_call_freq']

        if metric in all_volume_denom_metrics:
            return 'all_volume', metric.replace(to_replace, 'count')


        special_denoms = {
            'battery_opp_ata_avg': ('battery_ata_sum', 'battery_volume'),
            'batt_truk_avg': ('batt_truck_num', 'num_ops'),
            'test_rate_avg': ('matched_tests', 'num_ops'),
            'edocs_conv_avg': ('edocs_count', 'num_ops'),
            'edocs_avg': ('edocs_count', 'edocs_denom'),
            'vin_avg': ('vin_count', 'matched_tests'),
            'battery_ol_to_clr_avg': ('battery_ol_to_clr_sum', 'battery_volume')
        }

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

        if metric in special_denoms.keys():
            return special_denoms[metric][1], special_denoms[metric][0]

        if metric in volume_denom_metrics:
            return 'volume', metric.replace(to_replace, 'count')

        if getattr(DashboardAggregations, denom, False) and getattr(DashboardAggregations, num, False):
            return denom, num
        elif not getattr(DashboardAggregations, denom, False):
            return ExpressionWrapper(
                F(num) / F(metric), output_field=FloatField()), num
        elif not getattr(DashboardAggregations, num, False):
            return denom, ExpressionWrapper(
                F(denom) * F(metric), output_field=FloatField())

    def annotation_grouper(self, metric, newName=False):
        print(metric, newName)
        if not newName: newName = metric
        if 'freq' in metric or 'avg' in metric:
            denom, num = self.get_num_denom(metric)
            # print(denom, num)
            return {
                newName: ExpressionWrapper(Sum(num) / Sum(denom), output_field=FloatField())
            }
        if 'median' in metric:
            # this is an average of medians... not too good
            return {
                newName: Avg(metric)
                # newName: ExpressionWrapper(Avg(
                #     ExpressionWrapper(F(metric) * F('volume'), output_field=FloatField())
                # ) / F('volume'), output_field=FloatField())
            }
        else:
            return {
                newName: Sum(metric)
            }
