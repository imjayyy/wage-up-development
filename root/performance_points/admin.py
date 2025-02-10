from django.contrib import admin
from .models import *
from root.utilities import download_csv, send_custom_email
from django.urls import reverse
from django.utils.html import format_html

# Register your models here.


@admin.register(PPContest)
class PPContestAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PPContest._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(PPRound)
class PPRoundAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PPRound._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(PPTeam)
class PPTeamAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PPTeam._meta.fields if field.name != "id"]
    actions = [download_csv]

class CampaignListItemInline(admin.TabularInline):
    model = CampaignListItem
    extra = 1  # Number of blank fields to display for new items

@admin.register(PPCampaign)
class PPCampaignAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PPCampaign._meta.fields if field.name != "id"]
    inlines = [CampaignListItemInline]
    actions = [download_csv]

# @admin.register(CampaignRegistrationStatusView2023)
class CampaignRegistrationStatusView2023Admin(admin.ModelAdmin):
    list_display = ['full_name', 'organization_name', 'facility_rep', 'registration_link', 'registration_date', 'email', 'username']
    search_fields = ('emp__last_name',)
    list_filter = ('facility_rep', 'organization_name')
    ordering = ('-registration_date',)
    def registration_link(self, obj):
        print(obj.reg)
        if obj.reg:
            url = f"https://aaa-ne-api-dev.wageup.com/admin/performance_points/ppcampaignregistration/{obj.reg.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.reg.id)
        else:
            return None

    registration_link.short_description = 'Registration'  # Sets column name.
    actions = [download_csv]

@admin.register(SpringUp2024DriverTable)
class SpringUp2024DriverTableAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'station',  'ne_driver_id', 'field_consultant', 'registered', 'registration_date', 'username']
    search_fields = ('employee__last_name',)
    # list_filter = ('facility_rep', 'organization_name')
    ordering = ('-registration_date',)

    # def registration_link(self, obj):
    #     print(obj.reg)
    #     if obj.reg:
    #         url = f"https://aaa-ne-api-dev.wageup.com/admin/performance_points/ppcampaignregistration/{obj.reg.id}/change/"
    #         return format_html('<a href="{}">{}</a>', url, obj.reg.id)
    #     else:
    #         return None

    def ne_driver_id(self, obj):
        return obj.driver_id

    # registration_link.short_description = 'Registration'  # Sets column name.
    ne_driver_id.short_description = 'NE Driver ID'
    actions = [download_csv]



@admin.register(PPCampaignRegistration)
class PPCampaignRegistration(admin.ModelAdmin):
    list_display = [field.name for field in PPCampaignRegistration._meta.fields if field.name != "id"] + [
        'org_name',
        'emp_name',
        'ne_driver_id'
    ]
    search_fields = ('employee__full_name', 'employee__organization__name', 'employee__last_name', 'employee__first_name')
    actions = [download_csv]

    def org_name(self, queryset):
        return queryset.employee.organization.name

    def emp_name(self, queryset):
        return queryset.employee.full_name

    def ne_driver_id(self, queryset):
        return queryset.employee.raw_data_driver_id
#
# @admin.register(PPTeamScore)
# class PPTeamScoreAdmin(admin.ModelAdmin):
#     list_display = [field.name for field in PPTeamScore._meta.fields if field.name != "id"]
#     actions = [download_csv]
#
#
# @admin.register(PPTeamScoreComponent)
# class PPTeamScoreComponentAdmin(admin.ModelAdmin):
#     list_display = [field.name for field in PPTeamScoreComponent._meta.fields if field.name != "id"]
#     actions = [download_csv]


@admin.register(TeamPreferences)
class TeamPreferencesAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TeamPreferences._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(TeamAssignments)
class TeamAssignmentsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TeamAssignments._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(PPCampaignDriverMetricTrackingTable)
class PPCampaignDriverMetricTrackingTableAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PPCampaignDriverMetricTrackingTable._meta.fields if field.name != "id"]
    actions = [download_csv]

