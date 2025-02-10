from django.db import models
import sys
import random
import datetime as dt
from django.db.models import Sum, Count
from django.db.models.functions import Cast
sys.path.insert(0, 'root')

from accounts.models import *
from onboarding.models import Documentation

from observations import models as observation_models

# this is for searching comments

class MetricGoals(models.Model):
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name='goals_organization')
    metric = models.ForeignKey(Documentation, null=True, blank=True, on_delete=models.SET_NULL, related_name='goals_documentation')
    green = models.FloatField(null=True, blank=True)
    yellow = models.FloatField(null=True, blank=True)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='goals_user')
    facility_type = models.CharField(max_length=10, choices = (('PSP', 'PSP'), ('NON-PSP', 'PSP'), ('Fleet', 'PSP')), null=True, blank=True)
    highGood = models.BooleanField(default=True)

    class Meta:
        index_together = (
            ('employee', 'organization', 'metric'),
        )


# we update this table with Metrics Processing to know what time period qualifies for a certain metric

class TimeMetricPeriods(models.Model):
    discrete_time_category = models.CharField(max_length=255, db_column="DISCRETE_TIME_CATEGORY", blank=True, null=True)
    sc_dt = models.DateTimeField(db_column='SC_DT', blank=True, null=True)
    metric_type = models.CharField(max_length=255, db_column="METRIC_TYPE", blank=True, null=True)


# this is a view to set the status of etl

