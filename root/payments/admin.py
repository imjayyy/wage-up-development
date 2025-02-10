from django.contrib import admin
from .models import *
from root.utilities import download_csv, send_custom_email


# Register your models here.
@admin.register(TremendousCampaign)
class TremendousCampaignAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TremendousCampaign._meta.fields if field.name != "id"]
    actions = [download_csv]

# Register your models here.
@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PaymentLog._meta.fields if field.name != "id"]
    actions = [download_csv]

# Register your models here.
@admin.register(ManagerBudget)
class ManagerBudgetAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ManagerBudget._meta.fields if field.name != "id"]
    actions = [download_csv]


@admin.register(WingSpanUserEmployee)
class ManagerBudgetAdmin(admin.ModelAdmin):
    list_display = ['get_driver_id', 'get_name', 'get_org', 'wingspanUserId', 'employee', 'type', 'onboarded', 'collaborator_id', 'production', 'date_created', 'date_onboarded', 'completed_w9', ]

    def get_name(self, obj):
        return obj.employee.full_name

    def get_org(self, obj):
        return obj.employee.organization.name

    def get_driver_id(self, obj):
        return obj.employee.raw_data_driver_id

    get_driver_id.admin_order_field = 'driver_id'
    get_driver_id.short_description = 'Driver ID'

    get_name.admin_order_field = 'driver'
    get_name.short_description = 'Driver'

    get_org.admin_order_field = 'station'
    get_org.short_description = 'Station'

    search_fields = ['employee__raw_data_driver_id', 'employee__first_name', 'employee__last_name', 'employee__organization__name', 'wingspanUserId', 'type', 'onboarded', 'collaborator_id', 'production', 'date_created', 'date_onboarded', 'completed_w9']

    actions = [download_csv]
