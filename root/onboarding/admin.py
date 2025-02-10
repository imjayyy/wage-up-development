from django.contrib import admin
from .models import *
from root.utilities import download_csv


# Register your models here.

@admin.register(Documentation)
class DocumentAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Documentation._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]

@admin.register(MetricCategories)
class DocumentAdmin(admin.ModelAdmin):
    field_names = [field.name for field in MetricCategories._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]

@admin.register(GaUserTracking)
class GaUserTracking(admin.ModelAdmin):
    field_names = ['sessions',
                   'first_name',
                   'last_name',
                   'position_type',
                   'username',
                   'organization',
                   'organization_parent']
    list_display = field_names
    list_filter = ('position_type', )
    search_fields = ('last_name', 'name')

@admin.register(DemoPage)
class DemoPageAdmin(admin.ModelAdmin):
    field_names = [field.name for field in DemoPage._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]

@admin.register(UserDemoHistory)
class UserDemoHistoryAdmin(admin.ModelAdmin):
    field_names = [field.name for field in UserDemoHistory._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]

@admin.register(DemoContent)
class DemoContentAdmin(admin.ModelAdmin):
    field_names = [field.name for field in DemoContent._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]


@admin.register(Enhancements)
class EnhancementsAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Enhancements._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]

@admin.register(Deployments)
class DeploymentsAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Deployments._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]