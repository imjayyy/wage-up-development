from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes
from django.utils.text import slugify
import datetime as dt
import json
from django.contrib import auth
from django.conf import settings
from django.utils import timezone



## Permissions
"""
A simple identifier for where people can go on the site

This is accessed via the user_tests and is used in all class-views permissions

"""


class Permissions(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name or ''


## CorporateEntity
"""
This is an object for which employees are organized underneath
For example a list of business, regions, branches, etc. 
from this we organize structure in Framework using foreign key

The first entity in this table should be the client-organization itself

"""

# sometimes employees belong to multiple groups e.g. AAR, CSN Only, Fleet Only
# TODO: note this somewhat conflict with observations_employeegroup we may want to reassociate
class EntityGroups(models.Model):
    name = models.CharField(null=True, blank=True, max_length=255)
    description = models.TextField(null=True, blank=True)


class Organization(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    real_name = models.CharField(max_length=550, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    updated = models.DateTimeField(blank=True, null=True)
    slug = models.SlugField(null=True, blank=True)
    parent_name = models.CharField(max_length=255, null=True, blank=True)
    parent_type = models.CharField(max_length=255, null=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='org_parent')
    parallel_parents = models.ManyToManyField('self', blank=True)
    parallel_parent_stream = models.CharField(max_length=255, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    grandparent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                                    related_name='org_grandparent')
    employees_under = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                                        related_name='org_employees_under')
    facility_type = models.CharField(max_length=255, null=True, blank=True)
    latest_activity_on = models.DateField(null=True, blank=True)
    zip = models.CharField(max_length=255, null=True, blank=True)
    related_orgs = models.TextField(null=True, blank=True)
    facility_type_parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                                    related_name='org_facility_type_parent')

    class Meta:
        index_together = (
            ('name', 'type'),
        )

    def level_index(self, org_type):
        parent_index = {
            'Driver': 0,
            'Fleet-Supervisor': 1,
            'Station': 1,
            'Station-Business': 2,
            'Station-State-Facility-Type': 3,
            'Station-State': 3,
            'Facility-Rep': 3,
            'Facility-Rep-Facility-Type': 3,
            'Hub': 3,
            'Market': 4,
            'Market-Facility-Type': 4,
            'Club-Region': 5,
            'Club-Region-Facility-Type': 5,
            'Club': 4,
            'Club-Facility-Type': 6
        }
        return parent_index[org_type]


    def lineage(self, target_type):

        print(self.type, target_type)
        # ordering = ['Driver', 'Station', 'Station-State', 'Club']
        ordering = ['Driver', 'Station', 'Station-Business', 'Station-State-Facility-Type', 'Station-State', 'Facility-Rep-Facility-State',  'Facility-Rep', 'Hub', 'Club-Facility-Type', 'Club']
        # todo: find diff between target and source and parent up (amount)
        ordering_index = {
            'Driver': 0,
            'Station': 1,
            'Station-Business': 2,
            'Station-State': 4,
            'Station-State-Facility-Type': 3,
            'Facility-Rep': 4,
            'Facility-Rep-Facility-Type': 3,
            'Hub': 4,
            'Club-Facility-Type': 5,
            'Club': 6
        }

        parallel_parents = ['Facility-Rep', 'Hub']

        if ordering.index(self.type) < ordering.index(target_type):
            if self.type == 'Driver':
                raise Exception("driver not allowed like this")
            source = ordering_index[self.type]
            target = ordering_index[target_type]
            diff = target - source
            child = self
            for d in range(diff):
                parent = child.parent
                child = parent

            return [child]

        if target_type == 'Driver':
            return self.employees()

        if target_type == self.type:
            return [self.id]

        if self.type in parallel_parents:
            station_biz = Organization.objects.filter(parallel_parents__in=[self.id])
            if target_type == 'Station-Business':
                return station_biz.values_list('id', flat=True)
            elif target_type == 'Station':
                out = []
                for o in station_biz:
                    out = out + list(o.children().values_list('id', flat=True))
                return out
            elif target_type == 'Driver':
                out = []
                for o in station_biz:
                    out = out + list(o.employees().values_list('id', flat=True))
                return out

        if self.type == 'Club':
            org = Organization.objects.filter(type=target_type)
            return org.values_list('id', flat=True)

        exclusions = ['Grid', 'Call-Center', 'Call-Center-Operator', 'Call-Center-Group', 'Booth']
        obj = self
        print(self.name)
        if 'Facility-Type' in self.type:
            print("THIS is a facility type org!")
            children = obj.org_fac_type_children()
            # obj = Organization.objects.get(id=self.employees_under_id)
            if not children:
                children = obj.org_children()
        else:
            children = obj.org_children().exclude(type__in=exclusions)

        print(obj, "THIS IS THE OBJECT")
        levels_down_to_bottom = self.level_index(obj.type)
        target_levels_down = obj.level_index(target_type)
        levels_to_go = levels_down_to_bottom - target_levels_down
        if levels_to_go < 1:
            return None
        children_out = []
        print("LEVELS DOWN", levels_to_go)
        for l in range(levels_to_go):
            grandchildren = []
            for child in children:
                if child.type in exclusions:
                    continue
                if child.type == target_type:
                    children_out.append(child.id)
                else:
                    if 'Facility-Type' in self.type:
                        for grandchild in child.org_fac_type_children():
                            if grandchild.type in exclusions:
                                continue
                            grandchildren.append(grandchild)
                    else:
                        for grandchild in child.org_children():
                            if grandchild.type in exclusions:
                                continue
                            grandchildren.append(grandchild)
            children = grandchildren
            # print(children, grandchildren)
        print(children_out, "OUTPUT")
        return children_out

    def get_parent_to(self, org_type, store_path=False):
        org = self
        if store_path:
            org_list = [self.id]
        while org.type != org_type and org.parent is not None:
            if store_path:
                org_list.append(org.parent.id)
                org = org.parent
            else:
                org = org.parent
        if store_path:
            return org_list
        return org

    def get_cities(self):
        return list(Cities.objects.filter(organization_id=self.id).order_by('name').values_list('name', flat=True))

    def get_grids(self):
        if self.type == 'Club':
            return Organization.objects.filter(type='Grid')
        if self.type == 'Territory':
            return Organization.objects.filter(type='Grid', parent=self)
        if self.level_index(self.type) < 3:
            territories = self.get_parent_to('Territory')
            territories = [territories,]
        else:
            territories = self.lineage('Territory')
        return Organization.objects.filter(type='Grid', parent__in=territories)

    def children(self, emp_type=None):
        # print(self.name)
        children = Organization.objects.filter(parent=self).exclude(type='avl_zone')

        fac_type__position_type_lookup = {
            'Fleet-Manager': {'facility_type': 'FLEET'},
            'Station-Admin': {'facility_type__in': ['PSP', 'NON-PSP']},
            'Territory-Associate': {'facility_type__in': ['PSP', 'NON-PSP']},
        }

        if emp_type is not None:
            children = children.filter(**fac_type__position_type_lookup.get(emp_type, {}))


        if children.count() == 0:
            return Employee.objects.filter(organization=self)
        else:
            return children
        # this function tells who is underneath this entity

    def org_children(self):
        children = Organization.objects.filter(parent=self)
        return children

    def station_driver_children(self, last_date=False):
        children = StationDriver.objects.filter(station=self.object.id)
        if last_date:
            children = children.objects.filter(last_sc_dt__gte=last_date)
        return children

    def org_fac_type_children(self):
        children = Organization.objects.filter(facility_type_parent_id=self.id)
        # csn case:
        if not children:
            # print(self.facility_type)
            # print(self.employees_under)
            if self.facility_type.lower() == 'csn':
                csn_cousins = Organization.objects.filter(employees_under=self.employees_under, facility_type__in=['NON-PSP', 'PSP'])
                children = Organization.objects.filter(facility_type_parent_id__in=csn_cousins)

        # print(children, "FACILITY ORG CHILDREN")
        return children

    def grandchildren(self):
        children = Organization.objects.filter(grandparent=self)
        if children.count() == 0:

            return Employee.objects.filter(organization=self.id)
        else:
            return children
        # this function is aimed at when we want to jump a level lower -- i.e. get station_ids under a territory

    def employees(self, emp_type='Driver'):

        def get_emp_parents_from_territory_facility_type(obj):
            stations = obj.org_fac_type_children()
            print("Stations", stations)
            emp_parents = set()
            for station in stations:
                print(station.parent)
                emp_parents.add(station.parent.employees_under_id)
            print(emp_parents)
            return emp_parents


        print(self.type, "GETTING EMPLOYEES")
        if self.type == 'Station-Business':
            print('EMPLOYEE OBJECT BEING RETURNED', Employee.objects.filter(organization_id=self.employees_under_id))
            return Employee.objects.filter(organization_id=self.employees_under_id)
        if self.type == 'Station':
            if emp_type:
                return Employee.objects.filter(organization=self.parent.employees_under_id).filter(position_type=emp_type)
            else:
                return Employee.objects.filter(organization=self.parent.employees_under_id)
        if self.type == 'Station-State':
            if emp_type:
                return Employee.objects.filter(organization__in=self.children().values('id')).filter(position_type=emp_type)
            else:
                return Employee.objects.filter(organization=self.id)
        if self.type == 'Market':
            if emp_type:
                return Employee.objects.filter(organization__in=self.grandchildren().values('employees_under_id')).filter(position_type=emp_type)
            else:
                return Employee.objects.filter(organization=self.id)
        if self.type == 'Club-Region':
            if emp_type:
                emp_parents = []
                for gchild in self.grandchildren():
                    emp_parents = emp_parents + list(gchild.children().values_list('employees_under_id', flat=True))
                return Employee.objects.filter(organization__in=emp_parents).filter(position_type=emp_type)
            else:
                return Employee.objects.filter(organization=self.id)
        if self.type == 'Club':
            if emp_type:
                return list(Employee.objects.filter(position_type=emp_type).values_list('id'))
            else:
                return Employee.objects.filter(organization=self.id)
        if self.type == 'Territory-Facility-Type':
            emp_parents = get_emp_parents_from_territory_facility_type(self)
            print(emp_parents, "TERRITORY emp parents")
            return Employee.objects.filter(organization__in=emp_parents).filter(position_type=emp_type)
        if self.type == 'Market-Facility-Type':
            drivers = []
            for t in self.org_fac_type_children():
                emp_parents = get_emp_parents_from_territory_facility_type(t)
                if emp_parents:
                    emps = list(Employee.objects.filter(position_type=emp_type, organization_id__in=emp_parents).values_list('id', flat=True))
                    print(t, emps)
                    drivers = drivers + emps
            return drivers
        if self.type == 'Club-Region-Facility-Type':
            drivers = []
            for m in self.org_fac_type_children():
                for t in m.org_fac_type_children():
                    emp_parents = get_emp_parents_from_territory_facility_type(t)
                    if emp_parents:
                        emps = list(Employee.objects.filter(position_type=emp_type,
                                                            organization_id__in=emp_parents).values_list('id',
                                                                                                         flat=True))
                        print(t, emps)
                        drivers = drivers + emps
            return drivers
        if self.type == 'Club-Facility-Type':
            drivers = []
            for c in self.org_fac_type_children():
                for m in c.org_fac_type_children():
                    for t in m.org_fac_type_children():
                        print(t)
                        try:
                            emp_parents = get_emp_parents_from_territory_facility_type(t)
                        except:
                            print(t, t.id, "HAS NO CHILDREN!")
                            raise Exception
                            emp_parents = False
                        if emp_parents:
                            emps = list(Employee.objects.filter(position_type=emp_type,
                                                                organization_id__in=emp_parents).values_list('id',
                                                                                                             flat=True))
                            print(t, emps)
                            drivers = drivers + emps
            return drivers

        return Employee.objects.filter(organization=self.id).filter(position_type=emp_type)

    def siblings(self):
        return Organization.objects.filter(parent=self.parent)
        # this function tells who shares the same parent as you

    def __str__(self):
        return self.display_name or ''

    def check_for_duplicates(self):
        same_name_count = Organization.objects.filter(name=self.name, type=self.type).count()
        if same_name_count > 0:
            return True
        else:
            return False

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""

        # is_duplicate = self.check_for_duplicates()
        #
        # if is_duplicate:
        #     print("THIS IS A DUPLICATE")
        #     raise Exception("DUPLICATE RECORD FOUND: ", self.name)

        if not self.parent:
            try:
                self.parent = Organization.objects.get(name=self.parent_name)
            except:
                print("COULDNT MAKE A PARENT MATCH! Is the parent name properly set? for: ", self.name)

        if not self.grandparent:
            try:
                self.grandparent = self.parent.parent
            except:
                print("COULDNT MAKE A GRANDPARENT MATCH! ", self.name)

        if not self.parent_type:
            try:
                self.parent_type = self.parent.type
            except:
                print("COULDNT add parent type to", self.name)

        if not self.slug:
            try:
                self.slug = slugify(str(self.name))
            except:
                print("Couldnt auto-generate a slug: ", self.name)

        if not self.updated:
            try:
                self.updated = dt.datetime.utcnow()
            except:
                print("Couldnt auto-generate a updated field: ", self.name)

        if not self.display_name:
            try:
                if self.real_name != self.name:
                    self.display_name = str(self.name) + ' ' + str(self.real_name) + ' (@' + str(self.parent_name) + ')'
                else:
                    self.display_name = str(self.name) + ' (@' + str(self.parent_name) + ')'
            except:
                print("Couldnt assign a display name: ", self.name)

        if not self.real_name:
            try:
                self.real_name = self.name
            except:
                print("couldnt assign a real name to ", self.name)

        return super(Organization, self).save(*args, **kwargs)


## Employee
"""
Foreign Key with User or Null

This table is either provided by the client or by us and is a list of all ELIGIBLE employees that can use the site.

All the data in this table comes from the client-side.

It is connected to Permission Group --> An employee has a certain kind of permission

An optional table may also be an Abilities table which is Many to Many Tied to Employee

"""


class Employee(models.Model):
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True)
    slug = models.SlugField(null=True, blank=True)
    permission = models.ManyToManyField(Permissions, blank=True)
    position_type = models.CharField(max_length=255, null=True, blank=True, choices=(
        ('Driver', 'Driver'),
        ('Executive', 'Executive'),
        ('Station-Admin', 'Station-Admin'),
        ('Fleet-Manager', 'Fleet-Manager'),
        ('Call-Center-Operator', 'Call-Center-Operator'),
        ('Admin', 'Admin'),
        ('Appeals-Access', 'Appeals-Access'),
        ('Territory-Associate', 'Territory-Associate'),
        ('Bot', 'Bot')
    ))
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='employee')
    parallel_organizations = models.ManyToManyField(Organization, related_name='employee_parallel_organization', blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='employee')
    org_name_help = models.CharField(max_length=255, null=True, blank=True)
    username_help = models.CharField(max_length=255, null=True, blank=True)
    permission_help = models.CharField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    data_name = models.CharField(max_length=255, null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    latest_activity_on = models.DateField(null=True, blank=True)
    invited_on = models.DateTimeField(null=True, blank=True)
    login_id = models.CharField(max_length=255, null=True, blank=True)
    duplicate = models.BooleanField(null=True, blank=True)
    registered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='employee_registered_by')
    unverified_email = models.CharField(max_length=255, null=True, blank=True)
    no_match = models.BooleanField(null=True)
    active = models.BooleanField(default=True)
    user_mod = models.BooleanField(default=False)
    updated_auto = models.DateTimeField(auto_now=True)
    default_station = models.CharField(max_length=255, null=True, blank=True)
    raw_data_driver_id = models.CharField(max_length=255, blank=True, null=True)
    fleet_supervisor = models.ManyToManyField('self', blank=True)
    group = models.ManyToManyField('EmployeeGroup', related_name='employee_group',blank=True)
    # station_m2m = models.ManyToManyField(Organization, related_name="employee_station")

    class Meta:
        index_together = (
            ('data_name', 'position_type'),
        )

    def get_related_employee(self):
        print(f'Cross territory duplication ==================================\n=========================================\n==============================================')
        if self.organization.related_orgs is not None:
            related = json.loads(self.organization.related_orgs)
            related_emps = Employee.objects.filter(organization__in=Organization.objects.filter(
                slug__in=related['related-slug'] + [self.organization.slug]), first_name=self.first_name,
                last_name=self.last_name, position_type=self.position_type).exclude(
                id=self.id)
            print(related_emps)
            return related_emps
        else:
            return None
    def get_related_user(self):
        print('getting related user', self.id)
        emps = self.get_related_employee()
        print(emps)
        for e in emps:
            if e.user:
                return e.user
        raise Exception("No Related user Found", emps, self.id)

    def invite_link(self):
        invite = Invite.objects.filter(employee=self, already_used=False)
        if not invite:
            return "No Invite"
        else:
            invite = invite[0]

        if not invite.already_used:
            invite_url_id = urlsafe_base64_encode(force_bytes(invite.id))
            invite_url = "https://aaane.wageup.com/invited/?id=" + str(invite_url_id)
            return "Email: " + invite.email + "\n Invite URL: " + invite_url
        else:
            return "ALREADY USED INVITE"

    def cross_territory_duplicates(self):
        related_orgs = self.organization.related_orgs
        if related_orgs is not None and related_orgs != "":
            related_orgs = json.loads(related_orgs)
            dups_list = []
            for slug in related_orgs['related-slug']:
                org = Organization.objects.get(slug=slug)
                newEmp = list(Employee.objects.filter(organization=org, last_name=self.last_name, first_name=self.first_name).values_list('slug', 'organization__parent__name'))
                dups_list = dups_list + newEmp
            if len(dups_list) > 0:
                print(dups_list, "DUPS LIST")
                return dups_list
            return None
        else:
            return None

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.updated:
            try:
                self.updated = dt.datetime.now()
            except:
                print("Couldnt add time to the updated field!")

        if not self.slug:
            try:
                self.slug = slugify(str(self.organization.id) + '-' + str(self.first_name) + '-' + str(self.last_name))
            except:
                print("Couldnt auto-generate a slug: ", self.last_name)

        if not self.org_name_help:
            try:
                self.org_name_help = self.organization.name
            except:
                print("Couldnt get the Organization name for helper column ", self.last_name)

        if not self.username_help:
            try:
                self.username_help = self.user.username
            except:
                print("Couldnt get the Username for helper column! ", self.last_name)

        if not self.permission_help:
            try:
                self.permission_help = self.permission.name
            except:
                print("Couldnt get the Permission for helper column: ", self.last_name)

        if not self.full_name:
            try:
                self.full_name = self.first_name + ' ' + self.last_name
            except:
                print("Couldnt make a full name: ", self.last_name)

        if not self.display_name:
            try:
                self.display_name = self.full_name + ' (' + self.org_name_help + ')'
            except:
                print("Couldnt make a display name ", self.last_name)

        return super(Employee, self).save(*args, **kwargs)



    def __str__(self):
        return self.slug or ''



