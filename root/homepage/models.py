from django.db import models
from accounts.models import Employee, EmployeeGroup

# Create your models here.
class Widget(models.Model):
    type = models.CharField(max_length=225, null=True, blank=True)


class WidgetData(models.Model):
    widget = models.ForeignKey(Widget, related_name='widget_type', null=True, blank=True, on_delete=models.SET_NULL)
    order = models.IntegerField(null=True, blank=True)
    grid_size = models.IntegerField(default=1)
    title = models.TextField(null=True, blank=True)
    time = models.TextField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    announcementType = models.CharField(max_length=225, null=True, blank=True)
    image = models.FileField(null=True, blank=True)
    url_link = models.CharField(max_length=225, null=True, blank=True)
    permissions = models.ManyToManyField(Employee, related_name='visible_for')
    type = models.CharField(max_length=225, default='simple') # can be simple or modal for now
    modal_content = models.ManyToManyField('WidgetModalContent', related_name='modal_content')
    file = models.FileField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name='widget_group')
    seen_by = models.ManyToManyField(Employee, related_name='widget_seen_by')

# For modal purposes
class WidgetModalContent(models.Model):
    text = models.CharField(max_length=225, null=True, blank=True)
    url_link = models.CharField(max_length=225, null=True, blank=True)
    url_text = models.CharField(max_length=225, null=True, blank=True)
    file = models.FileField(null=True, blank=True)
    is_file = models.BooleanField(default=False)

# For the forms
class AddRemoveDriver(models.Model):
    tm = models.CharField(max_length=255, blank=True, null=True)
    shop_id = models.CharField(max_length=255, blank=True, null=True)
    multiple_id = models.BooleanField(blank=True, null=True)
    shop_id_list = models.CharField(max_length=255, blank=True, null=True)
    add_drivers = models.TextField(null=True, blank=True)
    remove_drivers = models.TextField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    open = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

class TechIssue(models.Model):
    shop_id = models.CharField(max_length=255, blank=True, null=True)
    tm = models.CharField(max_length=255, blank=True, null=True)
    point_of_contact = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(max_length=255, null=True, blank=True)
    open = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)