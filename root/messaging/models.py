from django.db import models
import datetime as dt
from datetime import timezone
from django.contrib.auth.models import User
from arena.models import DriverCampaign
from accounts.models import Employee, Organization
from performance_points.models import PPCampaign

# Create your models here.
class MTKMessage(models.Model):
    pp_campaign = models.ForeignKey(PPCampaign, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='banner_message')
    inbox_message_title = models.CharField(max_length=100, null=True, blank=True)
    inbox_message_text = models.TextField(null=True, blank=True)
    banner_text = models.CharField(max_length=50, null=True, blank=True)
    button_text = models.CharField(max_length=20, null=True, blank=True)
    registered_only = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=False)
    hierarchy = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=255,
                            null=True, blank=True, choices=[('general', 'general'), ('raffle', 'raffle'), ('w9', 'w9'), ('registration', 'registration')], default="general")
    external_link = models.CharField(max_length=255, null=True, blank=True)
    internal_link = models.CharField(max_length=255, null=True, blank=True, choices=[('/campaigns', '/campaigns'), ('/payments_w9', '/payments_w9'), ('/training', '/training')])

class EmailData(models.Model):
    requestData = models.TextField(null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    lambdaTableData = models.TextField(null=True, blank=True)
    lambdaSVGData = models.TextField(null=True, blank=True)
    lambdaData = models.TextField(null=True, blank=True)
    pdf_attachment = models.BooleanField(null=True)
    xls_attachment = models.BooleanField(null=True)
    recipients = models.ManyToManyField(User, related_name="UserEmailRecipient")
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='email_author')
    updated = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    disabled = models.BooleanField(default=False)

class TriggerMessages(models.Model):

    metric = models.CharField(max_length=255, null=True, blank=True)
    comparison_type = models.CharField(max_length=255, null=True, blank=True)
    value = models.FloatField(null=True, blank=True)
    logical_operator = models.CharField(max_length=255, null=True, blank=True) # e.g. disjunction, conjunction
    email_data = models.ForeignKey(EmailData, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='trigger_email_data')
    time_type = models.CharField(max_length=255, null=True, blank=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='trigger_org')
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='trigger_emp')
    sc_dt = models.DateField(null=True, blank=True)
    time_relation = models.CharField(max_length=255, null=True, blank=True)
    conjoined_trigger = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='trigger_conjoined')

class MailMessage(models.Model):
    recipient = models.ManyToManyField(Employee)
    message = models.TextField(null=True)
    subject = models.CharField(max_length=100, null=True, blank=True)
    priority = models.CharField(max_length=100, default='Normal')
    sent_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    author = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='mail_auth')
    parent = models.ForeignKey('self',  null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='mail_parent')


class ScheduledMessages(models.Model):
    interval = models.CharField(max_length=255, null=True, blank=True)
    starting = models.DateField(null=True, blank=True)
    ending = models.DateField(null=True, blank=True)
    email_data = models.ForeignKey(EmailData, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='schedule_email_data')


class Announcements(models.Model):
    starts = models.DateTimeField(auto_created=True)
    ends = models.DateTimeField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    position_types = models.CharField(max_length=255, null=True, blank=True,
                                      choices=[('everyone', 'everyone'),
                                               ('Admin', 'Admin'),
                                               ('Appeals-Access', 'Appeals-Access'),
                                               ('Driver', 'Driver'),
                                               ('Executive', 'Executive'),
                                               ('Facility-Rep', 'Facility-Rep'),
                                               ('Field-Rep', 'Field-Rep'),
                                               ('Fleet-Manager', 'Fleet-Manager'),
                                               ('Fleet-Supervisor', 'Fleet-Supervisor'),
                                               ('Project Manager', 'Project Manager'),
                                               ('Station-Admin', 'Station-Admin'),
                                               ('Territory-Associate', 'Territory-Associate')], default="everyone")
    link = models.CharField(max_length=255, null=True, blank=True)
    link_text = models.CharField(max_length=255, null=True, blank=True)
    link_external = models.BooleanField(default=False)
    read = models.ManyToManyField(User, related_name="announcements", blank=True)
    type = models.CharField(max_length=255, null=True, blank=True,
                            choices=[('is-danger', 'is-danger'), ('is-success', 'is-success'),
                                     ('is-primary', 'is-primary'), ('is-warning', 'is-warning')], default="is-primary")
    banner = models.BooleanField(default=False)
    platform = models.CharField(max_length=255, null=True, blank=True, choices=[('RDB Site', 'RDB Site'), ('App', 'App'), ('Global', 'Global')])
    campaign_group = models.ForeignKey(DriverCampaign, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='campaign_group')
    target_by_station_states = models.ManyToManyField(Organization, blank=True, related_name='targeting_station_state')
    target_by_station_business = models.ManyToManyField(Organization, blank=True, related_name='targeting_station_business')
    target_by_facility_rep = models.ManyToManyField(Organization, blank=True, related_name='targeting_facility_rep')
    target_by_hubs = models.ManyToManyField(Organization, blank=True, related_name='targeting_hubs')

class EmailLogs(models.Model):
    date_delivered = models.DateTimeField(auto_created=True)
    sent_to = models.EmailField(null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    parameters = models.TextField(null=True, blank=True)
    generated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='recipient_user')




class ChatGroup(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    invited_users = models.ManyToManyField(User, related_name='chat_group_invited')
    private = models.BooleanField(default=False)
    online_users = models.ManyToManyField(User, related_name='chat_group_online')
    position_type = models.CharField(max_length=255, null=True, blank=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, related_name='online_users', on_delete=models.CASCADE)
    lastMessageID = models.IntegerField(null=True, blank=True)
    lastMessageTime = models.DateTimeField(null=True, blank=True)


class ChatMessage(models.Model):
    from_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='chat_from')
    message = models.TextField(null=True, blank=True)
    time = models.DateTimeField(null=True, blank=True)
    data = models.TextField(null=True, blank=True)
    type = models.CharField(null=True, blank=True, max_length=255)
    group = models.ForeignKey(ChatGroup, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='chat_from')

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        self.time = dt.datetime.now().astimezone(timezone.utc)
        return super(ChatMessage, self).save(*args, **kwargs)

# class OnlineUsers(models.Model):
#     user = models.ForeignKey(User, null=True, blank=True, related_name='online_users', on_delete=models.CASCADE)
#     time = models.DateTimeField()
#
#     def save(self, *args, **kwargs):
#         ''' On save, update timestamps '''
#         self.time = dt.datetime.now().astimezone(timezone.utc)
#         return super(OnlineUsers, self).save(*args, **kwargs)

class BroadcastResponse(models.Model):
    message = models.ForeignKey(ChatMessage, null=True, blank=True, related_name='broadcast_response', on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, blank=True, related_name='broadcast_response', on_delete=models.CASCADE)
    responseBool = models.BooleanField(null=True)
    responseChar = models.CharField(max_length=255, null=True, blank=True)


class NotificationLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, related_name='notification_log', on_delete=models.CASCADE)
    type = models.CharField(max_length=255, null=True, blank=True)
    notification = models.TextField(null=True, blank=True)
    time = models.DateTimeField(auto_now_add=True, null=True)


class Meeting(models.Model):
    meeting_creator = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    meeting_name = models.CharField(max_length=255, null=True, blank=True)
    meeting_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    participants = models.ManyToManyField(User, related_name="meeting_participants")


# class UserEmails(models.Model):
#     user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
#                                             related_name='userMessageSchedules')
#     email_data = models.ForeignKey(EmailData, null=True, blank=True, on_delete=models.SET_NULL,
#                                             related_name='email_data')