class EmployeeProfile(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employee_profile')
    trouble_code_type = models.CharField(max_length=255, null=True, blank=True)
    active_not_available = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def employee_name(self):
        return self.employee.full_name

    class Meta:
        index_together = (
            ('employee', 'active')
        )

    # def employee_pto(self):
    #     today = dt.datetime.now()
    #     pto = EmployeeProfileEntries.objects.filter(driver_profile=seld.id, pto_end__gte=today).exclude(pto_end=None)
    #     return pto

class EmployeeProfileEntries(models.Model):
    driver_profile = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='employee_profile_entries')
    day_of_week = models.CharField(max_length=255, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    pto_start = models.DateField(null=True, blank=True)
    pto_end = models.DateField(null=True, blank=True)

class EmployeeGroup(models.Model):
    group_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    permission = models.ManyToManyField(Permissions, related_name='employee_group_permissions')

    def __str__(self):
        return self.group_name





### USER MODIFICATIONS -->> ADDING METHODS

class Bookmarks(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_bookmark')
    display = models.CharField(null=True, blank=True, max_length=255)
    link = models.CharField(null=True, blank=True, max_length=255)


def employee(self):
    employee = Employee.objects.get(user=self.id)
    return employee.id

def bookmarks(self):
    bookmarks = Bookmarks.objects.filter(user=self.id)
    return bookmarks

auth.models.User.add_to_class('employee', employee)
auth.models.User.add_to_class('bookmarks', bookmarks)

## Invite

"""

Carries data about the employee, for which we want to generate a user from

It can only be created by employee parents

It has a method which sends the invite to the email attached to it


"""

context_p1_text = """

This performance dashboard is your one-stop-shop for all the metrics you need to get better and to see how you compare 
to your peers. This is also where you can find out your latest scores in any ongoing games. 

"""


class Invite(models.Model):
    employee = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='invite')
    email = models.EmailField()
    created_on = models.DateField(auto_now_add=True, null=True, blank=True)
    sent_on = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='invite')
    created_by_employee = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL,
                                            related_name='created_by_invite')
    already_used = models.BooleanField(default=False)
    expiration = models.DateField(null=True, blank=True)
    context_p1 = models.TextField(default=context_p1_text, blank=True, null=True)
    context_p2 = models.TextField(default="", blank=True, null=True)
    campaign = models.CharField(max_length=255, null=True, blank=True)

    def email_invite(self, template='invite_email.html'):
        message = render_to_string('accounts/' + template, {
            'first_name': self.employee.first_name,
            'last_name': self.employee.last_name,
            'domain': settings.FRONT_END_DOMAIN,  # TODO: change the domain
            # 'organization': self.created_by_employee.organization,
            'inviteid': urlsafe_base64_encode(force_bytes(self.id)).decode(),
            'context_p1': self.context_p1,
            'context_p2': self.context_p2,
        })

        print("SENT INVITE EMAIL TO: ", self.email)
        to_email = self.email
        mail_subject = "Invitation for " + self.employee.first_name + ' ' + self.employee.last_name + " to access AAA NE Roadside Data Platform"
        email = EmailMessage(mail_subject, message, 'admin.noreply@wageup.com', to=[to_email, 'help@wageup.com'])
        # message = f"""
        #     <p>{self.context_p1}</p>
        #     <p>{self.context_p2}</p>
        # """
        # email_details = {
        #     'subject': mail_subject,
        #     'from': 'admin.noreply@wageup.com',
        #     'to': to_email,
        #     'goTo': {
        #         'url': settings.FRONT_END_DOMAIN + '?id=' + str(urlsafe_base64_encode(force_bytes(self.id)).decode()),
        #         'name': 'Registration'
        #     },
        #     'reply_to': 'admin.noreply@wageup.com',
        #     'message': message
        # }
        # s_email()
        email.send()

    def __str__(self):
        return self.employee.slug or ''

    def save(self, *args, **kwargs):
        """ set the cache_key_prefix and slug"""
        if not self.expiration:
            try:
                expiration = dt.datetime.utcnow() + dt.timedelta(days=60)
                self.expiration = expiration.date()
            except:
                print("Couldnt auto-generate an expiration: ", self.employee.full_name)

        if not self.created_by_employee:
            try:
                self.created_by_employee = Employee.objects.get(user=self.created_by)
            except:
                print("Couldnt assign employee for the creating user.", self.employee.full_name)
        return super(Invite, self).save(*args, **kwargs)


