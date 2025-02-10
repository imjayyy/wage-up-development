from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.db.models import Max
from .models import *
from root.utilities import download_csv
from root.utilities import InputFilter
from django.db.models import Q
# from .views import sendFirebaseNotification
from accounts.models import *
from arena.models import DriverCampaignRegistration

# def sendPushNotification(parameters):
#     fcm_devices = FCMDevice.objects.filter(user=parameters['user'])
#     fcm_devices.send_message(
#         title=parameters['title'], body=parameters['body'], time_to_live=604800,
#         click_action=parameters['click_url'])


@admin.register(Announcements)
class Announcements(admin.ModelAdmin):
    list_display = [field.name for field in Announcements._meta.fields if field.name != "id"]

    def PushAnnouncement(self, request, queryset):
        for q in queryset:

            users = User.objects.all()
            print(q.position_types)
            print(q.campaign_group)
            if q.position_types != 'everyone':
                users = users.filter(employee__position_type=q.position_types)

            if q.campaign_group is not None:
                drivers = DriverCampaignRegistration.objects.filter(campaign = q.campaign_group)
                users.filter(employee__in=drivers)

            users = list(users.values_list('id', flat=True))

            parameters = {
                'user': users,
                'title': "New Announcement",
                'body': q.message,
                'click_url': q.link
            }
            print(users)
            sendFirebaseNotification(parameters)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'target_by_station_states':
            kwargs['queryset'] = Organization.objects.filter(type='Station-State').order_by('name')
        if db_field.name == 'target_by_station_business':
            kwargs['queryset'] = Organization.objects.filter(type='Station-Business').order_by('name')
        if db_field.name == 'target_by_facility_rep':
            kwargs['queryset'] = Organization.objects.filter(type='Facility-Rep').order_by('name')
        if db_field.name == 'target_by_hubs':
            kwargs['queryset'] = Organization.objects.filter(type='Hub').order_by('name')
        return super(Announcements, self).formfield_for_manytomany(db_field, request, **kwargs)

    actions = [download_csv, PushAnnouncement]

@admin.register(EmailLogs)
class EmailLogs(admin.ModelAdmin):
    list_display = [field.name for field in EmailLogs._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(EmailData)
class EmailData(admin.ModelAdmin):
    list_display = ('subject', 'author_id', 'updated')
    actions = [download_csv]

@admin.register(ScheduledMessages)
class ScheduledMessages(admin.ModelAdmin):
    list_display = [field.name for field in ScheduledMessages._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(TriggerMessages)
class TriggerMessages(admin.ModelAdmin):
    list_display = [field.name for field in TriggerMessages._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(ChatMessage)
class ChatMessage(admin.ModelAdmin):
    list_display = [field.name for field in ChatMessage._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(ChatGroup)
class ChatGroup(admin.ModelAdmin):
    list_display = [field.name for field in ChatGroup._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(MTKMessage)
class MTKMessage(admin.ModelAdmin):
    list_display = [field.name for field in MTKMessage._meta.fields]
    list_filter = ['type', 'active']
    actions = [download_csv]
    search_fields = ['inbox_message_title', 'banner_text']

