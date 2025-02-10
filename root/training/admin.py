from django.contrib import admin
from .models import *
from root.utilities import download_csv
from .forms import UserDocumentForm

# Register your models here.

@admin.register(ModuleOverview)
class ModuleOverviewAdmin(admin.ModelAdmin):
    field_names = [field.name for field in ModuleOverview._meta.fields if field.name != "id"]
    list_display = field_names
    actions=[download_csv]

@admin.register(ModulePage)
class ModulePageAdmin(admin.ModelAdmin):
    field_names = [field.name for field in ModulePage._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('overview',)
    actions=[download_csv]

@admin.register(ModuleCompletion)
class ModuleCompletionAdmin(admin.ModelAdmin):
    field_names = [field.name for field in ModuleCompletion._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('module',)
    actions=[download_csv]

@admin.register(ModuleMultipleChoice)
class ModuleMultipleChoiceAdmin(admin.ModelAdmin):
    field_names = [field.name for field in ModuleMultipleChoice._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('module',)
    actions=[download_csv]

@admin.register(Campaign)
class ModuleMultipleChoiceAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Campaign._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('module',)
    actions=[download_csv]

@admin.register(ModuleFlow)
class ModuleFlowAdmin(admin.ModelAdmin):
    field_names = [field.name for field in ModuleFlow._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('module',)
    actions=[download_csv]

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    field_names = [field.name for field in UserProgress._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('module', 'user')
    actions=[download_csv]

@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    form = UserDocumentForm
    field_names = [field.name for field in UserDocument._meta.fields if field.name != 'id']
    list_display = field_names
    list_filter = ('doc_name', )
    actions = [download_csv]

    def save_model(self, request, obj, form, change):
        if len(request.POST.getlist('position_type')) > 0:
            type = ', '.join(request.POST.getlist('position_type'))
            obj.position_type = type
        super().save_model(request, obj, form, change)


@admin.register(TrainingProgress)
class TrainingProgress(admin.ModelAdmin):
    field_names = [field.name for field in TrainingProgress._meta.fields]
    list_display = field_names
    list_filter = ('organization_parent_name', )
    actions = [download_csv]

@admin.register(TrainingVideo)
class TrainingVideoAdmin(admin.ModelAdmin):
    field_names = [field.name for field in TrainingVideo._meta.fields]
    list_display = field_names


@admin.register(CampaignUser)
class CampaignUserAdmin(admin.ModelAdmin):
    field_names = [field.name for field in CampaignUser._meta.fields] + ['employee_name','organization_name']
    search_fields = ('employee__last_name', 'employee__organization__name')

    def employee_name(self, obj):
        return obj.employee.full_name

    def organization_name(self, obj):
        return obj.employee.organization.name

    raw_id_fields = ('employee', 'user')
    list_display = field_names

@admin.register(UserDocumentCategory)
class UserDocumentCategoryAdmin(admin.ModelAdmin):
    field_names = [field.name for field in UserDocumentCategory._meta.fields]
    list_display = field_names