## Profile
"""
Foreign Key with User 

This table is all user-generated data about the user. From here we can include profile pictures, location data

It can link to user-specific settings or goals. 

"""

# from messaging.models import ChatGroup

class Profile(models.Model):
    from training.models import ModuleOverview
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='profile')
    bio = models.TextField(null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    slug = models.SlugField(null=True, blank=True)
    employee = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='profile')
    viewed_show = models.BooleanField(
        default=False)  ## we could make this a many to many if we wanted to make multiple demos and track what has been seen.
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    receive_email_notifications = models.BooleanField(null=True, default=False)
    receive_phone_notifications = models.BooleanField(null=True, default=False)
    site_visits = models.IntegerField(default=0)
    photo_avatar = models.FileField(null=True, blank=True)
    banner_pic = models.FileField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    completed_modules = models.ManyToManyField(ModuleOverview, related_name='completed_modules')
    campaign_preferred_email = models.CharField(max_length=255, null=True, blank=True)
    watching_chat_users = models.ManyToManyField(User, related_name='watching_chat_users')
    # watching_chat_groups = models.ManyToManyField(ChatGroup, related_name='watching_chat_groups')
    silence_all_notifications = models.BooleanField(default=False)
    silence_login_notifications = models.BooleanField(default=True)
    silence_watched_login_notifications = models.BooleanField(default=False)
    silence_message_notifications = models.BooleanField(default=False)
    chat_status = models.CharField(null=True, max_length=255, blank=True)
    status_expiration = models.DateTimeField(null=True, blank=True)

    class Meta:
        index_together = (
            ('chat_status', 'user', 'silence_all_notifications', 'silence_message_notifications', 'silence_login_notifications', 'silence_watched_login_notifications'),
        )

    def save(self, *args, **kwargs):

        try:
            if not self.employee:
                self.employee = Employee.objects.get(id=self.user.employee())
            if not self.display_name:
                self.display_name = self.employee.display_name
            if not self.slug:
                self.slug = self.employee.slug
        except:
            print("couldnt make a match to an employee: ", self.user.username)

        return super(Profile, self).save(*args, **kwargs)


