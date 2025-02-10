from django.db.models import Avg, Count, Sum, Min, Max
from .models import *
from django.db.models import FloatField, F, ExpressionWrapper, CharField, Value as V
from dateutil.relativedelta import relativedelta
from django.db.models.functions import Extract, Concat, ExtractHour, ExtractMonth, ExtractYear
from django.db.models.functions import Round
import statistics
from django.db.models import Case, CharField, Value, When, IntegerField
from django.db.models import Q


class DashboardShiftGrouper:
    def __init__(self, **kwargs):
        self.dd = kwargs.get('dd')
        self.kwargs = kwargs

    def run(self):
        print('getting shifts')
        self.data = self.dd.queryset.filter(time_type='H')
        annot = {}
        [annot.update(self.annotation_grouper(aggM, newM)) for newM, aggM in
         zip(self.dd.metrics, self.dd.original_metrics)]
        print(annot)
        print(self.dd.data)
        date = Concat(ExtractYear('sc_dt'), V('-'), ExtractMonth('sc_dt'), output_field=CharField()) if 'Month' in self.dd.data.get('time_type') else F('sc_dt__date')
        self_org = self.data.annotate(hour=ExtractHour('sc_dt'), date=date, month=ExtractMonth('sc_dt__date')).annotate(shift=Case(
            When(Q(hour__isnull=True), then=0),
            When(Q(hour__lte=8), then=1),
            When(Q(hour__gt=16), then=3),
            default=2, output_field=CharField()
        )).values('shift', 'organization__name', 'date').annotate(**annot).order_by()

        def clean_val(k,v):
            if k != 'date':
                return self.dd.format_value(v)
            elif type(v) == dt.date or type(v) == dt.datetime:
                return self.dd.format_value(v)
            else:
                v = v.split('-')
                v = f"{v[0]}-{v[1].zfill(2)}"
                print(v)
                return dt.datetime.strptime(v, '%Y-%m').strftime('%b %Y')



        self_org = [{k:clean_val(k,v) for k,v in x.items()} for x in self_org]

        return self_org

    def get_num_denom(self, metric):
        print('metric changes', metric)
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
                newName: Round(ExpressionWrapper(Sum(num) / Sum(denom)*1000, output_field=FloatField()))/10
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