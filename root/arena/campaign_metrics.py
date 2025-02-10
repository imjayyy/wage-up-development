from django.db.models import Avg, Count, Sum, Min, Max
from dashboard.models import Std12EReduced
import json
from .models import *
from rest_framework.views import APIView
from dashboard.dashboardUtilities import generate_biz_rules_annotation

class CampaignMetricsHelper():

    def __init__(self, **kwargs):
        self.this_period_earnings = None
        self.arena = kwargs.get('arena')
        self.campaign = self.arena.campaign
        self.pay_period = self.arena.pay_period

        self.eligibility_router = {
            # 'OSAT_BASE': self.metric__OSAT_BASE
        }

        self.rewards_metric_router = {
            'total_earnings': self.metric__total_earnings,
            'this_period_earnings': self.metric__this_period_earnings,
            'raffle_tickets': self.metric__raffle_tickets,
            'variable_pay_per_survey_this_period_earnings': self.metric__variable_pay_per_survey_this_period_earnings, # TODO: this needs to be payment so far
            'variable_pay_per_survey_total_earnings': self.metric__variable_pay_per_survey_total_earnings, # TODO: this needs to be payment so far + already paid -- need to get current payment
            'variable_pay_per_survey_amount': self.metric__variable_pay_per_survey_amount
        }

        all_metrics = CampaignMetrics.objects

        non_template_metrics_qs = all_metrics.filter(templated=False)
        non_template_metrics ={}
        self.non_template_metrics_names = {}
        [non_template_metrics.update({m.key: getattr(self, f'metric__{m.key}')}) for m in non_template_metrics_qs]
        [self.non_template_metrics_names.update({m.key: m.name}) for m in non_template_metrics_qs]
        self.metric_router = {
            **non_template_metrics
        }

    def get_all_metric_data(self):
        metrics = self.campaign.metrics.all()
        self.metricData = []
        for m in metrics:
            md = self.get_metric_data(m)
            if type(md) == list:
                self.metricData = self.metricData + md
            else:
                self.metricData.append(md)
        return self.metricData

    def get_reward_metrics(self):
        '''
        :return: value for reward top, bottom reward metrics
        '''
        top_slot_value = self.rewards_metric_router[
            self.campaign.rewards_top_slot_metric.key]() if self.campaign.rewards_top_slot_metric is not None else "NA"
        bottom_slot_value = self.rewards_metric_router[
            self.campaign.rewards_bottom_slot_metric.key]() if self.campaign.rewards_bottom_slot_metric is not None else 'NA'

        return top_slot_value, bottom_slot_value

    def get_metric_data(self, metric, annotation_only=False):
        '''
            Metric functions should return
            {
                'metricTitle': string,
                'metricValue': (value),
                'metricType': string
            }
            or a list of ^ these values
        '''
        # print(metric.key)

        if metric.templated:
            # construct filter
            if metric.filter is None:
                final_filter = {}
            else:
                filter_d = json.loads(metric.filter)
                # print(metric.filter, filter_d)
                final_filter = {}

                for f in filter_d:
                    final_filter[f['filter']] = f['value']

            if metric.annotate is None:
                prefix = ""
            else:
                prefix = json.loads(metric.annotate)['prefix']

            return self.metric_template(
                prefix=prefix,
                fn_filter=final_filter,
                agg_type=metric.agg_type,
                agg_metric=metric.agg_metric
            )

        else:
            # print(metric)
            return self.metric_router[metric.key](annotation_only=annotation_only)

    def metric_template(self, *args, annotation_only=False, **kwargs):
        prefix = kwargs.get('prefix')
        fn_filter = kwargs.get('fn_filter')
        agg_type = kwargs.get('agg_type')
        agg_metric = kwargs.get('agg_metric')
        # print('filter', fn_filter, agg_metric)

        if annotation_only:
            # needs work to make more dynamic...
            return {
                'filter': fn_filter,
                'aggregation': {
                    'ts_count': Sum(agg_metric),
                    'base': Count(agg_metric),
                    'osat_avg': Avg(agg_metric)
                },
                'payment_field': 'ts_count'
            }

        if hasattr(self, f'{prefix}{agg_metric}_metrics'):
            return getattr(self, f'{prefix}{agg_metric}_metrics')[agg_type]
        else:
            self.get_basic_osat_metrics(surveys=self.arena.surveys.filter(**fn_filter),
                                        prefix=prefix)
            return getattr(self,f'{prefix}{agg_metric}_metrics')[agg_type]

    def get_basic_osat_metrics(self, surveys, prefix, sat_metric='overall_sat', with_rules=False):
        # surveys should already be filtered appropriately
        # if with_rules:
            # sat_vals = generate_biz_rules_annotation([sat_metric], surveys)
            # print(sat_vals)

        # else:
        sat_vals = surveys.aggregate(overall_sat_sum=Sum(sat_metric), overall_sat_count=Count(sat_metric), overall_sat_avg=Avg(sat_metric))
        self.__setattr__(f'{prefix}{sat_metric}_metrics', {
            'sum': {
                'metricTitle': f'{prefix} Totally Satisfied Survey Count',
                'metricValue': sat_vals[f'{sat_metric}_sum'] if sat_vals[f'{sat_metric}_sum'] is not None else 0,
                'metricType': 'int'
            },
            'count': {
                'metricTitle': f'{prefix} Total Survey Count',
                'metricValue': sat_vals[f'{sat_metric}_count'] if sat_vals[f'{sat_metric}_count'] is not None else 0,
                'metricType': 'int'
            },
            'avg': {
                'metricTitle': f'{prefix} Overall Satisfaction Average',
                'metricValue': sat_vals[f'{sat_metric}_avg'],
                'metricType': 'percent'
            },
            }
        )

    def metric__this_period_earnings(self, annotation_only=False):
        self.get_pending_payment()
        return self.pending_payment

    def metric__total_earnings(self, annotation_only=False):
        if self.pending_payment is None:
            self.get_pending_payment()
        if self.curr_payment_paid is None:
            self.get_curr_payment_paid()

        total_earnings = self.pending_payment + self.curr_payment_paid

        print("TOTAL EARNINGS CAP", self.pending_payment, self.curr_payment_paid, total_earnings, self.campaign.pay_cap)
        if total_earnings > self.campaign.pay_cap:
            total_earnings = self.campaign.pay_cap

        return total_earnings

    def metric__raffle_tickets(self, annotation_only=False):
        is_eligible = all([self.eligibility_router[metric]()['metricValue'] >= threshold for metric, threshold in
                           self.payment_converter['ELIGIBILITY'].items()])

        if not is_eligible:
            return "Not Eligible"

        raffle_tier = 'Not Eligible'
        # print(self.metricData)
        value = sum(
            [list(filter(lambda x: x['metricTitle'].lower().strip() == metric, self.metricData))[0]['metricValue'] * factor
             for metric, factor in self.payment_converter['METRICS'].items()])

        for tier, threshold in self.payment_converter['THRESHOLDS'].items():
            # print(value, threshold)
            if value * 100 >= threshold:
                raffle_tier = tier

        raffle_tier = f'{raffle_tier}'
        return raffle_tier

    def metric__variable_pay_per_survey_amount(self, annotation_only=False, osat_group=None, osat_m=None, value_only=False):
        if osat_group is None and osat_m is None and osat_m is None:
            if hasattr(self, 'overall_sat_metrics'):
                osat_m = getattr(self, 'overall_sat_metrics')
            else:
                self.get_basic_osat_metrics(surveys=self.arena.surveys,
                                            prefix="")
                osat_m = getattr(self, 'overall_sat_metrics')
            total_overall_sat, total_overall_sat_percent = osat_m['sum'], osat_m['avg']
        elif osat_group is None:
            # print('osat_m in variable_pay_per_survey_amount', osat_m)
            total_overall_sat = osat_m['base_overall_sat_sum']
            total_overall_sat_percent = osat_m['base_overall_sat_avg']
        else:
            out = []
            for d in osat_group:
                out.append({'emp_driver_id': d['emp_driver_id'],
                            'variable_pay_per_survey_amount': self.metric__variable_pay_per_survey_amount(osat_m=d, value_only=True)})
            return out


        # print('After getting metric__total_sat()')
        if self.campaign.payout_converter:
            tiers_load = json.loads(self.campaign.payout_converter)
            tiers = tiers_load['tiers']
            pay_amount = 0.0
            for t in tiers:
                try:
                    if value_only:
                        if t['min_percentage'] <= total_overall_sat_percent * 100 and t[
                            'max_percentage'] >= \
                                total_overall_sat_percent * 100:
                            pay_amount = t['payout']
                            break
                    else:
                        if t['min_percentage'] <= total_overall_sat_percent['metricValue']*100 and t['max_percentage'] >= \
                                total_overall_sat_percent['metricValue']*100:
                            pay_amount = t['payout']
                            break
                except:
                    continue
            if value_only:
                return f'${pay_amount:.2f}'
            return {
                  "metricTitle": self.non_template_metrics_names['variable_pay_per_survey_amount'],
                  "metricValue": f'${pay_amount:.2f}',
                  "metricType": "number"
                    }
        else:
            if value_only:
                return 0
            return {
                  "metricTitle": self.non_template_metrics_names['variable_pay_per_survey_amount'],
                  "metricValue": 0,
                  "metricType": "number"
                    }

    def metric__variable_pay_per_survey_total_earnings(self, annotation_only=False, osat_group=None, osat_m=None):
        if osat_group is None:
            if self.arena.curr_payment_paid is None and osat_m is None:
                self.arena.get_curr_payment_paid()
            elif self.arena.curr_payment_paid is None:
                self.arena.get_curr_payment_paid(osat_m['emp_driver_id'])
            elif osat_m is not None and self.arena.curr_payment_paid is not None:
                if self.arena.driver.id != osat_m['emp_driver_id']:
                    self.arena.get_curr_payment_paid(osat_m['emp_driver_id'])

            if self.this_period_earnings is None and osat_m is None:
                self.metric__variable_pay_per_survey_this_period_earnings()
            elif self.this_period_earnings is None:
                self.metric__variable_pay_per_survey_this_period_earnings(osat_m=osat_m, for_site=True)
            elif self.this_period_earnings is not None and osat_m is not None:
                self.metric__variable_pay_per_survey_this_period_earnings(osat_m=osat_m, for_site=True)
                # print(self.this_period_earnings, self.arena.curr_payment_paid)
            return f'${self.this_period_earnings + self.arena.curr_payment_paid:.2f}'
        else:
            # print('has osat group line 257', osat_group)
            out = []
            for d in osat_group:
                # print(d)
                out.append({'emp_driver_id': d['emp_driver_id'], 'variable_pay_per_survey_total_earnings': self.metric__variable_pay_per_survey_total_earnings(osat_m=d)})
            return out

    def metric__variable_pay_per_survey_this_period_earnings(self, annotation_only=False, osat_group=None, osat_m=None, for_site=False):
        total_earnings = 0
        if osat_group is None and osat_m is None:
            if hasattr(self, 'overall_sat_metrics'):
                osat_m = getattr(self, 'overall_sat_metrics')
            else:
                self.get_basic_osat_metrics(surveys=self.arena.surveys,
                                            prefix="")
                osat_m = getattr(self, 'overall_sat_metrics')

            # print(osat_m)
        elif osat_group is None:
            pass
        else:
            out = []
            for d in osat_group:
                out.append({'emp_driver_id': d['emp_driver_id'], 'variable_pay_per_survey_this_period_earnings': self.metric__variable_pay_per_survey_this_period_earnings(osat_m=d, for_site=True)})
            return out

        try:
            tiers_load = json.loads(self.campaign.payout_converter)
            tiers = tiers_load['tiers']
            curr_payout = 0.0
            for t in tiers:
                if for_site:
                    if t['min_percentage'] <= round(osat_m['base_overall_sat_avg'] * 100, 2) and t[
                        'max_percentage'] >= osat_m['base_overall_sat_avg'] * 100:
                        curr_payout = t['payout']
                        break
                else:
                    if t['min_percentage'] <= round(osat_m['avg']['metricValue']*100, 2) and t[
                        'max_percentage'] >= osat_m['avg']['metricValue']*100:
                        curr_payout = t['payout']
                        break
            if for_site:
                total_earnings += osat_m['base_overall_sat_sum'] * curr_payout
            else:
                total_earnings += osat_m['sum']['metricValue'] * curr_payout
        except:
            print('No payout converter found')
            total_earnings = 0.0
        self.this_period_earnings = total_earnings
        return f'${total_earnings:.2f}'