class Duplicates(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='duplicates')
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='duplicates')
    normalized_name = models.TextField(blank=True, null=True)
    public_name = models.BigIntegerField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    primary_key = models.AutoField(primary_key=True)
    organization_parent = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='duplicates_parent')
    organization_parent_name = models.CharField(db_column='ORGANIZATION_PARENT_NAME', max_length=255, blank=True,
                                                null=True)  # Field name made lowercase.
    organization_grandparent = models.ForeignKey(Organization, null=True, on_delete=models.SET_NULL, blank=True,
                                                 related_name='duplicates_grandparent')  # Field name made lowercase.
    organization_grandparent_name = models.CharField(db_column='ORGANIZATION_GRANDPARENT_NAME', max_length=255,
                                                     blank=True, null=True)  # Field name made lowercase.
    updated = models.DateTimeField(blank=True, null=True, auto_now=True)
    raw_data_driver_id = models.CharField(max_length=255, blank=True, null=True)



class QAEmployeeFlags(models.Model):
    employee_id = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='qa')
    no_match = models.BooleanField(null=True)
    fname = models.CharField(max_length=255, blank=True, null=True)
    lname = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='qa')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='qa')
    problem = models.CharField(max_length=255, blank=True, null=True)


class SimpleAccountsOrgStations(models.Model):
    wageup = models.OneToOneField(Organization, blank=True, on_delete=models.DO_NOTHING,
                                     related_name='simple_accounts', primary_key=True, unique=True)
    station_name = models.CharField(max_length=255, blank=True, null=True)
    wageup_station_biz_id = models.IntegerField(blank=True, null=True)
    station_business_name = models.CharField(max_length=255, blank=True, null=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    territory_name = models.CharField(max_length=255, blank=True, null=True)
    market_name = models.CharField(max_length=255, blank=True, null=True)
    club_region_name = models.CharField(max_length=255, blank=True, null=True)
    facility_type = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'simple_accounts_org_stations'


class UserActivity(models.Model):
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    organization = models.CharField(max_length=255, blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    username = models.CharField(max_length=150)
    territory = models.CharField(max_length=255, blank=True, null=True)
    position_type = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'user_activity'


class StationDriver(models.Model):
    driver = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='driver_stationDriver')
    station = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='station_stationDriver')
    last_sc_dt = models.DateField(null=True, blank=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'accounts_stationdriver_view'


class UserLogins(models.Model):
    userId = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    login_time = models.DateTimeField(null=True, blank=True)
    login_type = models.CharField(max_length=255, blank=True, null=True)


class Cities(models.Model):
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=255, blank=True, null=True)