class EtlStatus(models.Model):
    datetime = models.DateTimeField()
    today = models.BooleanField()
    progress = models.CharField(max_length=255, blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'etl_status'

# this is a raw records op table that we keep in django for the past 90 days...
# the primary purpose is to show things like maps, or to show recent call by call data

# ops ra


class RawOpsAggSource(models.Model):
    sc_dt = models.DateField(db_column='SC_DT')  # Field name made lowercase.
    sc_id = models.IntegerField(db_column='SC_ID')  # Field name made lowercase.
    re_tm = models.DateTimeField(db_column='RE_TM', blank=True, null=True)  # Field name made lowercase.
    org_svc_facl_id = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_ID', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_agg_svc_facl')  # Field name made lowercase.
    org_business_id = models.ForeignKey(Organization, db_column='ORG_BUSINESS_ID', blank=True,on_delete=models.SET_NULL, null=True, related_name='raw_ops_agg_business_id')  # Field name made lowercase.
    org_facility_state = models.ForeignKey(Organization,db_column='ORG_FACILITY_STATE', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_agg_facility_state')  # Field name made lowercase.
    org_svc_facility_rep = models.ForeignKey(Organization,db_column='ORG_SVC_FACL_REP', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_agg_facility_rep')  # Field name made lowercase.
    emp_driver_id = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_agg_emp_driver_id')  # Field name made lowercase.
    tcd = models.CharField(db_column='TCD', max_length=20, blank=True, null=True)  # Field name made lowercase.
    shift = models.CharField(db_column='SHIFT', max_length=20, blank=True, null=True)  # Field name made lowercase.
    ata = models.FloatField(db_column='ATA', null=True, blank=True)
    pta = models.FloatField(db_column='PTA', null=True, blank=True)
    reroute = models.BooleanField(null=True)
    overall_sat = models.BooleanField(null=True)
    facility_sat = models.BooleanField(null=True)
    kept_informed_sat = models.BooleanField(null=True)
    request_svc_sat = models.BooleanField(null=True, db_column='REQUEST_SERVICE_SAT')
    response_sat = models.BooleanField(null=True)
    date_updated_surveys = models.DateTimeField()
    class Meta:
        managed = False
        db_table = 'tcd_calcs_stored'
class RawOps(models.Model):
    sc_dt = models.DateField(db_column='SC_DT')  # Field name made lowercase.
    sc_id = models.IntegerField(db_column='SC_ID')  # Field name made lowercase.
    comm_ctr_id = models.CharField(db_column='COMM_CTR_ID', max_length=10)  # Field name made lowercase.
    driver_id = models.CharField(db_column='DRIVER_ID', max_length=120, blank=True, null=True)  # Field name made lowercase.
    driver_name = models.CharField(db_column='DRIVER_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    svc_facl_st_cd = models.CharField(db_column='SVC_FACL_ST_CD', max_length=20, blank=True, null=True)  # Field name made lowercase.
    hub = models.CharField(db_column='HUB', max_length=20, blank=True, null=True)  # Field name made lowercase.
    queue = models.CharField(db_column='QUEUE', max_length=10, blank=True, null=True)  # Field name made lowercase.
    svc_facl_id = models.CharField(db_column='SVC_FACL_ID', max_length=10, blank=True, null=True)  # Field name made lowercase.
    svc_facl_nm = models.CharField(db_column='SVC_FACL_NM', max_length=255, blank=True, null=True)  # Field name made lowercase.
    re_tm = models.DateTimeField(db_column='RE_TM', blank=True, null=True)  # Field name made lowercase.
    first_tow_status_time = models.DateTimeField(db_column='FIRST_TOW_STATUS_TIME', blank=True, null=True)  # Field name made lowercase.
    promised_time = models.DateTimeField(db_column='PROMISED_TIME', blank=True, null=True)  # Field name made lowercase.
    fst_ol_time = models.DateTimeField(db_column='FST_OL_TIME', blank=True, null=True)  # Field name made lowercase.
    clear_time = models.DateTimeField(db_column='CLEAR_TIME', blank=True, null=True)  # Field name made lowercase.
    associate_count = models.IntegerField(db_column='ASSOCIATE_COUNT', blank=True, null=True)  # Field name made lowercase.
    associate_id = models.CharField(db_column='ASSOCIATE_ID', max_length=10, blank=True, null=True)  # Field name made lowercase.
    base_cost = models.DecimalField(db_column='BASE_COST', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    battery_truck = models.IntegerField(db_column='BATTERY_TRUCK', blank=True, null=True)  # Field name made lowercase.
    battery_test = models.IntegerField(db_column='BATTERY_TEST', blank=True, null=True)  # Field name made lowercase.
    battery_test_failed = models.IntegerField(db_column='BATTERY_TEST_FAILED', blank=True, null=True)  # Field name made lowercase.
    battery_test_on_battery_call = models.IntegerField(db_column='BATTERY_TEST_ON_BATTERY_CALL', blank=True, null=True)  # Field name made lowercase.
    battery_replaced_on_failed_batt_call = models.IntegerField(db_column='BATTERY_REPLACED_ON_FAILED_BATT_CALL', blank=True, null=True)  # Field name made lowercase.
    bl_lat = models.FloatField(db_column='BL_LAT', blank=True, null=True)  # Field name made lowercase.
    bl_long = models.FloatField(db_column='BL_LONG', blank=True, null=True)  # Field name made lowercase.
    bl_state_cd = models.CharField(db_column='BL_STATE_CD', max_length=20, blank=True, null=True)  # Field name made lowercase.
    facility_zip = models.CharField(db_column='FACILITY_ZIP', max_length=20, blank=True, null=True)  # Field name made lowercase.
    call_center = models.CharField(db_column='CALL_CENTER', max_length=120, blank=True, null=True)  # Field name made lowercase.
    call_center_operator = models.CharField(db_column='CALL_CENTER_OPERATOR', max_length=255, blank=True, null=True)  # Field name made lowercase.
    call_cost = models.DecimalField(db_column='CALL_COST', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    check_id_api_response = models.TextField(db_column='CHECK_ID_API_RESPONSE', blank=True, null=True)  # Field name made lowercase.
    check_id_check_fail = models.IntegerField(db_column='CHECK_ID_CHECK_FAIL', blank=True, null=True)  # Field name made lowercase.
    check_id_compliant = models.IntegerField(db_column='CHECK_ID_COMPLIANT', blank=True, null=True)  # Field name made lowercase.
    check_id_d3_fname = models.CharField(db_column='CHECK_ID_D3_FNAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_d3_lname = models.CharField(db_column='CHECK_ID_D3_LNAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_decline_reason_with_id = models.CharField(db_column='CHECK_ID_DECLINE_REASON_WITH_ID', max_length=15, blank=True, null=True)  # Field name made lowercase.
    check_id_exception_code = models.CharField(db_column='CHECK_ID_EXCEPTION_CODE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_id = models.BigIntegerField(db_column='CHECK_ID_ID', blank=True, null=True)  # Field name made lowercase.
    check_id_id_type = models.CharField(db_column='CHECK_ID_ID_TYPE', max_length=13, blank=True, null=True)  # Field name made lowercase.
    check_id_imei = models.CharField(db_column='CHECK_ID_IMEI', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_input_method = models.CharField(db_column='CHECK_ID_INPUT_METHOD', max_length=6, blank=True, null=True)  # Field name made lowercase.
    check_id_name_match = models.CharField(db_column='CHECK_ID_NAME_MATCH', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_name_match_degrees = models.CharField(db_column='CHECK_ID_NAME_MATCH_DEGREES', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_name_match_type = models.CharField(db_column='CHECK_ID_NAME_MATCH_TYPE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_no_scan_reason = models.CharField(db_column='CHECK_ID_NO_SCAN_REASON', max_length=13, blank=True, null=True)  # Field name made lowercase.
    check_id_ran_call = models.IntegerField(db_column='CHECK_ID_RAN_CALL', blank=True, null=True)  # Field name made lowercase.
    check_id_ran_call_no_id_reason = models.CharField(db_column='CHECK_ID_RAN_CALL_NO_ID_REASON', max_length=22, blank=True, null=True)  # Field name made lowercase.
    check_id_scan_screen_used = models.IntegerField(db_column='CHECK_ID_SCAN_SCREEN_USED', blank=True, null=True)  # Field name made lowercase.
    check_id_showed_valid_id = models.IntegerField(db_column='CHECK_ID_SHOWED_VALID_ID', blank=True, null=True)  # Field name made lowercase.
    check_id_tech_id = models.CharField(db_column='CHECK_ID_TECH_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    chg_entitlement = models.CharField(db_column='CHG_ENTITLEMENT', max_length=1, blank=True, null=True)  # Field name made lowercase.
    clearing_code = models.CharField(db_column='CLEARING_CODE', max_length=100, blank=True, null=True)  # Field name made lowercase.
    cm_dispatch = models.IntegerField(db_column='CM_DISPATCH', blank=True, null=True)  # Field name made lowercase.
    cm_spp = models.IntegerField(db_column='CM_SPP', blank=True, null=True)  # Field name made lowercase.
    cm_trk = models.IntegerField(db_column='CM_TRK', blank=True, null=True)  # Field name made lowercase.
    co_dispatch = models.IntegerField(db_column='CO_DISPATCH', blank=True, null=True)  # Field name made lowercase.
    co_ext = models.IntegerField(db_column='CO_EXT', blank=True, null=True)  # Field name made lowercase.
    detailed_problem_code = models.CharField(db_column='DETAILED_PROBLEM_CODE', max_length=6, blank=True, null=True)  # Field name made lowercase.
    is_duplicate = models.IntegerField(db_column='IS_DUPLICATE', blank=True, null=True)  # Field name made lowercase.
    was_duplicated = models.IntegerField(db_column='WAS_DUPLICATED', blank=True, null=True)  # Field name made lowercase.
    enroute_cost = models.DecimalField(db_column='ENROUTE_COST', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    eta_count = models.IntegerField(db_column='ETA_COUNT', blank=True, null=True)  # Field name made lowercase.
    fac_type = models.CharField(db_column='FAC_TYPE', max_length=7, blank=True, null=True)  # Field name made lowercase.
    first_shop = models.CharField(db_column='FIRST_SHOP', max_length=10, blank=True, null=True)  # Field name made lowercase.
    first_spot_time = models.DateTimeField(db_column='FIRST_SPOT_TIME', blank=True, null=True)  # Field name made lowercase.
    first_tcd = models.CharField(db_column='FIRST_TCD', max_length=5, blank=True, null=True)  # Field name made lowercase.
    first_spot_id = models.CharField(db_column='FIRST_SPOT_ID', max_length=100, blank=True, null=True)  # Field name made lowercase.
    grid_id = models.CharField(db_column='GRID_ID', max_length=20, blank=True, null=True)  # Field name made lowercase.
    last_spot_time = models.DateTimeField(db_column='LAST_SPOT_TIME', blank=True, null=True)  # Field name made lowercase.
    miles_dest = models.IntegerField(db_column='MILES_DEST', blank=True, null=True)  # Field name made lowercase.
    plus_ind = models.CharField(db_column='PLUS_IND', max_length=2, blank=True, null=True)  # Field name made lowercase.
    reassign_reason_code = models.CharField(db_column='REASSIGN_REASON_CODE', max_length=20, blank=True, null=True)  # Field name made lowercase.
    renewal_mnth = models.IntegerField(db_column='RENEWAL_MNTH', blank=True, null=True)  # Field name made lowercase.
    resolution = models.CharField(db_column='RESOLUTION', max_length=10, blank=True, null=True)  # Field name made lowercase.
    resolution_desc = models.CharField(db_column='RESOLUTION_DESC', max_length=255, blank=True, null=True)  # Field name made lowercase.
    sc_call_clb_cd = models.CharField(db_column='SC_CALL_CLB_CD', max_length=20, blank=True, null=True)  # Field name made lowercase.
    sc_call_mbr_id = models.CharField(db_column='SC_CALL_MBR_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    svc_facl_rep_id = models.CharField(db_column='SVC_FACL_REP_ID', max_length=120, blank=True, null=True)  # Field name made lowercase.
    tcd = models.CharField(db_column='TCD', max_length=5, blank=True, null=True)  # Field name made lowercase.
    text_message = models.IntegerField(db_column='TEXT_MESSAGE', blank=True, null=True)  # Field name made lowercase.
    tlc_desc = models.CharField(db_column='TLC_DESC', max_length=255, blank=True, null=True)  # Field name made lowercase.
    tow_cost = models.DecimalField(db_column='TOW_COST', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    truck = models.CharField(db_column='TRUCK', max_length=120, blank=True, null=True)  # Field name made lowercase.
    org_svc_facl_id = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_ID', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_svc_facl_id')  # Field name made lowercase.
    org_business_id = models.ForeignKey(Organization, db_column='ORG_BUSINESS_ID', blank=True,on_delete=models.SET_NULL, null=True, related_name='raw_ops_business_id')  # Field name made lowercase.
    org_club_region = models.ForeignKey(Organization, db_column='ORG_CLUB_REGION', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_club_region')  # Field name made lowercase.
    org_call_center = models.ForeignKey(Organization, db_column='ORG_CALL_CENTER', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_call_center')  # Field name made lowercase.
    org_grid = models.ForeignKey(Organization, db_column='ORG_GRID', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_grid')  # Field name made lowercase.
    org_bl_state = models.ForeignKey(Organization, db_column='ORG_BL_STATE', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_bl_state')  # Field name made lowercase.
    org_facility_state = models.ForeignKey(Organization,db_column='ORG_FACILITY_STATE', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_facility_state')  # Field name made lowercase.
    org_hub = models.ForeignKey(Organization,db_column='ORG_HUB', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_hub')  # Field name made lowercase.
    emp_driver_id = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_emp_driver_id')  # Field name made lowercase.
    emp_call_center_operator = models.ForeignKey(Employee,db_column='EMP_CALL_CENTER_OPERATOR', blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_emp_call_center_operator')  # Field name made lowercase.
    org_svc_facl_rep = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_REP', blank=True,on_delete=models.SET_NULL, null=True, related_name='raw_ops_svc_facl_rep')  # Field name made lowercase.
    updated_ops_joined = models.DateTimeField(db_column='UPDATED_OPS_JOINED', blank=True, null=True)  # Field name made lowercase.
    call_accepted = models.IntegerField(db_column='CALL_ACCEPTED', blank=True, null=True)  # Field name made lowercase.
    ata = models.DecimalField(db_column='ATA', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    pta = models.DecimalField(db_column='PTA', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    ata_minus_pta = models.DecimalField(db_column='ATA_MINUS_PTA', max_digits=15, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    early = models.IntegerField(db_column='EARLY', blank=True, null=True)  # Field name made lowercase.
    late = models.IntegerField(db_column='LATE', blank=True, null=True)  # Field name made lowercase.
    on_time = models.IntegerField(db_column='ON_TIME', blank=True, null=True)  # Field name made lowercase.
    long_ata = models.IntegerField(db_column='LONG_ATA', blank=True, null=True)  # Field name made lowercase.
    nsr = models.IntegerField(db_column='NSR', blank=True, null=True)  # Field name made lowercase.
    cancelled = models.IntegerField(db_column='CANCELLED', blank=True, null=True)  # Field name made lowercase.
    ng_to_g = models.IntegerField(db_column='NG_TO_G', blank=True, null=True)  # Field name made lowercase.
    g_to_ng = models.IntegerField(db_column='G_TO_NG', blank=True, null=True)  # Field name made lowercase.
    g_to_g = models.IntegerField(db_column='G_TO_G', blank=True, null=True)  # Field name made lowercase.
    ng_to_ng = models.IntegerField(db_column='NG_TO_NG', blank=True, null=True)  # Field name made lowercase.
    dispatch_communicated = models.IntegerField(db_column='DISPATCH_COMMUNICATED', blank=True, null=True)  # Field name made lowercase.
    outside_communicated = models.IntegerField(db_column='OUTSIDE_COMMUNICATED', blank=True, null=True)  # Field name made lowercase.
    lost_call = models.IntegerField(db_column='LOST_CALL', blank=True, null=True)  # Field name made lowercase.
    field_rep_aaa_emp_num = models.CharField(db_column='FIELD_REP_AAA_EMP_NUM', max_length=100, blank=True, null=True)  # Field name made lowercase.
    reroute = models.IntegerField(db_column='REROUTE', blank=True, null=True)  # Field name made lowercase.
    field_rep_name = models.CharField(db_column='FIELD_REP_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    reroute_360 = models.IntegerField(db_column='REROUTE_360', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'dashboard_rawops'
        unique_together = (('sc_id', 'sc_dt', 'comm_ctr_id'),)

# employee dashboards

class EmployeeDashboard(models.Model):
    owner = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='owned_dashboards')
    employees = models.ManyToManyField(Employee)
    name = models.CharField(max_length=500, null=True, blank=True)
    order = models.IntegerField(null=True)
    comments = models.TextField(null=True, blank=True)
    notification = models.TextField(null=True, blank=True)
    notification_type = models.CharField(max_length=500, null=True, blank=True)


class DashboardAnnotation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='organization_dashboard_annotation')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='dashboard_annotation')
    json = models.TextField()

class EmployeeDashboardElement(models.Model):
    dashboard = models.ForeignKey(EmployeeDashboard, on_delete=models.CASCADE, related_name='elements')
    request = models.TextField(null=True)
    chart_type = models.CharField(null=True, max_length=255)
    name = models.CharField(max_length=255, null=True, blank=True)
    comments = models.TextField(null=True)
    order = models.IntegerField(null=True)
    initial_annotation = models.ForeignKey(DashboardAnnotation, on_delete=models.SET_NULL, null=True, related_name='dashboard_element_annotation')

class DashboardComment(models.Model):
    dashboard_element = models.ForeignKey(EmployeeDashboardElement, on_delete=models.SET_NULL, null=True, related_name='dashboard_comment')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='organization_dashboard_comment')

    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='employee_dashboard_comment')
    created_on = models.DateTimeField(auto_now=True)
    message = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.SET_NULL, null=True)
    rating = models.ManyToManyField(Employee)
    sender_avatar = models.CharField(max_length=255, null=True, blank=True)
    annotation = models.ForeignKey(DashboardAnnotation, on_delete=models.SET_NULL, null=True, related_name='annotation_dashboard_comment')

class DashboardCommentReadStatus(models.Model):
    dashboard_element = models.ForeignKey(EmployeeDashboardElement, on_delete=models.SET_NULL, null=True, related_name='dashboard_element_read')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='organization_dashboard_comment_read_status')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='employee_dashboard_comment_read_status')
    viewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dashboard_comment_viewer')
    viewed = models.BooleanField(default=False)

class RawStd12EQuestions(models.Model):
    field = models.CharField(max_length=255, blank=True, null=True)
    question = models.TextField(blank=True, null=True)
    question_type = models.CharField(max_length=255, blank=True, null=True)
    question_options = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.question_options:
            self.question_options = "null"
        return super(RawStd12EQuestions, self).save(*args, **kwargs)

class Std12EExtraCols(models.Model):
    sc_dt_surveys = models.DateTimeField(db_column='SC_DT_surveys', blank=True, null=True)  # Field name made lowercase.
    sc_id_surveys = models.BigIntegerField(db_column='SC_ID_surveys', blank=True, null=True)  # Field name made lowercase.
    aar_fac_id = models.TextField(db_column='AAR_FAC_ID', blank=True, null=True)  # Field name made lowercase.
    aar_fac_name = models.TextField(db_column='AAR_FAC_NAME', blank=True, null=True)  # Field name made lowercase.
    aar_or_co_fac_indic = models.TextField(db_column='AAR_OR_CO_FAC_INDIC', blank=True, null=True)  # Field name made lowercase.
    accd_insur = models.TextField(db_column='ACCD_INSUR', blank=True, null=True)  # Field name made lowercase.
    aces_b_veh_id = models.TextField(db_column='ACES_B_VEH_ID', blank=True, null=True)  # Field name made lowercase.
    alt_tow_dest = models.TextField(db_column='ALT_TOW_DEST', blank=True, null=True)  # Field name made lowercase.
    aqs12_eli = models.TextField(db_column='AQS12_ELI', blank=True, null=True)  # Field name made lowercase.
    ba_dol = models.TextField(db_column='BA_DOL', blank=True, null=True)  # Field name made lowercase.
    can_ser_ind = models.TextField(db_column='CAN_SER_IND', blank=True, null=True)  # Field name made lowercase.
    cas_cll_ind = models.TextField(db_column='CAS_CLL_IND', blank=True, null=True)  # Field name made lowercase.
    cc_amt = models.FloatField(db_column='CC_AMT', blank=True, null=True)  # Field name made lowercase.
    chg_entitlement = models.TextField(db_column='CHG_ENTITLEMENT', blank=True, null=True)  # Field name made lowercase.
    chrg_entitlement = models.TextField(db_column='CHRG_ENTITLEMENT', blank=True, null=True)  # Field name made lowercase.
    clb_opt_fld_1 = models.TextField(db_column='CLB_OPT_FLD_1', blank=True, null=True)  # Field name made lowercase.
    clb_opt_fld_2 = models.TextField(db_column='CLB_OPT_FLD_2', blank=True, null=True)  # Field name made lowercase.
    clb_opt_fld_3 = models.TextField(db_column='CLB_OPT_FLD_3', blank=True, null=True)  # Field name made lowercase.
    clb_opt_fld_4 = models.TextField(db_column='CLB_OPT_FLD_4', blank=True, null=True)  # Field name made lowercase.
    clb_opt_fld_5 = models.TextField(db_column='CLB_OPT_FLD_5', blank=True, null=True)  # Field name made lowercase.
    ers_cc_id = models.TextField(db_column='ERS_CC_ID', blank=True, null=True)  # Field name made lowercase.
    ers_cc_role = models.TextField(db_column='ERS_CC_ROLE', blank=True, null=True)  # Field name made lowercase.
    ers_reimb = models.TextField(db_column='ERS_Reimb', blank=True, null=True)  # Field name made lowercase.
    ers_ser_rec = models.TextField(db_column='ERS_SER_REC', blank=True, null=True)  # Field name made lowercase.
    hm_lkout = models.TextField(db_column='HM_LKOUT', blank=True, null=True)  # Field name made lowercase.
    itu_bbt = models.TextField(db_column='ITU_BBT', blank=True, null=True)  # Field name made lowercase.
    itu_nav = models.TextField(db_column='ITU_NAV', blank=True, null=True)  # Field name made lowercase.
    itu_odb2 = models.TextField(db_column='ITU_ODB2', blank=True, null=True)  # Field name made lowercase.
    ivr_aqs12_eli = models.TextField(db_column='IVR_AQS12_ELI', blank=True, null=True)  # Field name made lowercase.
    ivr_requested = models.TextField(db_column='IVR_REQUESTED', blank=True, null=True)  # Field name made lowercase.
    network_pvd = models.TextField(db_column='NETWORK_PVD', blank=True, null=True)  # Field name made lowercase.
    ob_bc_scanner = models.TextField(db_column='OB_BC_SCANNER', blank=True, null=True)  # Field name made lowercase.
    ob_printer = models.TextField(db_column='OB_PRINTER', blank=True, null=True)  # Field name made lowercase.
    odb_pos = models.TextField(db_column='ODB_POS', blank=True, null=True)  # Field name made lowercase.
    otg_sol_code = models.TextField(db_column='OTG_SOL_CODE', blank=True, null=True)  # Field name made lowercase.
    oth_dol = models.TextField(db_column='OTH_DOL', blank=True, null=True)  # Field name made lowercase.
    pl_dol = models.TextField(db_column='PL_DOL', blank=True, null=True)  # Field name made lowercase.
    prim_rpr_perfda = models.TextField(db_column='PRIM_RPR_PERFDA', blank=True, null=True)  # Field name made lowercase.
    prim_rpr_perfdb = models.TextField(db_column='PRIM_RPR_PERFDB', blank=True, null=True)  # Field name made lowercase.
    rap_ind = models.TextField(db_column='RAP_IND', blank=True, null=True)  # Field name made lowercase.
    rpst_dt = models.TextField(db_column='RPST_DT', blank=True, null=True)  # Field name made lowercase.
    rpst_trained = models.TextField(db_column='RPST_TRAINED', blank=True, null=True)  # Field name made lowercase.
    rv_dol = models.TextField(db_column='RV_DOL', blank=True, null=True)  # Field name made lowercase.
    sc_cl_dttm = models.DateTimeField(db_column='SC_CL_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_disposition = models.TextField(db_column='SC_DISPOSITION', blank=True, null=True)  # Field name made lowercase.
    sc_di_dttm = models.DateTimeField(db_column='SC_DI_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_lst_di_dttm = models.DateTimeField(db_column='SC_LST_DI_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_ls_or_tw_cd = models.TextField(db_column='SC_LS_OR_TW_CD', blank=True, null=True)  # Field name made lowercase.
    sc_mbr_cb_ph_cl = models.TextField(db_column='SC_MBR_CB_PH_CL', blank=True, null=True)  # Field name made lowercase.
    sc_miles_tw = models.TextField(db_column='SC_MILES_TW', blank=True, null=True)  # Field name made lowercase.
    sc_mob_diag_cd = models.TextField(db_column='SC_MOB_DIAG_CD', blank=True, null=True)  # Field name made lowercase.
    sc_res_cd2 = models.TextField(db_column='SC_RES_CD2', blank=True, null=True)  # Field name made lowercase.
    sc_rev_ls_or_tw_cd = models.TextField(db_column='SC_REV_LS_OR_TW_CD', blank=True, null=True)  # Field name made lowercase.
    sc_rso = models.TextField(db_column='SC_RSO', blank=True, null=True)  # Field name made lowercase.
    sc_tw_dttm = models.DateTimeField(db_column='SC_TW_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_veh_manfr_nm = models.TextField(db_column='SC_VEH_MANFR_NM', blank=True, null=True)  # Field name made lowercase.
    sc_veh_manf_yr_dt = models.TextField(db_column='SC_VEH_MANF_YR_DT', blank=True, null=True)  # Field name made lowercase.
    sc_veh_mdl_nm = models.TextField(db_column='SC_VEH_MDL_NM', blank=True, null=True)  # Field name made lowercase.
    sc_veh_type = models.TextField(db_column='SC_VEH_TYPE', blank=True, null=True)  # Field name made lowercase.
    sday_ssvc = models.TextField(db_column='SDAY_SSVC', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'std12e_extra_cols'

class Std12EReduced(models.Model):
    associate_count = models.BigIntegerField(db_column='ASSOCIATE_COUNT', blank=True, null=True)  # Field name made lowercase.
    associate_id = models.TextField(db_column='ASSOCIATE_ID', blank=True, null=True)  # Field name made lowercase.
    ata = models.DecimalField(db_column='ATA', max_digits=22, decimal_places=1, blank=True, null=True)  # Field name made lowercase.
    ata_minus_pta = models.FloatField(db_column='ATA_MINUS_PTA', blank=True, null=True)  # Field name made lowercase.
    accreditation = models.CharField(db_column='ACCREDITATION', max_length=255, blank=True, null=True)  # Field name made lowercase.
    age_group = models.TextField(db_column='AGE_GROUP', blank=True, null=True)  # Field name made lowercase.
    base_cost = models.FloatField(db_column='BASE_COST', blank=True, null=True)  # Field name made lowercase.
    battery_truck = models.IntegerField(db_column='BATTERY_TRUCK', blank=True, null=True)  # Field name made lowercase.
    battery_test = models.BigIntegerField(db_column='BATTERY_TEST', blank=True, null=True)  # Field name made lowercase.
    batt_svc_veh_disp_ind = models.TextField(db_column='BATT_SVC_VEH_DISP_IND', blank=True, null=True)  # Field name made lowercase.
    batt_test_on_batt_call = models.IntegerField(db_column='BATT_TEST_ON_BATT_CALL', blank=True, null=True)  # Field name made lowercase.
    bl_home_indic = models.TextField(db_column='BL_HOME_INDIC', blank=True, null=True)  # Field name made lowercase.
    bl_lat = models.FloatField(db_column='BL_LAT', blank=True, null=True)  # Field name made lowercase.
    bl_long = models.FloatField(db_column='BL_LONG', blank=True, null=True)  # Field name made lowercase.
    bl_near_cty_nm = models.CharField(db_column='BL_NEAR_CTY_NM', max_length=255, blank=True, null=True)  # Field name made lowercase.
    bl_state_cd = models.CharField(db_column='BL_STATE_CD', max_length=100, blank=True, null=True)  # Field name made lowercase.
    facility_zip = models.CharField(db_column='FACILITY_ZIP', max_length=20, blank=True, null=True)  # Field name made lowercase.
    battery_service_type = models.TextField(db_column='BATTERY_SERVICE_TYPE', blank=True, null=True)  # Field name made lowercase.
    call_accepted = models.IntegerField(db_column='CALL_ACCEPTED', blank=True, null=True)  # Field name made lowercase.
    call_center = models.TextField(db_column='CALL_CENTER', blank=True, null=True)  # Field name made lowercase.
    call_center_operator = models.CharField(db_column='CALL_CENTER_OPERATOR', max_length=255, blank=True, null=True)  # Field name made lowercase.
    call_cost = models.FloatField(db_column='CALL_COST', blank=True, null=True)  # Field name made lowercase.
    call_mover = models.TextField(db_column='CALL_MOVER', blank=True, null=True)  # Field name made lowercase.
    cancelled = models.IntegerField(db_column='CANCELLED', blank=True, null=True)  # Field name made lowercase.
    check_id_check_fail = models.IntegerField(db_column='CHECK_ID_CHECK_FAIL', blank=True, null=True)  # Field name made lowercase.
    check_id_compliant = models.IntegerField(db_column='CHECK_ID_COMPLIANT', blank=True, null=True)  # Field name made lowercase.
    check_id_decline_reason_with_id = models.CharField(db_column='CHECK_ID_DECLINE_REASON_WITH_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_id = models.BigIntegerField(db_column='CHECK_ID_ID', blank=True, null=True)  # Field name made lowercase.
    check_id_id_type = models.CharField(db_column='CHECK_ID_ID_TYPE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_imei = models.CharField(db_column='CHECK_ID_IMEI', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_input_method = models.CharField(db_column='CHECK_ID_INPUT_METHOD', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_no_scan_reason = models.CharField(db_column='CHECK_ID_NO_SCAN_REASON', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_ran_call = models.IntegerField(db_column='CHECK_ID_RAN_CALL', blank=True, null=True)  # Field name made lowercase.
    check_id_ran_call_no_id_reason = models.CharField(db_column='CHECK_ID_RAN_CALL_NO_ID_REASON', max_length=255, blank=True, null=True)  # Field name made lowercase.
    check_id_showed_valid_id = models.IntegerField(db_column='CHECK_ID_SHOWED_VALID_ID', blank=True, null=True)  # Field name made lowercase.
    clear_time = models.DateTimeField(db_column='CLEAR_TIME', blank=True, null=True)  # Field name made lowercase.
    club = models.TextField(db_column='CLUB', blank=True, null=True)  # Field name made lowercase.
    club_group = models.TextField(db_column='CLUB_GROUP', blank=True, null=True)  # Field name made lowercase.
    club_name = models.TextField(db_column='CLUB_NAME', blank=True, null=True)  # Field name made lowercase.
    club_recode = models.TextField(db_column='CLUB_RECODE', blank=True, null=True)  # Field name made lowercase.
    club_surveys = models.TextField(db_column='CLUB_SURVEYS', blank=True, null=True)  # Field name made lowercase.
    cl_pay_dt = models.TextField(db_column='CL_PAY_DT', blank=True, null=True)  # Field name made lowercase.
    cm_dispatch = models.BigIntegerField(db_column='CM_DISPATCH', blank=True, null=True)  # Field name made lowercase.
    cm_spp = models.BigIntegerField(db_column='CM_SPP', blank=True, null=True)  # Field name made lowercase.
    cm_trk = models.BigIntegerField(db_column='CM_TRK', blank=True, null=True)  # Field name made lowercase.
    col_cll = models.TextField(db_column='COL_CLL', blank=True, null=True)  # Field name made lowercase.
    comm_ctr_id = models.CharField(db_column='COMM_CTR_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    con_acc_hwy = models.TextField(db_column='CON_ACC_HWY', blank=True, null=True)  # Field name made lowercase.
    co_dispatch = models.BigIntegerField(db_column='CO_DISPATCH', blank=True, null=True)  # Field name made lowercase.
    co_ext = models.BigIntegerField(db_column='CO_EXT', blank=True, null=True)  # Field name made lowercase.
    club_tier = models.TextField(db_column='CLUB_TIER', blank=True, null=True)  # Field name made lowercase.
    date_updated = models.DateTimeField(db_column='DATE_UPDATED', blank=True, null=True)  # Field name made lowercase.
    date_updated_surveys = models.DateTimeField(db_column='DATE_UPDATED_SURVEYS')  # Field name made lowercase.
    dispatch_communicated = models.IntegerField(db_column='DISPATCH_COMMUNICATED', blank=True, null=True)  # Field name made lowercase.
    disp_unit_type = models.TextField(db_column='DISP_UNIT_TYPE', blank=True, null=True)  # Field name made lowercase.
    driver_id = models.TextField(db_column='DRIVER_ID', blank=True, null=True)  # Field name made lowercase.
    driver_name = models.CharField(db_column='DRIVER_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    drv_id = models.FloatField(db_column='DRV_ID', blank=True, null=True)  # Field name made lowercase.
    dtl_prob_code = models.TextField(db_column='DTL_PROB_CODE', blank=True, null=True)  # Field name made lowercase.
    dup_as_srv_tck = models.TextField(db_column='DUP_AS_SRV_TCK', blank=True, null=True)  # Field name made lowercase.
    dup_call_id = models.TextField(db_column='DUP_CALL_ID', blank=True, null=True)  # Field name made lowercase.
    dup_cll_veh_chg = models.TextField(db_column='DUP_CLL_VEH_CHG', blank=True, null=True)  # Field name made lowercase.
    dup_svc_call_date = models.TextField(db_column='DUP_SVC_CALL_DATE', blank=True, null=True)  # Field name made lowercase.
    desc2 = models.FloatField(db_column='DESC2', blank=True, null=True)  # Field name made lowercase.
    desc2_4_text = models.TextField(db_column='DESC2_4_TEXT', blank=True, null=True)  # Field name made lowercase.
    driver5 = models.FloatField(db_column='DRIVER5', blank=True, null=True)  # Field name made lowercase.
    duration_in_seconds_field = models.FloatField(db_column='DURATION__IN_SECONDS_', blank=True, null=True)  # Field name made lowercase. Field renamed because it contained more than one '_' in a row. Field renamed because it ended with '_'.
    early = models.IntegerField(db_column='EARLY', blank=True, null=True)  # Field name made lowercase.
    emp_call_center_operator = models.IntegerField(db_column='EMP_CALL_CENTER_OPERATOR', blank=True, null=True)  # Field name made lowercase.
    emp_driver_id = models.ForeignKey(Employee, db_column='EMP_DRIVER_ID', blank=True, null=True, on_delete=models.CASCADE, related_name='survey_driver')
    org_svc_facility_rep = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_REP', blank=True, null=True, on_delete=models.CASCADE, related_name='survey_facility_rep')
    enroute_cost = models.FloatField(db_column='ENROUTE_COST', blank=True, null=True)  # Field name made lowercase.
    er_miles = models.TextField(db_column='ER_MILES', blank=True, null=True)  # Field name made lowercase.
    eta = models.BigIntegerField(db_column='ETA', blank=True, null=True)  # Field name made lowercase.
    externalreference = models.TextField(db_column='EXTERNALREFERENCE', blank=True, null=True)  # Field name made lowercase.
    facility_sat = models.IntegerField(db_column='FACILITY_SAT', blank=True, null=True)  # Field name made lowercase.
    fac_dir_call = models.TextField(db_column='FAC_DIR_CALL', blank=True, null=True)  # Field name made lowercase.
    fac_type = models.TextField(db_column='FAC_TYPE', blank=True, null=True)  # Field name made lowercase.
    failed_battery_test = models.BigIntegerField(db_column='FAILED_BATTERY_TEST', blank=True, null=True)  # Field name made lowercase.
    first_fac_type = models.CharField(db_column='FIRST_FAC_TYPE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    fst_ol_time = models.DateTimeField(db_column='FST_OL_TIME', blank=True, null=True)  # Field name made lowercase.
    fst_shop = models.CharField(db_column='FST_SHOP', max_length=255, blank=True, null=True)  # Field name made lowercase.
    fst_spot_time = models.DateTimeField(db_column='FST_SPOT_TIME', blank=True, null=True)  # Field name made lowercase.
    fst_tr_code = models.TextField(db_column='FST_TR_CODE', blank=True, null=True)  # Field name made lowercase.
    gps_ind = models.TextField(db_column='GPS_IND', blank=True, null=True)  # Field name made lowercase.
    grid_id = models.CharField(db_column='GRID_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    grid_zipcode = models.CharField(db_column='GRID_ZIPCODE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    g_to_g = models.IntegerField(db_column='G_TO_G', blank=True, null=True)  # Field name made lowercase.
    g_to_ng = models.IntegerField(db_column='G_TO_NG', blank=True, null=True)  # Field name made lowercase.
    heavy_user = models.FloatField(db_column='HEAVY_USER', blank=True, null=True)  # Field name made lowercase.
    invite_sc_dt = models.DateTimeField(db_column='INVITE_SC_DT', blank=True, null=True)  # Field name made lowercase.
    kept_informed_sat = models.IntegerField(db_column='KEPT_INFORMED_SAT', blank=True, null=True)  # Field name made lowercase.
    late = models.IntegerField(db_column='LATE', blank=True, null=True)  # Field name made lowercase.
    long_ata = models.IntegerField(db_column='LONG_ATA', blank=True, null=True)  # Field name made lowercase.
    lst_spot_time = models.DateTimeField(db_column='LST_SPOT_TIME', blank=True, null=True)  # Field name made lowercase.
    match_key = models.CharField(db_column='MATCH_KEY', max_length=255, blank=True, null=True)  # Field name made lowercase.
    match_key_surveys = models.CharField(db_column='MATCH_KEY_SURVEYS', max_length=255, blank=True, null=True)  # Field name made lowercase.
    mbr_complaint = models.TextField(db_column='MBR_COMPLAINT', blank=True, null=True)  # Field name made lowercase.
    mbr_compliment = models.TextField(db_column='MBR_COMPLIMENT', blank=True, null=True)  # Field name made lowercase.
    mbr_cty_nm = models.TextField(db_column='MBR_CTY_NM', blank=True, null=True)  # Field name made lowercase.
    mbr_join_dt = models.TextField(db_column='MBR_JOIN_DT', blank=True, null=True)  # Field name made lowercase.
    mbr_mbr_typ = models.TextField(db_column='MBR_MBR_TYP', blank=True, null=True)  # Field name made lowercase.
    mbr_pstl_cd = models.CharField(db_column='MBR_PSTL_CD', max_length=255, blank=True, null=True)  # Field name made lowercase.
    mbr_st_cd = models.TextField(db_column='MBR_ST_CD', blank=True, null=True)  # Field name made lowercase.
    miles_dest = models.FloatField(db_column='MILES_DEST', blank=True, null=True)  # Field name made lowercase.
    ng_to_g = models.IntegerField(db_column='NG_TO_G', blank=True, null=True)  # Field name made lowercase.
    ng_to_ng = models.IntegerField(db_column='NG_TO_NG', blank=True, null=True)  # Field name made lowercase.
    nps = models.FloatField(db_column='NPS', blank=True, null=True)  # Field name made lowercase.
    nps_nps_group = models.FloatField(db_column='NPS_NPS_GROUP', blank=True, null=True)  # Field name made lowercase.
    nsr = models.IntegerField(db_column='NSR', blank=True, null=True)  # Field name made lowercase.
    nt_call_ind = models.TextField(db_column='NT_CALL_IND', blank=True, null=True)  # Field name made lowercase.
    n_mbr_ind = models.TextField(db_column='N_MBR_IND', blank=True, null=True)  # Field name made lowercase.
    on_time = models.IntegerField(db_column='ON_TIME', blank=True, null=True)  # Field name made lowercase.
    org_business_id = models.ForeignKey(Organization, db_column='ORG_BUSINESS_ID', blank=True, null=True, on_delete=models.CASCADE, related_name='survey_biz_id')
    org_call_center = models.IntegerField(db_column='ORG_CALL_CENTER', blank=True, null=True)  # Field name made lowercase.
    org_grid = models.IntegerField(db_column='ORG_GRID', blank=True, null=True)  # Field name made lowercase.
    org_bl_state = models.ForeignKey(Organization, db_column='ORG_BL_STATE', blank=True, null=True, on_delete=models.CASCADE, related_name='survey_bl_state')
    org_facility_state = models.ForeignKey(Organization, db_column='ORG_FACILITY_STATE', blank=True, null=True, on_delete=models.CASCADE, related_name='survey_facility_state')
    org_hub = models.IntegerField(db_column='ORG_HUB', blank=True, null=True)  # Field name made lowercase.
    org_svc_facl_id = models.ForeignKey(Organization, db_column='ORG_SVC_FACL_ID', blank=True, null=True, on_delete=models.CASCADE, related_name='survey_facl_id')  # Field name made lowercase.
    outside_communicated = models.IntegerField(db_column='OUTSIDE_COMMUNICATED', blank=True, null=True)  # Field name made lowercase.
    overall_sat = models.IntegerField(db_column='OVERALL_SAT', blank=True, null=True)  # Field name made lowercase.
    outc1 = models.FloatField(db_column='OUTC1', blank=True, null=True)  # Field name made lowercase.
    plus_ind = models.TextField(db_column='PLUS_IND', blank=True, null=True)  # Field name made lowercase.
    primary_key = models.BigIntegerField(db_column='PRIMARY_KEY', blank=True, null=True)  # Field name made lowercase.
    prim_bat_rider = models.TextField(db_column='PRIM_BAT_RIDER', blank=True, null=True)  # Field name made lowercase.
    first_tow_status_time = models.DateTimeField(db_column='FIRST_TOW_STATUS_TIME', blank=True, null=True)  # Field name made lowercase.
    promised_time = models.DateTimeField(db_column='PROMISED_TIME', blank=True, null=True)  # Field name made lowercase.
    pta = models.DecimalField(db_column='PTA', max_digits=22, decimal_places=1, blank=True, null=True)  # Field name made lowercase.
    q24 = models.FloatField(db_column='Q24', blank=True, null=True)  # Field name made lowercase.
    q26 = models.FloatField(db_column='Q26', blank=True, null=True)  # Field name made lowercase.
    q27 = models.FloatField(db_column='Q27', blank=True, null=True)  # Field name made lowercase.
    q28 = models.FloatField(db_column='Q28', blank=True, null=True)  # Field name made lowercase.
    q30 = models.TextField(db_column='Q30', blank=True, null=True)  # Field name made lowercase.
    q_sc_dt = models.DateTimeField(db_column='Q_SC_DT', blank=True, null=True)  # Field name made lowercase.
    q_chl = models.CharField(db_column='Q_CHL', blank=True, null=True, max_length=100)  # Field name made lowercase.
    distribution = models.CharField(db_column='Distribution', blank=True, null=True, max_length=100)  # Field name made lowercase.
    rec_ind = models.TextField(db_column='REC_IND', blank=True, null=True)  # Field name made lowercase.
    region = models.CharField(db_column='REGION', max_length=255, blank=True, null=True)  # Field name made lowercase.
    renewal_mnth = models.TextField(db_column='RENEWAL_MNTH', blank=True, null=True)  # Field name made lowercase.
    replaced_batt_on_failed_batt_call = models.IntegerField(db_column='REPLACED_BATT_ON_FAILED_BATT_CALL', blank=True, null=True)  # Field name made lowercase.
    request_service_sat = models.IntegerField(db_column='REQUEST_SERVICE_SAT', blank=True, null=True)  # Field name made lowercase.
    resolution = models.TextField(db_column='RESOLUTION', blank=True, null=True)  # Field name made lowercase.
    resolution_desc = models.TextField(db_column='RESOLUTION_DESC', blank=True, null=True)  # Field name made lowercase.
    responserequests = models.TextField(db_column='RESPONSEREQUESTS', blank=True, null=True)  # Field name made lowercase.
    response_loc_req = models.TextField(db_column='RESPONSE_LOC_REQ', blank=True, null=True)  # Field name made lowercase.
    response_loc_used = models.TextField(db_column='RESPONSE_LOC_USED', blank=True, null=True)  # Field name made lowercase.
    response_reg = models.TextField(db_column='RESPONSE_REG', blank=True, null=True)  # Field name made lowercase.
    response_sat = models.IntegerField(db_column='RESPONSE_SAT', blank=True, null=True)  # Field name made lowercase.
    re_tm = models.DateTimeField(db_column='RE_TM', blank=True, null=True)  # Field name made lowercase.
    recordeddate = models.DateTimeField(db_column='RECORDEDDATE', blank=True, null=True)  # Field name made lowercase.
    renew = models.FloatField(db_column='RENEW', blank=True, null=True)  # Field name made lowercase.
    renew_nps_group = models.FloatField(db_column='RENEW_NPS_GROUP', blank=True, null=True)  # Field name made lowercase.
    responseid = models.TextField(db_column='RESPONSEID', blank=True, null=True)  # Field name made lowercase.
    sc_aaia_batt_typ = models.TextField(db_column='SC_AAIA_BATT_TYP', blank=True, null=True)  # Field name made lowercase.
    sc_batt_repl_indic = models.TextField(db_column='SC_BATT_REPL_INDIC', blank=True, null=True)  # Field name made lowercase.
    sc_batt_test_results = models.TextField(db_column='SC_BATT_TEST_RESULTS', blank=True, null=True)  # Field name made lowercase.
    sc_batt_tst_cd = models.TextField(db_column='SC_BATT_TST_CD', blank=True, null=True)  # Field name made lowercase.
    sc_bat_svc_ind = models.TextField(db_column='SC_BAT_SVC_IND', blank=True, null=True)  # Field name made lowercase.
    sc_call_clb_cd = models.CharField(db_column='SC_CALL_CLB_CD', max_length=255, blank=True, null=True)  # Field name made lowercase.
    sc_call_clb_mbr_id = models.CharField(db_column='SC_CALL_CLB_MBR_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    sc_call_mbr_id = models.CharField(db_column='SC_CALL_MBR_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    sc_clr_cd = models.TextField(db_column='SC_CLR_CD', blank=True, null=True)  # Field name made lowercase.
    sc_club_code = models.TextField(db_column='SC_CLUB_CODE', blank=True, null=True)  # Field name made lowercase.
    sc_comm_ctr = models.TextField(db_column='SC_COMM_CTR', blank=True, null=True)  # Field name made lowercase.
    sc_comm_ctr_sub = models.CharField(db_column='SC_COMM_CTR_SUB', max_length=10)  # Field name made lowercase.
    sc_dt = models.DateField(db_column='SC_DT', blank=True, null=True)  # Field name made lowercase.
    sc_dt_surveys = models.DateField(db_column='SC_DT_SURVEYS')  # Field name made lowercase.
    sc_er_dttm = models.DateTimeField(db_column='SC_ER_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_eta = models.DateTimeField(db_column='SC_ETA', blank=True, null=True)  # Field name made lowercase.
    sc_id = models.BigIntegerField(db_column='SC_ID', blank=True, null=True)  # Field name made lowercase.
    sc_id_surveys = models.BigIntegerField(db_column='SC_ID_SURVEYS')  # Field name made lowercase.
    sc_mbr_cb_indic = models.TextField(db_column='SC_MBR_CB_INDIC', blank=True, null=True)  # Field name made lowercase.
    sc_ol_dttm = models.DateTimeField(db_column='SC_OL_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_prm_arr_dttm = models.DateTimeField(db_column='SC_PRM_ARR_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_prob_cd = models.TextField(db_column='SC_PROB_CD', blank=True, null=True)  # Field name made lowercase.
    sc_reasgn_rsn_cd = models.TextField(db_column='SC_REASGN_RSN_CD', blank=True, null=True)  # Field name made lowercase.
    sc_recv_dttm = models.DateTimeField(db_column='SC_RECV_DTTM', blank=True, null=True)  # Field name made lowercase.
    sc_res_cd = models.TextField(db_column='SC_RES_CD', blank=True, null=True)  # Field name made lowercase.
    sc_svc_clb_cd = models.TextField(db_column='SC_SVC_CLB_CD', blank=True, null=True)  # Field name made lowercase.
    sc_svc_prov_type = models.CharField(db_column='SC_SVC_PROV_TYPE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    short_match_key = models.CharField(db_column='SHORT_MATCH_KEY', max_length=255, blank=True, null=True)  # Field name made lowercase.
    single_state = models.TextField(db_column='SINGLE_STATE', blank=True, null=True)  # Field name made lowercase.
    sms_click = models.TextField(db_column='SMS_CLICK', blank=True, null=True)  # Field name made lowercase.
    sms_elig = models.TextField(db_column='SMS_ELIG', blank=True, null=True)  # Field name made lowercase.
    sms_notify = models.TextField(db_column='SMS_NOTIFY', blank=True, null=True)  # Field name made lowercase.
    sms_opted_in = models.TextField(db_column='SMS_OPTED_IN', blank=True, null=True)  # Field name made lowercase.
    sms_sent = models.TextField(db_column='SMS_SENT', blank=True, null=True)  # Field name made lowercase.
    sp_fac_id = models.TextField(db_column='SP_FAC_ID', blank=True, null=True)  # Field name made lowercase.
    svc_facl_id = models.CharField(db_column='SVC_FACL_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    svc_facl_nm = models.CharField(db_column='SVC_FACL_NM', max_length=255, blank=True, null=True)  # Field name made lowercase.
    svc_facl_rep_id = models.CharField(db_column='SVC_FACL_REP_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    tcd = models.TextField(db_column='TCD', blank=True, null=True)  # Field name made lowercase.
    tech_assist = models.TextField(db_column='TECH_ASSIST', blank=True, null=True)  # Field name made lowercase.
    text_msg = models.BigIntegerField(db_column='TEXT_MSG', blank=True, null=True)  # Field name made lowercase.
    tlc_desc = models.TextField(db_column='TLC_DESC', blank=True, null=True)  # Field name made lowercase.
    tow_cost = models.FloatField(db_column='TOW_COST', blank=True, null=True)  # Field name made lowercase.
    tow_dest_in_record = models.TextField(db_column='TOW_DEST_IN_RECORD', blank=True, null=True)  # Field name made lowercase.
    tow_dest_lat = models.TextField(db_column='TOW_DEST_LAT', blank=True, null=True)  # Field name made lowercase.
    tow_dest_lon = models.TextField(db_column='TOW_DEST_LON', blank=True, null=True)  # Field name made lowercase.
    tow_dest_near_cty_nm = models.TextField(db_column='TOW_DEST_NEAR_CTY_NM', blank=True, null=True)  # Field name made lowercase.
    trc_call = models.TextField(db_column='TRC_CALL', blank=True, null=True)  # Field name made lowercase.
    trk_avl_indic = models.TextField(db_column='TRK_AVL_INDIC', blank=True, null=True)  # Field name made lowercase.
    trk_disp = models.TextField(db_column='TRK_DISP', blank=True, null=True)  # Field name made lowercase.
    trk_id = models.TextField(db_column='TRK_ID', blank=True, null=True)  # Field name made lowercase.
    trk_mobdiag_indic = models.TextField(db_column='TRK_MOBDIAG_INDIC', blank=True, null=True)  # Field name made lowercase.
    trk_term = models.TextField(db_column='TRK_TERM', blank=True, null=True)  # Field name made lowercase.
    trk_type = models.TextField(db_column='TRK_TYPE', blank=True, null=True)  # Field name made lowercase.
    trk_ware = models.TextField(db_column='TRK_WARE', blank=True, null=True)  # Field name made lowercase.
    tsprequest = models.TextField(db_column='TSPREQUEST', blank=True, null=True)  # Field name made lowercase.
    ttl_cost_all_reps = models.TextField(db_column='TTL_COST_ALL_REPS', blank=True, null=True)  # Field name made lowercase.
    tt_state = models.TextField(db_column='TT_STATE', blank=True, null=True)  # Field name made lowercase.
    type_of_service = models.TextField(db_column='TYPE_OF_SERVICE', blank=True, null=True)  # Field name made lowercase.
    veh_id_nr = models.TextField(db_column='VEH_ID_NR', blank=True, null=True)  # Field name made lowercase.
    virt_stat = models.TextField(db_column='VIRT_STAT', blank=True, null=True)  # Field name made lowercase.
    driver10 = models.FloatField(db_column='DRIVER10', blank=True, null=True)  # Field name made lowercase.
    elapsedtime = models.TextField(db_column='ELAPSEDTIME', blank=True, null=True)  # Field name made lowercase.
    event_type = models.TextField(db_column='EVENT_TYPE', blank=True, null=True)  # Field name made lowercase.
    id_primary = models.IntegerField(db_column='ID_PRIMARY', blank=True, null=True)  # Field name made lowercase.
    identifier = models.TextField(db_column='IDENTIFIER', blank=True, null=True)  # Field name made lowercase.
    new_fields_date_updated = models.DateTimeField(db_column='NEW_FIELDS_DATE_UPDATED', blank=True, null=True)  # Field name made lowercase.
    service_provider = models.TextField(db_column='SERVICE_PROVIDER', blank=True, null=True)  # Field name made lowercase.
    totclubs = models.TextField(db_column='TOTCLUBS', blank=True, null=True)  # Field name made lowercase.
    truck = models.TextField(db_column='TRUCK', blank=True, null=True)  # Field name made lowercase.
    directional_error = models.CharField(db_column='DIRECTIONAL_ERROR', max_length=255, blank=True, null=True)  # Field name made lowercase.
    reroute = models.IntegerField(db_column='REROUTE', blank=True, null=True)  # Field name made lowercase.
    remove = models.IntegerField(db_column='REMOVE')  # Field name made lowercase.
    fleet_supervisor = models.IntegerField(db_column='FLEET_SUPERVISOR', blank=True, null=True)  # Field name made lowercase.
    extra_cols_key = models.IntegerField(db_column='EXTRA_COLS_KEY', blank=True, null=True)  # Field name made lowercase.
    clearing_code = models.CharField(db_column='CLEARING_CODE', max_length=100, blank=True, null=True)  # Field name made lowercase.
    first_spot_id = models.CharField(db_column='FIRST_SPOT_ID', max_length=100, blank=True, null=True)  # Field name made lowercase.
    lost_call = models.IntegerField(db_column='LOST_CALL', blank=True, null=True)  # Field name made lowercase.
    field_rep_aaa_emp_num = models.CharField(db_column='FIELD_REP_AAA_EMP_NUM', max_length=100, blank=True, null=True)  # Field name made lowercase.
    field_rep_name = models.CharField(db_column='FIELD_REP_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    duplicate = models.IntegerField(db_column='DUPLICATE_CALL', blank=True, null=True)  # Field name made lowercase.
    reroute_360 = models.IntegerField(db_column='REROUTE_360', blank=True, null=True)  # Field name made lowercase.
    first_spot_delay = models.IntegerField(db_column='FIRST_SPOT_DELAY', blank=True, null=True)  # Field name made lowercase.
    sister_reroute = models.IntegerField(db_column='SISTER_REROUTE', blank=True, null=True)  # Field name made lowercase.
    appeals_request_id = models.IntegerField(db_column='APPEALS_REQUEST_ID', blank=True, null=True)  # Field name made lowercase.
    is_valid_record = models.BooleanField(db_column='IS_VALID_RECORD', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'std12e_reduced'
        unique_together = (('sc_id_surveys', 'sc_dt_surveys', 'sc_comm_ctr_sub'),)

# Does not have year, aca has year (breaking surveys)
class Std12ETiers(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    bottom = models.FloatField(null=True, blank=True)
    top = models.FloatField(null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    metrics = models.CharField(max_length=255, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'dashboard_std12etiers'

class Std12ETierTimePeriods(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    recorded_cutoff = models.DateField(null=True, blank=True)
    recorded_cutoff_time = models.DateTimeField(null=True, blank=True)
    show_until = models.DateField(null=True, blank=True)

    def auto_fill_show(self):
        import datetime as dt
        if self.type == 'csn':
            self.show_surveys = self.recorded_cutoff + dt.timedelta(days=15)
        if self.type == 'fleet':
            self.show_surveys = self.recorded_cutoff + dt.timedelta(days=15)
        super(Std12ETierTimePeriods, self).save()
        return self.recorded_cutoff

    def save(self, *args, **kwargs):
        if self.show_surveys is None and self.recorded_cutoff is not None:
            self.auto_fill_show()
        return super(Std12ETierTimePeriods, self).save(*args, **kwargs)

class CommentsSurveysE(models.Model):
    survey = models.ForeignKey(Std12EReduced, null=True, blank=True, on_delete=models.SET_NULL, related_name='survey_e_comments')
    tokenized_comment = models.TextField(blank=True, null=True)
    sentiment = models.FloatField(blank=True, null=True)
    topics_string = models.TextField(blank=True, null=True)

class CommentTopics(models.Model):
    comment = models.TextField(blank=True, null=True)
    sentiment = models.FloatField(blank=True, null=True)
    survey = models.ForeignKey(Std12EReduced, null=True, blank=True, on_delete=models.SET_NULL, related_name='survey_e_comment_topics')
    topic = models.TextField(blank=True, null=True)

#my dashboard


class DashboardAggregations(models.Model):
    sc_dt = models.DateTimeField(db_column='SC_DT', blank=True, null=True)  # Field name made lowercase.
    organization = models.ForeignKey(Organization, db_column='ORGANIZATION_ID', blank=True, on_delete=models.SET_NULL, null=True, related_name='dashboard_organization')  # Field name made lowercase.
    employee = models.ForeignKey(Employee, db_column='EMPLOYEE_ID',  blank=True, on_delete=models.SET_NULL, null=True, related_name='raw_ops_svc_facl_id')  # Field name made lowercase.
    time_type = models.CharField(db_column='TIME_TYPE', max_length=10, blank=True, null=True)  # Field name made lowercase.
    id_name_helper = models.CharField(db_column='ID_NAME_HELPER', max_length=255, blank=True, null=True)  # Field name made lowercase.
    index_type = models.TextField(db_column='INDEX_TYPE', blank=True, null=True)  # Field name made lowercase.
    parent_id = models.FloatField(db_column='PARENT_ID', blank=True, null=True)  # Field name made lowercase.
    week_day = models.CharField(db_column='WEEK_DAY', max_length=20, blank=True, null=True)  # Field name made lowercase.
    updated = models.DateTimeField(db_column='UPDATED', blank=True, null=True)  # Field name made lowercase.
    all_volume = models.BigIntegerField(db_column='ALL_VOLUME', blank=True, null=True)  # Field name made lowercase.
    ata_median = models.FloatField(db_column='ATA_MEDIAN', blank=True, null=True)  # Field name made lowercase.
    ata_minus_pta_median = models.FloatField(db_column='ATA_MINUS_PTA_MEDIAN', blank=True, null=True)  # Field name made lowercase.
    base_cost_avg = models.FloatField(db_column='BASE_COST_AVG', blank=True, null=True)  # Field name made lowercase.
    base_cost_sum = models.FloatField(db_column='BASE_COST_SUM', blank=True, null=True)  # Field name made lowercase.
    battery_volume = models.DecimalField(db_column='BATTERY_VOLUME', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    batt_call_count = models.DecimalField(db_column='BATT_CALL_COUNT', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    batt_test_on_batt_call_count = models.DecimalField(db_column='BATT_TEST_ON_BATT_CALL_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    batt_test_on_batt_call_freq = models.DecimalField(db_column='BATT_TEST_ON_BATT_CALL_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    call_accepted_count = models.DecimalField(db_column='CALL_ACCEPTED_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    call_cost_avg = models.FloatField(db_column='CALL_COST_AVG', blank=True, null=True)  # Field name made lowercase.
    call_cost_sum = models.FloatField(db_column='CALL_COST_SUM', blank=True, null=True)  # Field name made lowercase.
    cancelled_count = models.DecimalField(db_column='CANCELLED_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    cancelled_freq = models.DecimalField(db_column='CANCELLED_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    early_count = models.DecimalField(db_column='EARLY_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    early_freq = models.DecimalField(db_column='EARLY_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    enroute_cost_avg = models.FloatField(db_column='ENROUTE_COST_AVG', blank=True, null=True)  # Field name made lowercase.
    enroute_cost_sum = models.FloatField(db_column='ENROUTE_COST_SUM', blank=True, null=True)  # Field name made lowercase.
    eta_update_avg = models.DecimalField(db_column='ETA_UPDATE_AVG', max_digits=23, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    failed_batt_test_on_batt_call = models.DecimalField(db_column='FAILED_BATT_TEST_ON_BATT_CALL', max_digits=24, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    g_to_g_count = models.DecimalField(db_column='G_TO_G_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    g_to_g_freq = models.DecimalField(db_column='G_TO_G_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    g_to_ng_count = models.DecimalField(db_column='G_TO_NG_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    g_to_ng_freq = models.DecimalField(db_column='G_TO_NG_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    late_count = models.DecimalField(db_column='LATE_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    late_freq = models.DecimalField(db_column='LATE_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    long_ata_count = models.DecimalField(db_column='LONG_ATA_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    long_ata_freq = models.DecimalField(db_column='LONG_ATA_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    ng_to_g_count = models.DecimalField(db_column='NG_TO_G_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    ng_to_g_freq = models.DecimalField(db_column='NG_TO_G_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    ng_to_ng_count = models.DecimalField(db_column='NG_TO_NG_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    ng_to_ng_freq = models.DecimalField(db_column='NG_TO_NG_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    not_tow_volume = models.DecimalField(db_column='NOT_TOW_VOLUME', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    no_service_rendered_count = models.DecimalField(db_column='NO_SERVICE_RENDERED_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    no_service_rendered_freq = models.DecimalField(db_column='NO_SERVICE_RENDERED_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    on_time_count = models.DecimalField(db_column='ON_TIME_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    on_time_freq = models.DecimalField(db_column='ON_TIME_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    pass_batt_test_count = models.DecimalField(db_column='PASS_BATT_TEST_COUNT', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    pta_median = models.FloatField(db_column='PTA_MEDIAN', blank=True, null=True)  # Field name made lowercase.
    replaced_batt_on_failed_batt_call_count = models.DecimalField(db_column='REPLACED_BATT_ON_FAILED_BATT_CALL_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    replaced_batt_on_failed_batt_call_freq = models.DecimalField(db_column='REPLACED_BATT_ON_FAILED_BATT_CALL_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    reroute_freq = models.DecimalField(db_column='REROUTE_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    short_freq = models.DecimalField(db_column='SHORT_FREQ', max_digits=8, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    tow_cost_avg = models.FloatField(db_column='TOW_COST_AVG', blank=True, null=True)  # Field name made lowercase.
    tow_cost_sum = models.FloatField(db_column='TOW_COST_SUM', blank=True, null=True)  # Field name made lowercase.
    tow_volume = models.DecimalField(db_column='TOW_VOLUME', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    volume = models.DecimalField(db_column='VOLUME', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_facility_sat_avg = models.FloatField(db_column='AAA_MGMT_ANY_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_facility_sat_count = models.BigIntegerField(db_column='AAA_MGMT_ANY_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_facility_sat_sum = models.FloatField(db_column='AAA_MGMT_ANY_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_kept_informed_sat_avg = models.FloatField(db_column='AAA_MGMT_ANY_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_kept_informed_sat_count = models.BigIntegerField(db_column='AAA_MGMT_ANY_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_kept_informed_sat_sum = models.FloatField(db_column='AAA_MGMT_ANY_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_overall_sat_avg = models.FloatField(db_column='AAA_MGMT_ANY_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_overall_sat_count = models.BigIntegerField(db_column='AAA_MGMT_ANY_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_overall_sat_sum = models.BigIntegerField(db_column='AAA_MGMT_ANY_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_request_service_sat_avg = models.FloatField(db_column='AAA_MGMT_ANY_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_request_service_sat_count = models.BigIntegerField(db_column='AAA_MGMT_ANY_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_request_service_sat_sum = models.FloatField(db_column='AAA_MGMT_ANY_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_response_sat_avg = models.FloatField(db_column='AAA_MGMT_ANY_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_response_sat_count = models.BigIntegerField(db_column='AAA_MGMT_ANY_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_any_response_sat_sum = models.FloatField(db_column='AAA_MGMT_ANY_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_facility_sat_avg = models.FloatField(db_column='AAA_MGMT_BATTERY_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_facility_sat_count = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_facility_sat_sum = models.FloatField(db_column='AAA_MGMT_BATTERY_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_kept_informed_sat_avg = models.FloatField(db_column='AAA_MGMT_BATTERY_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_kept_informed_sat_count = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_kept_informed_sat_sum = models.FloatField(db_column='AAA_MGMT_BATTERY_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_overall_sat_avg = models.FloatField(db_column='AAA_MGMT_BATTERY_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_overall_sat_count = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_overall_sat_sum = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_request_service_sat_avg = models.FloatField(db_column='AAA_MGMT_BATTERY_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_request_service_sat_count = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_request_service_sat_sum = models.FloatField(db_column='AAA_MGMT_BATTERY_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_response_sat_avg = models.FloatField(db_column='AAA_MGMT_BATTERY_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_response_sat_count = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_response_sat_sum = models.FloatField(db_column='AAA_MGMT_BATTERY_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_facility_sat_avg = models.FloatField(db_column='AAA_MGMT_NOT_TOW_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_facility_sat_count = models.BigIntegerField(db_column='AAA_MGMT_NOT_TOW_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_facility_sat_sum = models.FloatField(db_column='AAA_MGMT_NOT_TOW_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_kept_informed_sat_avg = models.FloatField(db_column='AAA_MGMT_NOT_TOW_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_kept_informed_sat_count = models.BigIntegerField(db_column='AAA_MGMT_NOT_TOW_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_kept_informed_sat_sum = models.FloatField(db_column='AAA_MGMT_NOT_TOW_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_overall_sat_avg = models.FloatField(db_column='AAA_MGMT_NOT_TOW_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_overall_sat_count = models.BigIntegerField(db_column='AAA_MGMT_NOT_TOW_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_overall_sat_sum = models.BigIntegerField(db_column='AAA_MGMT_NOT_TOW_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_request_service_sat_avg = models.FloatField(db_column='AAA_MGMT_NOT_TOW_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_request_service_sat_count = models.BigIntegerField(db_column='AAA_MGMT_NOT_TOW_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_request_service_sat_sum = models.FloatField(db_column='AAA_MGMT_NOT_TOW_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_response_sat_avg = models.FloatField(db_column='AAA_MGMT_NOT_TOW_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_response_sat_count = models.BigIntegerField(db_column='AAA_MGMT_NOT_TOW_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_not_tow_response_sat_sum = models.FloatField(db_column='AAA_MGMT_NOT_TOW_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_facility_sat_avg = models.FloatField(db_column='AAA_MGMT_TOW_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_facility_sat_count = models.BigIntegerField(db_column='AAA_MGMT_TOW_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_facility_sat_sum = models.FloatField(db_column='AAA_MGMT_TOW_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_kept_informed_sat_avg = models.FloatField(db_column='AAA_MGMT_TOW_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_kept_informed_sat_count = models.BigIntegerField(db_column='AAA_MGMT_TOW_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_kept_informed_sat_sum = models.FloatField(db_column='AAA_MGMT_TOW_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_overall_sat_avg = models.FloatField(db_column='AAA_MGMT_TOW_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_overall_sat_count = models.BigIntegerField(db_column='AAA_MGMT_TOW_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_overall_sat_sum = models.BigIntegerField(db_column='AAA_MGMT_TOW_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_request_service_sat_avg = models.FloatField(db_column='AAA_MGMT_TOW_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_request_service_sat_count = models.BigIntegerField(db_column='AAA_MGMT_TOW_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_request_service_sat_sum = models.FloatField(db_column='AAA_MGMT_TOW_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_response_sat_avg = models.FloatField(db_column='AAA_MGMT_TOW_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_response_sat_count = models.BigIntegerField(db_column='AAA_MGMT_TOW_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_tow_response_sat_sum = models.FloatField(db_column='AAA_MGMT_TOW_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_any_facility_sat_avg = models.FloatField(db_column='COMP_ANY_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_any_facility_sat_count = models.BigIntegerField(db_column='COMP_ANY_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_any_facility_sat_sum = models.FloatField(db_column='COMP_ANY_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_any_kept_informed_sat_avg = models.FloatField(db_column='COMP_ANY_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_any_kept_informed_sat_count = models.BigIntegerField(db_column='COMP_ANY_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_any_kept_informed_sat_sum = models.FloatField(db_column='COMP_ANY_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_any_overall_sat_avg = models.FloatField(db_column='COMP_ANY_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_any_overall_sat_count = models.BigIntegerField(db_column='COMP_ANY_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_any_overall_sat_sum = models.BigIntegerField(db_column='COMP_ANY_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_any_request_service_sat_avg = models.FloatField(db_column='COMP_ANY_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_any_request_service_sat_count = models.BigIntegerField(db_column='COMP_ANY_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_any_request_service_sat_sum = models.FloatField(db_column='COMP_ANY_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_any_response_sat_avg = models.FloatField(db_column='COMP_ANY_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_any_response_sat_count = models.BigIntegerField(db_column='COMP_ANY_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_any_response_sat_sum = models.FloatField(db_column='COMP_ANY_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_battery_facility_sat_avg = models.FloatField(db_column='COMP_BATTERY_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_battery_facility_sat_count = models.BigIntegerField(db_column='COMP_BATTERY_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_battery_facility_sat_sum = models.FloatField(db_column='COMP_BATTERY_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_battery_kept_informed_sat_avg = models.FloatField(db_column='COMP_BATTERY_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_battery_kept_informed_sat_count = models.BigIntegerField(db_column='COMP_BATTERY_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_battery_kept_informed_sat_sum = models.FloatField(db_column='COMP_BATTERY_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_battery_overall_sat_avg = models.FloatField(db_column='COMP_BATTERY_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_battery_overall_sat_count = models.BigIntegerField(db_column='COMP_BATTERY_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_battery_overall_sat_sum = models.BigIntegerField(db_column='COMP_BATTERY_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_battery_request_service_sat_avg = models.FloatField(db_column='COMP_BATTERY_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_battery_request_service_sat_count = models.BigIntegerField(db_column='COMP_BATTERY_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_battery_request_service_sat_sum = models.FloatField(db_column='COMP_BATTERY_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_battery_response_sat_avg = models.FloatField(db_column='COMP_BATTERY_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_battery_response_sat_count = models.BigIntegerField(db_column='COMP_BATTERY_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_battery_response_sat_sum = models.FloatField(db_column='COMP_BATTERY_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_facility_sat_avg = models.FloatField(db_column='COMP_NOT_TOW_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_facility_sat_count = models.BigIntegerField(db_column='COMP_NOT_TOW_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_facility_sat_sum = models.FloatField(db_column='COMP_NOT_TOW_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_kept_informed_sat_avg = models.FloatField(db_column='COMP_NOT_TOW_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_kept_informed_sat_count = models.BigIntegerField(db_column='COMP_NOT_TOW_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_kept_informed_sat_sum = models.FloatField(db_column='COMP_NOT_TOW_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_overall_sat_avg = models.FloatField(db_column='COMP_NOT_TOW_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_overall_sat_count = models.BigIntegerField(db_column='COMP_NOT_TOW_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_overall_sat_sum = models.BigIntegerField(db_column='COMP_NOT_TOW_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_request_service_sat_avg = models.FloatField(db_column='COMP_NOT_TOW_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_request_service_sat_count = models.BigIntegerField(db_column='COMP_NOT_TOW_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_request_service_sat_sum = models.FloatField(db_column='COMP_NOT_TOW_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_response_sat_avg = models.FloatField(db_column='COMP_NOT_TOW_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_response_sat_count = models.BigIntegerField(db_column='COMP_NOT_TOW_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_not_tow_response_sat_sum = models.FloatField(db_column='COMP_NOT_TOW_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_tow_facility_sat_avg = models.FloatField(db_column='COMP_TOW_FACILITY_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_tow_facility_sat_count = models.BigIntegerField(db_column='COMP_TOW_FACILITY_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_tow_facility_sat_sum = models.FloatField(db_column='COMP_TOW_FACILITY_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_tow_kept_informed_sat_avg = models.FloatField(db_column='COMP_TOW_KEPT_INFORMED_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_tow_kept_informed_sat_count = models.BigIntegerField(db_column='COMP_TOW_KEPT_INFORMED_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_tow_kept_informed_sat_sum = models.FloatField(db_column='COMP_TOW_KEPT_INFORMED_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_tow_overall_sat_avg = models.FloatField(db_column='COMP_TOW_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_tow_overall_sat_count = models.BigIntegerField(db_column='COMP_TOW_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_tow_overall_sat_sum = models.BigIntegerField(db_column='COMP_TOW_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_tow_request_service_sat_avg = models.FloatField(db_column='COMP_TOW_REQUEST_SERVICE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_tow_request_service_sat_count = models.BigIntegerField(db_column='COMP_TOW_REQUEST_SERVICE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_tow_request_service_sat_sum = models.FloatField(db_column='COMP_TOW_REQUEST_SERVICE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_tow_response_sat_avg = models.FloatField(db_column='COMP_TOW_RESPONSE_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_tow_response_sat_count = models.BigIntegerField(db_column='COMP_TOW_RESPONSE_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_tow_response_sat_sum = models.FloatField(db_column='COMP_TOW_RESPONSE_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    facility_type = models.CharField(db_column='FACILITY_TYPE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    reroute_sum = models.IntegerField(db_column='REROUTE_SUM', blank=True, null=True)  # Field name made lowercase.
    reroute_avg = models.FloatField(db_column='REROUTE_AVG', blank=True, null=True)  # Field name made lowercase.
    survey_count = models.BigIntegerField(db_column='SURVEY_COUNT', blank=True, null=True)  # Field name made lowercase.
    fac_type_parent_id = models.BigIntegerField(db_column='FAC_TYPE_PARENT_ID', blank=True, null=True)  # Field name made lowercase.
    field_rep_name = models.IntegerField(db_column='APPROXIMATE_BATTERY_REVENUE', blank=True, null=True)
    ata_under_45_count = models.IntegerField(db_column='ATA_UNDER_45_COUNT', blank=True, null=True)
    ata_under_45_freq = models.FloatField(db_column='ATA_UNDER_45_FREQ', blank=True, null=True)
    battery_ol_to_clr_avg = models.FloatField(db_column='BATTERY_OL_TO_CLR_AVG', blank=True, null=True)
    battery_ol_to_clr_count = models.IntegerField(db_column='BATTERY_OL_TO_CLR', blank=True, null=True)
    battery_opp_ata_avg = models.FloatField(db_column='BATTERY_OPP_ATA_AVG', blank=True, null=True)
    battery_opp_ata = models.FloatField(db_column='BATTERY_OPP_ATA', blank=True, null=True)
    battery_replacement_freq = models.FloatField(db_column='BATTERY_REPLACEMENT_FREQ', blank=True, null=True)
    battery_replacement_paid_freq = models.FloatField(db_column='BATTERY_REPLACEMENT_PAID_PCNT', blank=True, null=True)
    battery_replacement_count = models.IntegerField(db_column='BATTERY_REPLACEMENT_VOLUME', blank=True, null=True)
    paid_call_count = models.IntegerField(db_column='PAID_CALL_COUNT', blank=True, null=True)
    light_svc_volume = models.IntegerField(db_column='LIGHT_SVC_VOLUME', blank=True, null=True)
    passed_calls_freq = models.IntegerField(db_column='PASSED_CALLS_FREQ', blank=True, null=True)
    passed_calls_freq_3m = models.IntegerField(db_column='passed_calls_freq_3m', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'dashboard_aggregations'
        unique_together = (('organization', 'employee', 'sc_dt', 'time_type'), ('employee', 'organization', 'sc_dt', 'time_type'),)

class DashboardUpdateHistory(models.Model):
    date_updated = models.DateTimeField()
    notes = models.TextField()


# scheduler

class TimeseriesPredictionsHourly(models.Model):
    id = models.BigIntegerField(db_column='id', primary_key=True, unique=True)
    sc_dt = models.DateTimeField(db_column='SC_DT', null=True, blank=True)
    organization_id = models.FloatField(db_column='ORGANIZATION_ID', null=True, blank=True)
    volume_pred = models.FloatField(db_column='VOLUME_PRED', null=True, blank=True)
    actual_volume = models.FloatField(db_column='ACTUAL_VOLUME', null=True, blank=True)
    volume_pred_lower = models.FloatField(db_column='VOLUME_PRED_LOWER', null=True, blank=True)
    volume_pred_upper = models.FloatField(db_column='VOLUME_PRED_UPPER', null=True, blank=True)
    date_predicted = models.CharField(db_column='DATE_PREDICTED', max_length=255, null=True, blank=True)
    code = models.CharField(db_column='TROUBLE_CODE', max_length=255, null=True, blank=True)
    today = models.FloatField(db_column='TODAY_TOTAL_VOLUME', null=True, blank=True)

    def calls_per_hour_per_driver_foo(self):
        calls = random.randrange(0, 20, 1) / 10
        return 2

    class Meta:
        managed = False
        db_table = 'TIMESERIES_4HOUR_CODE'
        index_together = (
            ('organization_id', 'sc_dt'),
        )

class TimeseriesPredictionsHistory(models.Model):
    id = models.BigIntegerField(db_column='id', primary_key=True, unique=True)
    sc_dt = models.DateTimeField(db_column='SC_DT', null=True, blank=True)
    volume_pred = models.FloatField(db_column='VOLUME_PRED', null=True, blank=True)
    volume_pred_upper = models.FloatField(db_column='VOLUME_PRED_UPPER', null=True, blank=True)
    volume_pred_lower = models.FloatField(db_column='VOLUME_PRED_LOWER', null=True, blank=True)
    actual_volume = models.FloatField(db_column='ACTUAL_VOLUME', null=True, blank=True)
    code = models.CharField(db_column='TROUBLE_CODE', max_length=255, null=True, blank=True)
    date_pred = models.DateField(db_column='DATE_PREDICTED', null=True, blank=True)
    organization_id = models.FloatField(db_column='ORGANIZATION_ID', null=True, blank=True)
    today = models.FloatField(db_column='TODAY_TOTAL_VOLUME', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'TIMESERIES_HISTORICAL_HOURLY'

class TimeseriesPredictionsByHour(models.Model):
    id = models.BigIntegerField(db_column='id', primary_key=True, unique=True)
    sc_dt = models.DateTimeField(db_column='SC_DT', null=True, blank=True)
    volume_pred = models.FloatField(db_column='VOLUME_PRED', null=True, blank=True)
    actual_volume = models.FloatField(db_column='ACTUAL_VOLUME', null=True, blank=True)
    code = models.CharField(db_column='TROUBLE_CODE', max_length=255, null=True, blank=True)
    date_pred = models.DateField(db_column='DATE_PREDICTED', null=True, blank=True)
    organization_id = models.FloatField(db_column='ORGANIZATION_ID', null=True, blank=True)
    was_optimized = models.BooleanField(null=True)
    productivity = models.FloatField(db_column='PRODUCTIVITY', null=True, blank=True)
    drivers_needed = models.BigIntegerField(db_column='DRIVERS_NEEDED', null=True, blank=True)
    rollover_hour_minus_one = models.BigIntegerField(db_column='rollover_hour_minus_one', null=True, blank=True)
    rollover_hour_minus_two = models.BigIntegerField(db_column='rollover_hour_minus_two', null=True, blank=True)
    rollover_hour_minus_three = models.BigIntegerField(db_column='rollover_hour_minus_three', null=True, blank=True)
    waiters = models.BigIntegerField(db_column='waiters', null=True, blank=True)
    new_drivers_needed = models.BigIntegerField(db_column='new_drivers_needed', null=True, blank=True)
    send_home = models.BigIntegerField(db_column='send_home', null=True, blank=True)
    call_time = models.FloatField(db_column='call_time', null=True, blank=True)
    total_drivers = models.BigIntegerField(db_column='total_drivers', null=True, blank=True)
    today = models.FloatField(db_column='TODAY_TOTAL_VOLUME', null=True, blank=True)

    def calls_per_hour_per_driver_foo(self):
        calls = random.randrange(0, 20, 1) / 10
        return 2

    class Meta:
        managed = False
        db_table = 'TIMESERIES_HOUR_CODE'
        index_together = (
            ('organization_id', 'sc_dt'),
        )

class TimeseriesScheduledDrivers(models.Model):
    employee = models.ForeignKey(Employee, related_name='scheduled_driver', on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateTimeField(auto_now=False, auto_now_add=False)
    duration = models.IntegerField(null=True, blank=True)
    schedule = models.ForeignKey('TimeseriesSchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='scheduled_drivers')
    end_date = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    schedule_type = models.CharField(max_length=225, null=True, blank=True)
    placeholder = models.ForeignKey('PlaceholderDriver', null=True, blank=True, on_delete=models.SET_NULL)
    lunch_time = models.DateTimeField(auto_now=False,auto_now_add=False, null=True, blank=True)
    zone = models.CharField(max_length=255, null=True, blank=True)
    truck = models.CharField(max_length=255, null=True, blank=True)
    truck_type = models.CharField(max_length=255, null=True, blank=True)

    def get_driver_name(self):
        if self.employee is not None:
            name = '{0} {1}'.format(self.employee.first_name, self.employee.last_name)
        else:
            try:
                name = self.placeholder.name
            except Exception as e:
                print(e)
                print('problem is', self.id)
                return "Missing Name"

        return name

    class Meta:
        db_table = 'dashboard_timeseriesscheduleddrivers'
        unique_together = (('employee', 'schedule'))



class TimeseriesSchedule(models.Model):
    organization_id = models.FloatField(null=True, blank=True)
    date = models.DateField(auto_now=False, auto_now_add=False)
    publish = models.BooleanField(default=False)

    def get_scheduled_drivers(self):
        drivers = TimeseriesScheduledDrivers.objects.filter(schedule=self)
        return drivers

    def count_scheduled_drivers(self):
        return self.get_scheduled_drivers().count()

    def get_all_predicted_calls(self):
        predictions = TimeseriesPredictionsHourly.objects.filter(organization_id=self.organization_id, sc_dt=self.date)
        if predictions.count() == 0:
            predictions = TimeseriesPredictionsHistory.objects.filter(organization_id=self.organization_id, sc_dt__contains=self.date)
        return predictions
    class Meta:
        db_table = 'dashboard_timeseriesschedule'
        index_together = (
            ('organization_id', 'date'),
        )

class TimeseriesScheduleTemplate(models.Model):
    organization_id = models.FloatField(null=True, blank=True)
    date_saved = models.DateField(auto_now=True)
    template_name = models.CharField(max_length=255, default='Default', null=True, blank=True)

class TimeseriesScheduledDiversTemplate(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, blank=True, null=True)
    template = models.ForeignKey(TimeseriesScheduleTemplate, on_delete=models.CASCADE, related_name='drivers_template', blank=True, null=True)
    day_of_week = models.CharField(max_length=20, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    schedule_type = models.CharField(max_length=255, null=True, blank=True)

class TimeseriesExpectations(models.Model):
    organization_id = models.FloatField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    def total_calls(self):
        calls = TimeseriesPredictionsByHour.objects.filter(
            organization_id=self.organization_id,
            sc_dt__gte=self.date,
            sc_dt__lt=self.date + dt.timedelta(days=1))\
            .annotate(date=Cast('sc_dt', models.DateTimeField()))\
            .values('date')\
            .annotate(total_pred=Sum('volume_pred')).values('total_pred', 'sc_dt')
        return list(calls)

    def total_drivers(self):
        schedule = TimeseriesSchedule.objects.get_or_create(organization_id=self.organization_id, date=self.date)[0]
        drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)\
            .annotate(date=Cast('start_date', models.DateTimeField()))\
            .values('date').annotate(total_drivers=Count('employee'))
        return drivers

class PlaceholderDriver(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    service_type = models.CharField(max_length=255, null=True, blank=True)
    sun_start = models.TimeField(null=True, blank=True)
    sun_end = models.TimeField(null=True, blank=True)
    mon_start = models.TimeField(null=True, blank=True)
    mon_end = models.TimeField(null=True, blank=True)
    tue_start = models.TimeField(null=True, blank=True)
    tue_end = models.TimeField(null=True, blank=True)
    wed_start = models.TimeField(null=True, blank=True)
    wed_end = models.TimeField(null=True, blank=True)
    thu_start = models.TimeField(null=True, blank=True)
    thu_end = models.TimeField(null=True, blank=True)
    fri_start = models.TimeField(null=True, blank=True)
    fri_end = models.TimeField(null=True, blank=True)
    sat_start = models.TimeField(null=True, blank=True)
    sat_end = models.TimeField(null=True, blank=True)
    sun_available = models.BooleanField(default=True)
    mon_available = models.BooleanField(default=True)
    tue_available = models.BooleanField(default=True)
    wed_available = models.BooleanField(default=True)
    thu_available = models.BooleanField(default=True)
    fri_available = models.BooleanField(default=True)
    sat_available = models.BooleanField(default=True)

class SchedulerReviewByDriver(models.Model):
    employee = models.ForeignKey(Employee,db_column='EMP_DRIVER_ID', null=True, blank=True, on_delete=models.SET_NULL, related_name='schedulerReivew')
    date = models.DateField(null=True, blank=True)
    starting_time = models.DateTimeField(null=True, blank=True)
    ending_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    tcd = models.CharField(null=True, blank=True, max_length=225)
    off = models.BooleanField(null=True, blank=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name='schedulerReivew')
    placeholder = models.ForeignKey(PlaceholderDriver, null=True, blank=True, on_delete=models.SET_NULL, related_name='ghost_driver_scheduled')

class TimeseriesPredictionsByHourNew(models.Model):
    sc_dt = models.DateTimeField(db_column='SC_DT', null=True, blank=True)
    volume_pred = models.FloatField(db_column='VOLUME_PRED', null=True, blank=True)
    actual_volume = models.FloatField(db_column='ACTUAL_VOLUME', null=True, blank=True)
    code = models.CharField(db_column='TCD', max_length=255, null=True, blank=True)
    date_pred = models.DateTimeField(db_column='DATE_PREDICTED', null=True, blank=True)
    organization_id = models.FloatField(db_column='ORGANIZATION_ID', null=True, blank=True)
    was_optimized = models.BooleanField(null=True, db_column='WAS_OPTIMIZED')
    productivity = models.FloatField(db_column='PRODUCTIVITY', null=True, blank=True)
    drivers_needed = models.BigIntegerField(db_column='DRIVERS_NEEDED', null=True, blank=True)
    rollover_hour_minus_one = models.BigIntegerField(db_column='rollover_hour_minus_one', null=True, blank=True)
    rollover_hour_minus_two = models.BigIntegerField(db_column='rollover_hour_minus_two', null=True, blank=True)
    rollover_hour_minus_three = models.BigIntegerField(db_column='rollover_hour_minus_three', null=True, blank=True)
    waiters = models.BigIntegerField(db_column='waiters', null=True, blank=True)
    new_drivers_needed = models.BigIntegerField(db_column='new_drivers_needed', null=True, blank=True)
    send_home = models.BigIntegerField(db_column='send_home', null=True, blank=True)
    call_time = models.FloatField(db_column='call_time', null=True, blank=True)
    total_drivers = models.BigIntegerField(db_column='total_drivers', null=True, blank=True)
    today = models.FloatField(db_column='TODAY_TOTAL_VOLUME', null=True, blank=True)
    org_type = models.CharField(db_column='ORG_TYPE', max_length=255, null=True, blank=True)
    active_holidays = models.BooleanField(null=True, db_column='ACTIVE_HOLIDAYS', blank=True)
    active_weather = models.BooleanField(null=True, db_column='ACTIVE_WEATHER', blank=True)
    holiday_impacts = models.FloatField(db_column='HOLIDAY_IMPACTS', null=True, blank=True)
    weather_impacts = models.FloatField(db_column='WEATHER_IMPACTS', null=True, blank=True)
    time_type = models.CharField(db_column='TIME_TYPE', max_length=255, null=True, blank=True)
    total_drivers_wait_15 = models.BigIntegerField(db_column='total_drivers_wait_15', null=True, blank=True)


    class Meta:
        db_table = 'dashboard_timeseriespredictionsbyhournew'
        # db_table = 'dashboard_timeseriespredictionsbyhourswapTimeWindows'
        index_together = (
            ('organization_id', 'sc_dt'),
        )

class TimeseriesPredictionsOrgsPredicted(models.Model):
    id = models.IntegerField(db_column='id', primary_key=True)
    organization = models.IntegerField(db_column='organization_id')
    time_type = models.CharField(db_column='time_type', max_length=255, null=True, blank=True)
    org_name = models.CharField(db_column='name', max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'predicted_stations'
        managed = False

class TimeseriesPredictionsByHourSwap(models.Model):
    sc_dt = models.DateTimeField(db_column='SC_DT', null=True, blank=True)
    volume_pred = models.FloatField(db_column='VOLUME_PRED', null=True, blank=True)
    actual_volume = models.FloatField(db_column='ACTUAL_VOLUME', null=True, blank=True)
    code = models.CharField(db_column='TCD', max_length=255, null=True, blank=True)
    date_pred = models.DateTimeField(db_column='DATE_PREDICTED', null=True, blank=True)
    organization_id = models.FloatField(db_column='ORGANIZATION_ID', null=True, blank=True)
    was_optimized = models.BooleanField(null=True, db_column='WAS_OPTIMIZED')
    productivity = models.FloatField(db_column='PRODUCTIVITY', null=True, blank=True)
    drivers_needed = models.BigIntegerField(db_column='DRIVERS_NEEDED', null=True, blank=True)
    rollover_hour_minus_one = models.BigIntegerField(db_column='rollover_hour_minus_one', null=True, blank=True)
    rollover_hour_minus_two = models.BigIntegerField(db_column='rollover_hour_minus_two', null=True, blank=True)
    rollover_hour_minus_three = models.BigIntegerField(db_column='rollover_hour_minus_three', null=True, blank=True)
    waiters = models.BigIntegerField(db_column='waiters', null=True, blank=True)
    new_drivers_needed = models.BigIntegerField(db_column='new_drivers_needed', null=True, blank=True)
    send_home = models.BigIntegerField(db_column='send_home', null=True, blank=True)
    call_time = models.FloatField(db_column='call_time', null=True, blank=True)
    total_drivers = models.BigIntegerField(db_column='total_drivers', null=True, blank=True)
    today = models.FloatField(db_column='TODAY_TOTAL_VOLUME', null=True, blank=True)
    org_type = models.CharField(db_column='ORG_TYPE', max_length=255, null=True, blank=True)
    active_holidays = models.BooleanField(null=True, db_column='ACTIVE_HOLIDAYS', blank=True)
    active_weather = models.BooleanField(null=True, db_column='ACTIVE_WEATHER', blank=True)
    holiday_impacts = models.FloatField(db_column='HOLIDAY_IMPACTS', null=True, blank=True)
    weather_impacts = models.FloatField(db_column='WEATHER_IMPACTS', null=True, blank=True)
    time_type = models.CharField(db_column='TIME_TYPE', max_length=255, null=True, blank=True)

    class Meta:
        index_together = (
            ('organization_id', 'sc_dt'),
        )

class TimeseriesPredictionsByFourHourNew(models.Model):
    sc_dt = models.DateTimeField(db_column='SC_DT', null=True, blank=True)
    volume_pred = models.FloatField(db_column='VOLUME_PRED', null=True, blank=True)
    actual_volume = models.FloatField(db_column='ACTUAL_VOLUME', null=True, blank=True)
    code = models.CharField(db_column='TCD', max_length=255, null=True, blank=True)
    date_pred = models.DateTimeField(db_column='DATE_PREDICTED', null=True, blank=True)
    organization_id = models.FloatField(db_column='ORGANIZATION_ID', null=True, blank=True)
    was_optimized = models.BooleanField(null=True, db_column='WAS_OPTIMIZED')
    productivity = models.FloatField(db_column='PRODUCTIVITY', null=True, blank=True)
    drivers_needed = models.BigIntegerField(db_column='DRIVERS_NEEDED', null=True, blank=True)
    rollover_hour_minus_one = models.BigIntegerField(db_column='rollover_hour_minus_one', null=True, blank=True)
    rollover_hour_minus_two = models.BigIntegerField(db_column='rollover_hour_minus_two', null=True, blank=True)
    rollover_hour_minus_three = models.BigIntegerField(db_column='rollover_hour_minus_three', null=True, blank=True)
    waiters = models.BigIntegerField(db_column='waiters', null=True, blank=True)
    new_drivers_needed = models.BigIntegerField(db_column='new_drivers_needed', null=True, blank=True)
    send_home = models.BigIntegerField(db_column='send_home', null=True, blank=True)
    call_time = models.FloatField(db_column='call_time', null=True, blank=True)
    total_drivers = models.BigIntegerField(db_column='total_drivers', null=True, blank=True)
    today = models.FloatField(db_column='TODAY_TOTAL_VOLUME', null=True, blank=True)
    org_type = models.CharField(db_column='ORG_TYPE', max_length=255, null=True, blank=True)
    active_holidays = models.BooleanField(null=True, db_column='ACTIVE_HOLIDAYS', blank=True)
    active_weather = models.BooleanField(null=True, db_column='ACTIVE_WEATHER', blank=True)
    holiday_impacts = models.FloatField(db_column='HOLIDAY_IMPACTS', null=True, blank=True)
    weather_impacts = models.FloatField(db_column='WEATHER_IMPACTS', null=True, blank=True)

    class Meta:
        index_together = (
            ('organization_id', 'sc_dt'),
        )

#### updated timeseries prediction tables...



## appeals
class Appeals(models.Model):
    service_date = models.DateTimeField(db_column='Service Date', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    call_number = models.CharField(db_column='Call Number', max_length=255, blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    incentive_month = models.BigIntegerField(db_column='incentive month', blank=True, null=True)  # Field renamed to remove unsuitable characters.
    incentive_year = models.BigIntegerField(db_column='incentive year', blank=True, null=True)  # Field renamed to remove unsuitable characters.
    reroutes = models.BigIntegerField(db_column='Reroutes', blank=True, null=True)  # Field name made lowercase.
    removes = models.BigIntegerField(db_column='Removes', blank=True, null=True)  # Field name made lowercase.
    date_added = models.DateTimeField(blank=True, null=True)
    date_modified = models.DateTimeField(blank=True, null=True)
    appeal_type = models.CharField(max_length=5)
    good = models.BooleanField(null=True)

    class Meta:
        managed = False
        db_table = 'appeals'

#check id? remove...?

class Checkidopsraw(models.Model):
    sc_id = models.BigIntegerField(db_column='SC_ID', blank=True, null=True)  # Field name made lowercase.
    call_id = models.CharField(max_length=255, blank=True, null=True)
    sc_dt = models.DateTimeField(db_column='SC_DT', blank=True, null=True)  # Field name made lowercase.
    re_tm = models.DateTimeField(db_column='RE_TM', blank=True, null=True)  # Field name made lowercase.
    fst_ol_time = models.DateTimeField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)
    api_response = models.TextField(blank=True, null=True)
    d3_fname = models.TextField(blank=True, null=True)
    d3_lname = models.TextField(blank=True, null=True)
    fname = models.TextField(blank=True, null=True)
    lname = models.TextField(blank=True, null=True)
    driver_name = models.CharField(max_length=255, blank=True, null=True)
    emp_driver_id = models.FloatField(blank=True, null=True)
    svc_facl_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'CheckIDOpsRaw'


# skills

class SkillLevels(models.Model):
    skill_name = models.TextField(blank=True, null=True)
    level = models.BigIntegerField( blank=True, null=True)  # Field name made lowercase.
    min_value = models.FloatField(blank=True, null=True)
    max_value = models.FloatField(blank=True, null=True)

class SkillLevelsTenureLevels(models.Model):
    quarter_start_date = models.DateTimeField(blank=True,
                                              null=True)  # Field name made lowercase.
    quarter_end_date = models.DateTimeField(blank=True,
                                              null=True)  # Field name made lowercase.
    average = models.FloatField(blank=True, null=True)
    skill = models.TextField(blank=True,
                                                     null=True)  # Field name made lowercase.
    # class Meta:
    #     managed = False
    #     db_table = 'dashboard_skill_levels_tenure_averages'

class SkillLevelsEmployee(models.Model):
    employee = models.ForeignKey(Employee,db_column='EMP_DRIVER_ID', null=True, blank=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(Organization,db_column='organization_id', null=True, blank=True, on_delete=models.SET_NULL)
    start_date = models.DateTimeField(db_column='start_date', blank=True,null=True)
    skill_name = models.TextField(db_column='skill_name', blank=True, null=True)
    value = models.FloatField(db_column='value',blank=True, null=True)
    tenure = models.DateTimeField(db_column='tenure',blank=True, null=True)
    tenure_average = models.FloatField(db_column='tenure_average',blank=True, null=True)
    skill_level = models.BigIntegerField(db_column='skill_level',blank=True, null=True)
    skill_level_min= models.FloatField(db_column='skill_level_min', blank=True, null=True)
    skill_level_max= models.FloatField(db_column='skill_level_max', blank=True, null=True)
    aggregated= models.BooleanField(db_column='aggregated', blank=True, null=True)
    # class Meta:
    #     managed = False
    #     db_table = 'dashboard_skill_levels_employee_values'

class DirectViews(models.Model):
    tableName = models.CharField(max_length=100)
    label = models.CharField(max_length=255, null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)
    filter_options = models.JSONField(null=True, blank=True)
    lambdaOptions = models.JSONField(null=True, blank=True)
    icon = models.CharField(max_length=100, default='task')

class DashboardBatteryAggregations(models.Model):
    sc_dt = models.DateField(db_column='SC_DT')  # Field name made lowercase.
    time_type = models.CharField(db_column='TIME_TYPE', max_length=255)  # Field name made lowercase.
    organization = models.ForeignKey(Organization, db_column='ORGANIZATION_ID', blank=True, on_delete=models.SET_NULL, null=True, related_name='dashboard_batt_organization')  # Field name made lowercase.
    employee = models.ForeignKey(Employee, db_column='EMPLOYEE_ID',  blank=True, on_delete=models.SET_NULL, null=True, related_name='dashboard_batt_emp')  # Field name made lowercase.
    index_type = models.CharField(db_column='INDEX_TYPE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    id_name_helper = models.CharField(db_column='ID_NAME_HELPER', max_length=255, blank=True, null=True)  # Field name made lowercase.
    parent_id = models.IntegerField(db_column='PARENT_ID', blank=True, null=True)  # Field name made lowercase.
    parent_name = models.CharField(db_column='PARENT_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    num_ops = models.FloatField(db_column='NUM_OPS', blank=True, null=True)  # Bat Ops
    batt_truck_num = models.FloatField(db_column='BATT_TRUCK_NUM', blank=True, null=True)  # Field name made lowercase.
    batt_truk_avg = models.FloatField(db_column='BATT_TRUK_PCNT', blank=True, null=True)  # Field name made lowercase.
    matched_tests = models.FloatField(db_column='MATCHED_TESTS', blank=True, null=True)  # Field name made lowercase.
    test_rate_avg = models.FloatField(db_column='TEST_RATE', blank=True, null=True)  # Field name made lowercase.
    edocs_count = models.FloatField(db_column='EDOCS_COUNT', blank=True, null=True)  # Field name made lowercase.
    edocs_conv_avg = models.FloatField(db_column='EDOCS_CONV_PCNT', blank=True, null=True)  # Field name made lowercase.
    conv_to_fail_num = models.FloatField(db_column='CONV_TO_FAIL_NUM', blank=True, null=True)  # Field name made lowercase.
    conv_to_fail_denom = models.FloatField(db_column='CONV_TO_FAIL_DENOM', blank=True, null=True)  # Field name made lowercase.
    conv_to_fail = models.FloatField(db_column='CONV_TO_FAIL', blank=True, null=True)  # Field name made lowercase.
    edocs_denom = models.FloatField(db_column='EDOCS_PCNT_DENOM', blank=True, null=True)  # Field name made lowercase.
    edocs_avg = models.FloatField(db_column='EDOCS_PCNT', blank=True, null=True)  # Field name made lowercase.
    vin_count = models.FloatField(db_column='VIN_COUNT', blank=True, null=True)  # Field name made lowercase.
    vin_avg = models.FloatField(db_column='VIN_PCNT', blank=True, null=True)  # Field name made lowercase.
    date_updated = models.DateTimeField(db_column='DATE_UPDATED', blank=True, null=True)  # Field name made lowercase.
    paid_call_count = models.DecimalField(db_column='PAID_CALL_COUNT', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    light_svc_volume = models.DecimalField(db_column='LIGHT_SVC_VOLUME', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    ata_under_45_freq = models.DecimalField(db_column='ATA_UNDER_45_FREQ', max_digits=7, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    battery_volume = models.DecimalField(db_column='BATTERY_VOLUME', max_digits=23, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    battery_ata_avg = models.DecimalField(db_column='BATTERY_OPP_ATA_AVG', max_digits=23, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    battery_ata_sum = models.DecimalField(db_column='BATTERY_OPP_ATA_SUM', max_digits=23, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    battery_replacement_volume = models.DecimalField(db_column='BATTERY_REPLACEMENT_VOLUME', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    battery_replacement_freq = models.DecimalField(db_column='BATTERY_REPLACEMENT_FREQ', max_digits=23, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    battery_ol_to_clr_avg = models.DecimalField(db_column='BATTERY_OL_TO_CLR_AVG', max_digits=23, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    battery_ol_to_clr_sum = models.DecimalField(db_column='BATTERY_OL_TO_CLR_SUM', max_digits=23, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_overall_sat_avg = models.FloatField(db_column='AAA_MGMT_BATTERY_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_overall_sat_count = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    aaa_mgmt_battery_overall_sat_sum = models.BigIntegerField(db_column='AAA_MGMT_BATTERY_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    comp_battery_overall_sat_avg = models.FloatField(db_column='COMP_BATTERY_OVERALL_SAT_AVG', blank=True, null=True)  # Field name made lowercase.
    comp_battery_overall_sat_count = models.BigIntegerField(db_column='COMP_BATTERY_OVERALL_SAT_COUNT', blank=True, null=True)  # Field name made lowercase.
    comp_battery_overall_sat_sum = models.BigIntegerField(db_column='COMP_BATTERY_OVERALL_SAT_SUM', blank=True, null=True)  # Field name made lowercase.
    approximate_battery_revenue = models.DecimalField(db_column='APPROXIMATE_BATTERY_REVENUE', max_digits=25, decimal_places=0, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'dashboard_battery_aggregations'
        unique_together = (('organization', 'employee', 'sc_dt', 'time_type', 'parent_id'), ('employee', 'organization', 'sc_dt', 'time_type', 'parent_id'),)