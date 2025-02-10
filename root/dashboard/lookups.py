from django.db.models import Case, CharField, Value, When, Q

from .models import *

from django.db.models import FloatField, F, DecimalField, IntegerField, BooleanField, Func

class dashboardLookups():
    def __init__(self):
        self.time_type_conversions = {
            'Yesterday': 'D',
            'D': 'D',
            'M': 'M',
            'Month': "M",
            'Day': "D",
            'Hour': "H",
            "W-MON": "W-MON",
            'Week': "W-MON",
            'Prev_week': "W-Mon",
            'MTD_Last_Year': 'mtd_last_year',
            'YTD': 'ytd',
            'ytd': 'ytd',
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
            'TIMESERIES': 'M'
        }
        self.eligible_months = {
            'std12e': ['Month', 'Week', 'Day', 'Incentive', 'Hour_of_Day', 'Day_and_Hour_of_Week', 'Day_of_Week'],
            'ops': ['Month', 'Day', 'Hour', 'Week', 'Hour_of_Day', 'Day_and_Hour_of_Week', 'Day_of_Week']
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

        self.useful_annotations = {
            'outc1': Case(When(outc1=0, then=Value('Unknown')),
                          When(outc1=1, then=Value('Totally Satisfied')),
                          When(outc1=2, then=Value('Satisfied')),
                          When(outc1=3, then=Value('Neither Satisfied nor Disatisfied')),
                          When(outc1=4, then=Value('Dissatisfied')),
                          When(outc1=5, then=Value('Totally Dissatisfied')),
                          When(outc1=6, then=Value('Left Blank')),
                          default=Value('Unknown'),
                          output_field=CharField()
                          ),
            'driver10': Case(When(driver10=0, then=Value('Unknown')),
                             When(driver10=1, then=Value('Totally Satisfied')),
                             When(driver10=2, then=Value('Satisfied')),
                             When(driver10=3, then=Value('Neither Satisfied nor Disatisfied')),
                             When(driver10=4, then=Value('Dissatisfied')),
                             When(driver10=5, then=Value('Totally Dissatisfied')),
                             When(driver10=6, then=Value('Left Blank')),
                             default=Value('Unknown'),
                             output_field=CharField()
                             ),
            'q24': Case(When(q24=0, then=Value('Unknown')),
                        When(q24=1, then=Value('Totally Satisfied')),
                        When(q24=2, then=Value('Satisfied')),
                        When(q24=3, then=Value('Neither Satisfied nor Disatisfied')),
                        When(q24=4, then=Value('Dissatisfied')),
                        When(q24=5, then=Value('Totally Dissatisfied')),
                        When(q24=6, then=Value('Left Blank')),
                        default=Value('Unknown'),
                        output_field=CharField()
                        ),
            'q26': Case(When(q26=0, then=Value('Unknown')),
                        When(q26=1, then=Value('Totally Satisfied')),
                        When(q26=2, then=Value('Satisfied')),
                        When(q26=3, then=Value('Neither Satisfied nor Disatisfied')),
                        When(q26=4, then=Value('Dissatisfied')),
                        When(q26=5, then=Value('Totally Dissatisfied')),
                        When(q26=6, then=Value('Left Blank')),
                        default=Value('Unknown'),
                        output_field=CharField()
                        ),
            'driver5': Case(When(driver5=0, then=Value('Unknown')),
                            When(driver5=1, then=Value('Totally Satisfied')),
                            When(driver5=2, then=Value('Satisfied')),
                            When(driver5=3, then=Value('Neither Satisfied nor Disatisfied')),
                            When(driver5=4, then=Value('Dissatisfied')),
                            When(driver5=5, then=Value('Totally Dissatisfied')),
                            When(driver5=6, then=Value('Left Blank')),
                            default=Value('Unknown'),
                            output_field=CharField()
                            ),
            'appeals_eligible': Case(When(
                ~Q(sc_svc_prov_type='F') & ~Q(overall_sat=1) & Q(q30__isnull=False) & Q(reroute=0) & Q(
                    reroute_360=0) & Q(first_spot_delay=0) &
                Q(remove=0) & Q(appeals_request__isnull=True) & Q(sc_dt_surveys__gte='2020-12-01') & Q(duplicate=0),
                then=True), default=False, output_field=BooleanField()),




            'appeals_eligible_info': Case(When(Q(sc_svc_prov_type='F'), then=Value('Is Fleet')),
                                              When(Q(overall_sat=1), then=Value('Overall Sat is TS')),
                                              When(Q(q30__isnull=True), then=Value('No Comment')),
                                              When(Q(reroute=1), then=Value('Is a Reroute')),
                                              When(Q(reroute_360=1), then=Value('Is a Reroute')),
                                              When(Q(remove=1), then=Value('December Manual Appeal Removal')),
                                              When(Q(first_spot_delay=1),
                                                   then=Value('Is already removed by manual appeal')),
                                              When(Q(appeals_request__isnull=False),
                                                   then=Value('Appeal already submitted')),
                                              When(Q(sc_dt_surveys__lt='2020-12-01'), then=Value('Survey is too old')),
                                              When(Q(duplicate=1), then=Value('Is Duplicate')),
                                              default=Value('Is eligible'),
                                              output_field=CharField()
                                              ),


            'appeals_status': F('appeals_request__request_data__status'),

            'survey__outc1': Case(When(survey__outc1=0, then=Value('Unknown')),
                          When(survey__outc1=1, then=Value('Totally Satisfied')),
                          When(survey__outc1=2, then=Value('Satisfied')),
                          When(survey__outc1=3, then=Value('Neither Satisfied nor Disatisfied')),
                          When(survey__outc1=4, then=Value('Dissatisfied')),
                          When(survey__outc1=5, then=Value('Totally Dissatisfied')),
                          When(survey__outc1=6, then=Value('Left Blank')),
                          default=Value('Unknown'),
                          output_field=CharField()
                          ),
            'survey__driver10': Case(When(survey__driver10=0, then=Value('Unknown')),
                             When(survey__driver10=1, then=Value('Totally Satisfied')),
                             When(survey__driver10=2, then=Value('Satisfied')),
                             When(survey__driver10=3, then=Value('Neither Satisfied nor Disatisfied')),
                             When(survey__driver10=4, then=Value('Dissatisfied')),
                             When(survey__driver10=5, then=Value('Totally Dissatisfied')),
                             When(survey__driver10=6, then=Value('Left Blank')),
                             default=Value('Unknown'),
                             output_field=CharField()
                             ),
            'survey__q24': Case(When(survey__q24=0, then=Value('Unknown')),
                        When(survey__q24=1, then=Value('Totally Satisfied')),
                        When(survey__q24=2, then=Value('Satisfied')),
                        When(survey__q24=3, then=Value('Neither Satisfied nor Disatisfied')),
                        When(survey__q24=4, then=Value('Dissatisfied')),
                        When(survey__q24=5, then=Value('Totally Dissatisfied')),
                        When(survey__q24=6, then=Value('Left Blank')),
                        default=Value('Unknown'),
                        output_field=CharField()
                        ),
            'survey__q26': Case(When(survey__q26=0, then=Value('Unknown')),
                        When(survey__q26=1, then=Value('Totally Satisfied')),
                        When(survey__q26=2, then=Value('Satisfied')),
                        When(survey__q26=3, then=Value('Neither Satisfied nor Disatisfied')),
                        When(survey__q26=4, then=Value('Dissatisfied')),
                        When(survey__q26=5, then=Value('Totally Dissatisfied')),
                        When(survey__q26=6, then=Value('Left Blank')),
                        default=Value('Unknown'),
                        output_field=CharField()
                        ),
            'survey__driver5': Case(When(survey__driver5=0, then=Value('Unknown')),
                            When(survey__driver5=1, then=Value('Totally Satisfied')),
                            When(survey__driver5=2, then=Value('Satisfied')),
                            When(survey__driver5=3, then=Value('Neither Satisfied nor Disatisfied')),
                            When(survey__driver5=4, then=Value('Dissatisfied')),
                            When(survey__driver5=5, then=Value('Totally Dissatisfied')),
                            When(survey__driver5=6, then=Value('Left Blank')),
                            default=Value('Unknown'),
                            output_field=CharField()
                            ),
            'survey__response_sat': Case(When(survey__response_sat=0, then=Value('Unknown')),
                                 When(survey__response_sat=1, then=Value('Totally Satisfied')),
                                 When(survey__response_sat=2, then=Value('Satisfied')),
                                 When(survey__response_sat=3, then=Value('Neither Satisfied nor Disatisfied')),
                                 When(survey__response_sat=4, then=Value('Dissatisfied')),
                                 When(survey__response_sat=5, then=Value('Totally Dissatisfied')),
                                 When(survey__response_sat=6, then=Value('Left Blank')),
                                 default=Value('Unknown'),
                                 output_field=CharField()
                                 ),
            'survey__appeals_eligible': Case(When(
                ~Q(survey__sc_svc_prov_type='F') & ~Q(survey__overall_sat=1) & Q(survey__q30__isnull=False) & Q(survey__reroute=0) & Q(
                    survey__reroute_360=0) & Q(survey__first_spot_delay=0) &
                Q(survey__remove=0) & Q(survey__appeals_request__isnull=True) & Q(survey__sc_dt_surveys__gte='2020-12-01') & Q(survey__duplicate=0),
                then=True), default=False, output_field=BooleanField()),

            'survey__appeals_eligible_info': Case(When(Q(survey__sc_svc_prov_type='F'), then=Value('Is Fleet')),
                                          When(Q(survey__overall_sat=1), then=Value('Overall Sat is TS')),
                                          When(Q(survey__q30__isnull=True), then=Value('No Comment')),
                                          When(Q(survey__reroute=1), then=Value('Is a Reroute')),
                                          When(Q(survey__reroute_360=1), then=Value('Is a Reroute')),
                                          When(Q(survey__remove=1), then=Value('December Manual Appeal Removal')),
                                          When(Q(survey__first_spot_delay=1),
                                               then=Value('Is already removed by manual appeal')),
                                          When(Q(survey__appeals_request__isnull=False),
                                               then=Value('Appeal already submitted')),
                                          When(Q(survey__sc_dt_surveys__lt='2020-12-01'), then=Value('Survey is too old')),
                                          When(Q(survey__duplicate=1), then=Value('Is Duplicate')),
                                          default=Value('Is eligible'),
                                          output_field=CharField()
                                          ),

            'survey__appeals_status': F('survey__appeals_request__request_data__status'),
            'dispatch_communicated': Case(When(dispatch_communicated=0, then=Value('NO')),
                                          When(dispatch_communicated=1, then=Value('YES')),
                                          default=Value('UNKNOWN'),
                                          output_field=CharField()
                                          ),
            'tcd': Case(When(tcd__startswith='3', then=Value('Battery')),
                        When(tcd__startswith='6', then=Value('Tow')),
                        default=Value('Light Service'),
                        output_field=CharField()
                        ),
            'first_spot_fac': F('fst_shop'),
            'check_id_compliant': Case(When(check_id_compliant=0, then=Value('No')),
                                       When(check_id_compliant=1, then=Value('Yes')),
                                       default=Value('No'),
                                       output_field=CharField()),

            'biz_reroute_exclude': Case(When(Q(reroute=True) & Q(overall_sat=0)), then=True, default=False, output_field=BooleanField())


        }

        self.value_type_from_lookup = {
            'battery_ops': 'int',
            'battery_ata_avg': 'float',
            'edocs_install_count': 'int',
            'battery_ol_to_clr_avg': 'float',

        }