class UserActions(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    display = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    model_name = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

class UserActionDetails(models.Model):
    db_action_type = models.CharField(max_length=255, blank=True, null=True) #e.g. update, delete, add, remove,
    db_model = models.CharField(max_length=255, blank=True, null=True)
    db_model_id = models.IntegerField(null=True, blank=True)
    context = models.CharField(max_length=255, blank=True, null=True)
    field = models.CharField(max_length=255, blank=True, null=True)
    from_value = models.CharField(max_length=255, blank=True, null=True)
    to_value = models.CharField(max_length=255, blank=True, null=True)
    parent_action = models.ForeignKey(UserActions, null=True, blank=True, on_delete=models.CASCADE, related_name='details')

class CustomEmail(models.Model):
    campaign = models.CharField(max_length=255, blank=True, null=True) #e.g. update, delete, add, remove,
    email_body = models.TextField()
    email_subject = models.CharField(max_length=255, blank=True, null=True)
    testing = models.BooleanField(default=True)
    testing_email = models.CharField(max_length=255, blank=True, null=True, default='help@wageup.com')
    from_email = models.CharField(max_length=255, blank=True, null=True, default='help@wageup.com')

    def save(self, *args, **kwargs):
        assert '@wageup.com' in self.from_email, 'must use @wageup.com in from email!'
        super(CustomEmail, self).save(*args, **kwargs)



# class SocketConnections(models.Model):
#     room_group_name = models.CharField(max_length=255, null=True, blank=True)
#     user = models.ForeignKey(User, null=True, blank=True, related_name='socket_connection', on_delete=models.CASCADE)
#     time = models.DateTimeField()
#
#     def __str__(self):
#         return str(self.user) + '-' + str(self.room_group_name)
#
#     def save(self, *args, **kwargs):
#         ''' On save, update timestamps '''
#         self.time = dt.datetime.now()
#         return super(SocketConnections, self).save(*args, **kwargs)
#
#     class Meta:
#         unique_together = [
#            'room_group_name',
#            'user'
#         ]


class ApprovalRequests(models.Model):
    requester = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='requester_employee')
    approver = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='approver_employee')
    submission_date = models.DateTimeField(null=True, blank=True, default=timezone.now)
    review_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(choices=[('Pending_Review', 'Pending_Review'), ('Rejected', "Rejected"), ("Approved", "Approved")], max_length=100, default='Pending_Review')
    requester_notes = models.TextField(null=True, blank=True)
    approver_notes = models.TextField(null=True, blank=True)


    #def save(self): do we want to check approver has the right permission?