# def metric__totally_satisfied_surveys_count(self, annotation_only=False):
#     # weekday reference: 1 (Sunday) to 7 (Saturday).
#
#     if annotation_only:
#         return {
#             'filter': {
#             },
#             'aggregation': {
#                 'ts_count': Sum('overall_sat'),
#                 'base': Count('overall_sat'),
#                 'osat_avg': Avg('overall_sat')
#             },
#             'payment_field': 'ts_count'
#         }
#
#     if hasattr(self, self._osat_metrics):
#         return self._osat_metrics['sum']
#     else:
#         self.get_basic_osat_metrics(surveys=self.surveys,
#                                     prefix='')
#         return self._osat_metrics['sum']
#
#
# def metric__totally_satisfied_surveys_weekdays(self, annotation_only=False):
#     # weekday reference: 1 (Sunday) to 7 (Saturday).
#
#     if annotation_only:
#         return {
#             'filter': {
#                 'sc_dt_surveys__week_day__in': [2, 3, 4, 5, 6]
#             },
#             'aggregation': {
#                 'ts_count': Sum('overall_sat'),
#                 'base': Count('overall_sat'),
#                 'osat_avg': Avg('overall_sat')
#             },
#             'payment_field': 'ts_count'
#         }
#
#     return self.get_basic_osat_metrics(surveys=self.surveys.filter(sc_dt_surveys__week_day__in=[2, 3, 4, 5, 6]),
#                                        prefix='Weekday')
#
#
# def metric__totally_satisfied_surveys_weekends(self, annotation_only=False):
#     if annotation_only:
#         return {
#             'filter': {
#                 'sc_dt_surveys__week_day__in': [1, 7]
#             },
#             'aggregation': {
#                 'ts_count': Sum('overall_sat'),
#                 'base': Count('overall_sat'),
#                 'osat_avg': Avg('overall_sat')
#             },
#             'payment_field': 'ts_count'
#         }
#     return self.get_basic_osat_metrics(surveys=self.surveys.filter(sc_dt_surveys__week_day__in=[1, 7]),
#                                        prefix='Weekend')
#
#
# def metric__total_sat(self, annotation_only=False):
#     out = self.get_basic_osat_metrics(surveys=self.surveys,
#                                       prefix='',
#                                       with_rules=True)
#     return [out[1], out[2]]
#
#
# def metric__osat_base(self, annotation_only=False):
#     return self.get_basic_osat_metrics(surveys=self.surveys,
#                                        prefix='',
#                                        with_rules=True)[1]
#
#
# def metric__driver_overall_sat(self, annotation_only=False):
#     metric = Std12EReduced.objects.filter(driver_id='129127', sc_dt_surveys__range=['2021-02-01', '2021-03-31']) \
#         .aggregate(average_total_sat=Avg('q24'))
#     return 'not built'