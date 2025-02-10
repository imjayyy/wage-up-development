from django.db import models
from accounts.models import Employee, EmployeeGroup, Organization, Profile
from dashboard.models import *

# Create your models here.

class Subscriptions(models.Model):
    organization_subject = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='organization_subscription')
    employee_subject = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_subscription')
    topic_request_data = models.TextField(null=True, blank=True)
    subscriptions = models.ManyToManyField(Employee)

class Topics(models.Model):
    name = models.CharField(null=True, blank=True, max_length=255)

# class EmployeeCommentsGroup(models.Model):
#     name = models.CharField(null=True, blank=True, max_length=255)
#     associated_with = models.CharField(null=True, blank=True, max_length=255)

class Comments(models.Model):
    commentDate = models.DateTimeField('date published', auto_now=True)
    commentText = models.TextField(blank=False, null=False)
    requestData = models.TextField(null=True, blank=True)
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='comment_emp')
    employeeDashboard = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='comment_emp_db')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,  related_name='comment_org')
    order = models.IntegerField(null=False, blank=False, default=0)
    important = models.BooleanField(default=False) # for pinning
    edited = models.BooleanField(default=False)
    comment_likes = models.ManyToManyField(Employee, related_name='comment_likes')
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='comment_parent')
    is_reply = models.BooleanField(default=False)
    mentions = models.ManyToManyField(Employee, blank=True, related_name='comment_mentions')
    topics = models.ManyToManyField(Topics, blank=True, related_name='comment_topics')
    chart_element = models.ForeignKey('dashboard.EmployeeDashboardElement', blank=True, null=True, related_name='comment_chart_element', on_delete=models.SET_NULL)
    seen_by = models.ManyToManyField(Employee, related_name='seen_by')
    people_of_interest = models.ManyToManyField(Employee, related_name='people_of_interest')
    # important_mark = models.BooleanField(default=False) # for making it important
    private = models.BooleanField(default=False)
    groups = models.ManyToManyField(EmployeeGroup, related_name='comment_group', blank=True)
    survey = models.ManyToManyField('dashboard.Std12EReduced', related_name='survey', blank=True)

    def user_full_name(self):
        if self.employee:
            try:
                employee = Employee.objects.get(user=self.employee)
                return '{0} {1}'.format(employee.first_name, employee.last_name)
            except:
                return '{0} {1}'.format(self.employee.first_name, self.employee.last_name)

    def get_org_name(self):
        if self.organization:
            if str(self.organization.name) != str(self.organization.real_name):
                return '{0} ({1})'.format(self.organization.name, self.organization.real_name)
            else:
                return self.organization.name

    def comment_likes_count(self):
        return self.comment_likes.count()

    def employee_avatar(self):
        try:
            profile = Profile.objects.get(employee=self.employee)
            return profile.photo_avatar
        except:
            pass

        try:
            profile = Profile.objects.get(user=self.employee.user)
            return profile.photo_avatar
        except:
            return None

    class Meta:
        index_together = (
            ('organization', 'commentDate')
        )

    # def get_comment_replies(self):
    #     replies = Comments.objects.filter(reply_to=self.id)
    #     all_replies = []
    #     for r in replies:
    #         obj = r.values('id', 'commentDate', 'commentText', 'requestDate', 'employee', 'organization', 'order', 'important', 'edited', 'comment_likes', 'reply_to')
    #         obj['comment_replies'] = r.comment_replies()
    #         all_replies.append(obj)
    #
    #     return all_replies

class UserCommentNotifications(models.Model):
    newNotificationCount = models.IntegerField(null=False, blank=False, default=0)
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='comment_notifications')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name='comment_notification_org')