appeals_choices = [
('Battery Warranty Voided', 'battery_warranty_void'),
 ('Battery Replacement Not Eligible (no fail)',
  'battery_replace_not_eligible'),
 ('Servicing Restrictions (Club or State mandated/ Environment / Weather)',
  'service_restriction_mandate'),
 ('Service Exceeds Membership Coverage Limits (enrollment, tolls, mileage, excess winch etc.)',
  'service_exceeds_member_limits'),
 ('Coverage Exclusions (AGM Battery, tire plug, diesel fuel, windshield wiper fluid, etc.)',
  'coverage_exclusion'),
 ('Service Requirements (vehicle keys etc.)', 'service_requirements'),
 ('Incorrect Contact and Location Information* (unable to be resolved through attempts) ',
  'incorrect_info'),
 ('communications_problem',
  'communications_problem'),
 ('System/App Malfunction ', 'system_malfunction'),
 ('Phone Connectivity', 'phone_connectivity'),
 ('Survey comments/answers are about an experience with a different station or driver.',
  'different_driver')]

class ApprovalRequestAppeals(models.Model):
    appeals_reason = models.CharField(choices=appeals_choices, max_length=255)
    exception_granted = models.BooleanField(null=True, blank=True)
    request_data = models.ForeignKey(ApprovalRequests, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='appeals_approval')
    reviewer_appeals_reason = models.CharField(max_length=255, null=True, blank=True)

