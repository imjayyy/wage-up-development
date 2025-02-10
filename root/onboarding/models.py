from django.db import models
from django.contrib.auth.models import User
from accounts.models import *


### DEMOS ###

# a list of demo objects to be returned dependent on the page



class DemoContent(models.Model):
    html_content = models.TextField(null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    include = models.BooleanField(null=True)
    order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.object_id)


class DemoPage(models.Model):
    url = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    content = models.ManyToManyField(DemoContent)

    def __str__(self):
        return str(self.name)


# track where users have gone
class UserDemoHistory(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, related_name='demo_history', on_delete=models.SET_NULL)
    page = models.ForeignKey(DemoPage, null=True, blank=True, related_name='demo_history', on_delete=models.SET_NULL)
    seen = models.BooleanField(null=True)

    def __str__(self):
        return str(self.user.username) + ': ' + str(self.page.name)

### DOCUMENTS ###

class MetricCategories(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    # permission = models.ManyToManyField(Permissions)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='category_parent', on_delete=models.SET_NULL)

class Documentation(models.Model):
    element = models.CharField(max_length=255, null=True, blank=True)
    element_type = models.CharField(max_length=255, null=True, blank=True)
    html_content = models.TextField(null=True, blank=True)
    category = models.ForeignKey(MetricCategories, null=True, blank=True, related_name='metric_category', on_delete=models.SET_NULL)
    number_type = models.CharField(max_length=255, null=True, blank=True)
    highGood = models.BooleanField(null=True)
    permission = models.ManyToManyField(Permissions, blank=True)
    faq = models.ManyToManyField('self', blank=True)
    formatted_name = models.CharField(max_length=255, null=True, blank=True)
    raw_equation = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.element)




class Feedback(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, related_name='feedback', on_delete=models.SET_NULL)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)


class GaUserTracking(models.Model):
    sessions = models.BigIntegerField(db_column='Sessions', blank=True, null=True)  # Field name made lowercase.
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    position_type = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=150)
    organization = models.CharField(max_length=255, blank=True, null=True)
    organization_parent = models.CharField(max_length=255, blank=True, null=True)
    org_parent = models.ForeignKey(Organization, null=True, blank=True, related_name='userTracking', on_delete=models.SET_NULL)
    last_login = models.DateTimeField()
    is_staff = models.BooleanField(null=True)
    sat_app_logins = models.BigIntegerField(db_column='sat_app_logins', blank=True, null=True)  # Field name made lowercase.
    website_logins = models.BigIntegerField(db_column='website_logins', blank=True, null=True)  # Field name made lowercase.
    scheduler_views = models.BigIntegerField(db_column='scheduler_views', blank=True, null=True)  # Field name made lowercase.
    last_scheduler_view = models.DateTimeField(db_column='last_scheduler_view', blank=True, null=True)  # Field name made lowercase.
    map_views = models.BigIntegerField(db_column='map_views', blank=True, null=True)  # Field name made lowercase.


    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'user_tracking_view'



class Enhancements(models.Model):
    explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.explanation

class Deployments(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    enhancements = models.ManyToManyField(Enhancements, blank=True)

class ErrorLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, related_name='errorTracking', on_delete=models.SET_NULL)
    time = models.DateTimeField(auto_now_add=True)
    error = models.TextField(blank=True, null=True)
    context = models.TextField(blank=True, null=True)