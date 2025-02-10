from django.db.models import F, Func
from django.db.models import Avg, Count, Sum, Min, Max
from django.db.models import Case, CharField, Value, When


class MetricAnnotationBuilder:

    def __init__(self, **kwargs):
        self.metric_list = kwargs.get('metric_list')

        self.router = {
            'ata_minus_pta_mean': self.ata_minus_pta_mean,
            'ata_mean': self.ata_mean,
            'pta_mean': self.pta_mean,
            'volume': self.volume,
            'battery_volume': self.battery_volume,
            'tow_volume': self.tow_volume,
            'early_count': self.early_count,
            'early_freq': self.early_freq,
            'late_freq': self.late_freq,

        }

        self.battery_tcds = []
        self.tow_tcds = []

    def get_annotations(self):
        return {metric: self.router[metric] for metric in self.metric_list}

    #### metrics below here

    def ata_minus_pta_mean(self):
        return Avg(F('ata') - F('pta'))

    def ata_mean(self):
        return Avg('ata')

    def pta_mean(self):
        return Avg('pta')

    def volume(self):
        return Count('id')

    def battery_volume(self):
        return Sum(Case(When(tcd__in=self.battery_tcds), then=1, default=0))

    def tow_volume(self):
        return Sum(Case(When(tcd__in=self.tow_tcds), then=1, default=0))

    def early_count(self):
        return Sum(Case(When(self.ata_minus_pta_mean() < -15), then=1, default=0))

    def late_count(self):
        return Sum(Case(When(self.ata_minus_pta_mean() > 15), then=1, default=0))

    def early_freq(self):
        return Avg(Case(When(self.ata_minus_pta_mean() < -15), then=1, default=0))

    def late_freq(self):
        return Avg(Case(When(self.ata_minus_pta_mean() > 15), then=1, default=0))