class ApprovalRequestEmployeeTimeOff(models.Model):
    pto_start = models.DateField(null=True, blank=True)
    pto_end = models.DateField(null=True, blank=True)
    request_data = models.ForeignKey(ApprovalRequests, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='timeoff_approval')

class ApprovalRequestEmployeeAvailability(models.Model):
    day_of_week = models.CharField(max_length=255, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    prev_start = models.TimeField(null=True, blank=True)
    prev_end = models.TimeField(null=True, blank=True)
    request_data = models.ForeignKey(ApprovalRequests, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='availability_approval')

    # def current_availability(self):
    #     entry = EmployeeProfileEntries.objects.get(driver_profile__employee_id=self.request_data__requester_id, day_of_week=self.day_of_week)
    #     return {'start_time': entry.start_time, 'end_time': entry.end_time}

class ScheduleOpenAvailability(models.Model):
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.CASCADE)
    date_schedule = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    open = models.BooleanField(default=True)
    service_type = models.CharField(max_length=255, null=True, blank=True)
    potential_drivers = models.ManyToManyField(Employee, related_name='potential_drivers')
    drivers_available = models.ManyToManyField(Employee, related_name='drivers_said_yes')
    drivers_rejected = models.ManyToManyField(Employee, related_name='drivers_said_no')
    drivers_accepted = models.ManyToManyField(Employee, related_name='drivers_scheduled')

