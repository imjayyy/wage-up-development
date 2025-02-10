from django.contrib import admin
from .models import *
from root.utilities import download_csv
from root.utilities import InputFilter
from django.db.models import Q

class SurveyServiceDateFilter(InputFilter):
    parameter_name = 'sc_dt_surveys'
    title = 'Service Date Surveys CHANGED'

    def queryset(self, request, queryset):
        if self.value() is not None:
            sc_dt = self.value()

            return queryset.filter(
                Q(sc_dt_surveys=sc_dt)
            )

class SurveyServiceDateAfter(InputFilter):
    parameter_name = 'sc_dt_surveys__gte'
    title = 'Survey Service Date After:'

    def queryset(self, request, queryset):
        if self.value() is not None:
            sc_dt = self.value()

            return queryset.filter(
                Q(sc_dt_surveys__gte = sc_dt)
            )


class AppeaalsStatusFilter(InputFilter):
    parameter_name = 'appeals_request__request_data__status'
    title = 'Appeals Status'

    def queryset(self, request, queryset):
        if self.value() is not None:
            status = self.value()

            return queryset.filter(
                Q(appeals_request__request_data__status=status)
            )

class SurveyCallIDFilter(InputFilter):
    parameter_name = 'sc_id_surveys'
    title = 'Survey Call ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            sc_id = self.value()

            return queryset.filter(
                Q(sc_id_surveys=sc_id)
            )


class AppealsServiceIDFilter(InputFilter):
    parameter_name = 'call_number'
    title = 'Appeals Call ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            call_number = self.value()

            return queryset.filter(
                Q(call_number=call_number)
            )

class ServiceDateFilter(InputFilter):
    parameter_name = 'sc_dt'
    title = 'Service Date'

    def queryset(self, request, queryset):
        if self.value() is not None:
            sc_dt = self.value()

            return queryset.filter(
                Q(sc_dt=sc_dt)
            )

class ServiceDateAfter(InputFilter):
    parameter_name = 'sc_dt__gte'
    title = 'Service Date After:'

    def queryset(self, request, queryset):
        if self.value() is not None:
            sc_dt = self.value()

            return queryset.filter(
                Q(sc_dt__gte=sc_dt)
            )


class ServiceIDFilter(InputFilter):
    parameter_name = 'sc_id'
    title = 'Call ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            sc_id = self.value()

            return queryset.filter(
                Q(sc_id=sc_id)
            )

class EmpDriverID(InputFilter):
    parameter_name = 'emp_driver_id'
    title = 'WageUp Employee ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            emp_driver_id = self.value()

            return queryset.filter(
                Q(emp_driver_id=emp_driver_id)
            )

class OrgSvcFaclID(InputFilter):
    parameter_name = 'org_svc_facl_id'
    title = 'WageUp Station ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            org_svc_facl_id = self.value()

            return queryset.filter(
                Q(org_svc_facl_id=org_svc_facl_id)
            )

# Register your models here.
# @admin.register(Dashboard)
# class DashboardAdmin(admin.ModelAdmin):
#     list_display = [field.name for field in Dashboard._meta.fields if field.name != "id"]
#     list_filter = ('sc_dt', 'index_type', 'time_type',)
#     actions = [download_csv]

@admin.register(RawOps)
class RawOps(admin.ModelAdmin):
    list_display = ['sc_dt', 'sc_id', 'driver_name', 'emp_driver_id', 'check_id_compliant', 're_tm', 'svc_facl_id', 'resolution', 'tcd']
    list_filter = (ServiceDateFilter, ServiceIDFilter,EmpDriverID,OrgSvcFaclID, ServiceDateAfter)
    actions = [download_csv]

@admin.register(Std12EReduced)
class Std12EReduced(admin.ModelAdmin):
    list_display = ['sc_dt_surveys', 'sc_id_surveys', 'sc_svc_prov_type', 'reroute', 'remove', 'appeals_status', 'is_valid_record',
                    'directional_error', 'recordeddate', 'date_updated_surveys','check_id_compliant', 'check_id_id', 'driver_id', 'drv_id', 'driver_name',
                    'dup_call_id','fst_spot_time', 'kept_informed_sat',  'facility_sat', 'overall_sat', 'driver5', 'org_business_id', 'org_svc_facl_id', 'q24', 'q26', 'q27', 'q28', 'q30',
                    'driver10', 'rec_ind', 'response_sat', 're_tm', 'sp_fac_id', 'svc_facl_id', 'tcd']
    ordering=('-date_updated_surveys',)
    list_filter = (SurveyServiceDateFilter, SurveyServiceDateAfter, SurveyCallIDFilter,EmpDriverID,OrgSvcFaclID, AppeaalsStatusFilter)
    actions = [download_csv]

    def appeals_status(self, obj):
        try:
            return obj.appeals_request.request_data.status
        except:
            return None
# Register your models here.
@admin.register(EmployeeDashboardElement)
class CustomDashboardApiAdmin(admin.ModelAdmin):
    list_display = [field.name for field in EmployeeDashboardElement._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(EmployeeDashboard)
class CustomDashboardApiAdmin(admin.ModelAdmin):
    list_display = [field.name for field in EmployeeDashboard._meta.fields if field.name != "id"]
    actions = [download_csv]

# Register your models here.
@admin.register(RawStd12EQuestions)
class RawStd12EQuestionsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in RawStd12EQuestions._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(Std12ETierTimePeriods)
class Std12ETierTimePeriodsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Std12ETierTimePeriods._meta.fields if field.name != "id"]
    list_filter = ('name', 'start', 'end', 'type', 'recorded_cutoff', 'show_until')

@admin.register(Appeals)
class Appeals(admin.ModelAdmin):
    list_display = [field.name for field in Appeals._meta.fields]
    list_filter = ('good', 'removes', 'reroutes', 'incentive_month', AppealsServiceIDFilter)
    actions = [download_csv]

# @admin.register(Checkidopsraw)
# class Checkidopsraw(admin.ModelAdmin):
#     list_display = [field.name for field in Checkidopsraw._meta.fields]
#     actions = [download_csv]
#     list_filter = (ServiceDateFilter, ServiceIDFilter,EmpDriverID,OrgSvcFaclID, ServiceDateAfter)

@admin.register(MetricGoals)
class DocumentAdmin(admin.ModelAdmin):
    field_names = [field.name for field in MetricGoals._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]