class MobileAppVersion(models.Model):
    version = models.CharField(max_length=255)
    current_release = models.BooleanField(default=False)
    release_date = models.DateField(auto_now=True, blank=True, null=True)

class CustomWageupEmail(models.Model):
    subject = models.CharField(max_length=255)
    custom_url = models.CharField(max_length=255, null=True, blank=True)
    custom_button_label = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=False)


class CustomWageupEmail(models.Model):
    subject = models.CharField(max_length=255)
    custom_url = models.CharField(max_length=255, null=True, blank=True)
    custom_button_label = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.subject

class Survey(models.Model):
    # Adding Survey to admin
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='survey')
    employee_first_name = models.CharField(max_length=255, null=True, blank=True)
    employee_last_name = models.CharField(max_length=255, null=True, blank=True)
    employee_email = models.EmailField(null=True, blank=True)
    mtk_satisfaction = models.CharField(max_length=255, null=True, blank=True)
    mtk_recommendation_likelihood = models.IntegerField(null=True, blank=True)
    mtk_job_improvements = models.JSONField(default=list, blank=True)
    mtk_usage_frequency = models.CharField(max_length=255, null=True, blank=True)
    mtk_ease_of_use = models.CharField(max_length=255, null=True, blank=True)
    mtk_importance = models.CharField(max_length=255, null=True, blank=True)
    mtk_inspiration = models.CharField(max_length=255, blank=True)
    mtk_improvement_response = models.TextField(null=True, blank=True)
    mtk_testimonial = models.TextField(null=True, blank=True)

class EligibleDriver(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    driver_id = models.IntegerField(null=True, blank=True)
    driver_org = models.CharField(max_length=100, null=True, blank=True)
    recipient_email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.display_name} - {self.driver_org} - Eligible"
