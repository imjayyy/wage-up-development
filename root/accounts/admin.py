from django.contrib import admin
from .models import *
from django.utils.text import slugify
from accounts.models import *
from root.utilities import download_csv
from root.utilities import InputFilter
from root.utilities import send_custom_email
from django.db.models import Q
from django.conf import settings
# from django.core import urlresolvers
from django.utils.html import format_html
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from messaging.views import send_email as s_email
import datetime as dt

# Register your models here.
class OrgNameFilter(InputFilter):
    parameter_name = 'organization__name'
    title = 'ORGANIZATION NAME'

    def queryset(self, request, queryset):
        if self.value() is not None:
            org_name = self.value()

            return queryset.filter(
                Q(organization__name=org_name)
            )

class EmailFilter(InputFilter):
    parameter_name = 'employee_email'
    title = 'EMPLOYEE EMAIL'

    def queryset(self, request, queryset):
        if self.value() is not None:
            email = self.value()

            return queryset.filter(
                Q(user__email=email) | Q(invite__email=email)
            )

class OrgNameFilter(InputFilter):
    parameter_name = 'organization__children'
    title = 'STATION ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            print(Organization)
            org_name = Organization.objects.get(name=self.value()).parent_id

            return queryset.filter(
                Q(organization_id=org_name))

class ParentEmpOrgNameFilter(InputFilter):
    parameter_name = 'organization__parent__name'
    title = 'Parent Organization Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            org_name = self.value()

            return queryset.filter(
                Q(organization__parent__name=org_name)
            )

class csn_fleet(admin.SimpleListFilter):
    parameter_name = 'csn_fleet'
    title = 'FLEET vs CSN'

    def lookups(self, request, model_admin):

        return (
            ('fleet', ('Fleet')),
            ('csn',  ('CSN')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'fleet':
            return queryset.filter(organization__facility_type='Fleet')

        if self.value() == 'csn':
            return queryset.exclude(organization__facility_type='Fleet')


class isUser(admin.SimpleListFilter):
    parameter_name = 'user'
    title = 'IS CURRENTLY A USER'

    def lookups(self, request, model_admin):

        return (
            ('yes', ('Yes')),
            ('no',  ('No')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(user__isnull=False)

        if self.value() == 'no':
            return queryset.filter(user__isnull=True)


class isStaff(admin.SimpleListFilter):
    parameter_name = 'staff'
    title = 'IS STAFF'

    def lookups(self, request, model_admin):

        return (
            ('yes', ('Yes')),
            ('no',  ('No')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(user__is_staff=True)

        if self.value() == 'no':
            return queryset.filter(user__is_staff=False)


class isActive(admin.SimpleListFilter):
    parameter_name = 'active'
    title = 'IS ACTIVE (90 days)'

    def lookups(self, request, model_admin):

        return (
            ('yes', ('Yes')),
            ('no',  ('No')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(active=True)

        if self.value() == 'no':
            return queryset.filter(active=False)



class employeeIsUser(admin.SimpleListFilter):
    parameter_name = 'employee__user'
    title = 'IS CURRENTLY A USER'

    def lookups(self, request, model_admin):

        return (
            ('yes', ('Yes')),
            ('no',  ('No')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(employee__user__isnull=False)

        if self.value() == 'no':
            return queryset.filter(employee__user__isnull=True)



class ParentOrganizationFilter(InputFilter):
    parameter_name = 'parent_name'
    title = 'PARENT ORGANIZATION NAME'

    def queryset(self, request, queryset):
        if self.value() is not None:
            org_name = self.value()

            return queryset.filter(
                Q(parent_name=org_name)
            )


class EmployeeParentOrganizationFilter(InputFilter):
    parameter_name = 'employee__organization__parent_name'
    title = 'PARENT ORGANIZATION NAME'

    def queryset(self, request, queryset):
        if self.value() is not None:
            org_name = self.value()

            return queryset.filter(
                Q(employee__organization__parent_name=org_name)
            )


@admin.register(QAEmployeeFlags)
class QAEmployeeFlags(admin.ModelAdmin):
    field_names = [field.name for field in QAEmployeeFlags._meta.fields]
    list_display = field_names
    list_display_links = ['id',]
    list_filter = ('problem',)
    search_fields = ('lname', )


@admin.register(SimpleAccountsOrgStations)
class SimpleAccountsOrgStations(admin.ModelAdmin):
    field_names = ['link_to_organization',] + [field.name for field in SimpleAccountsOrgStations._meta.fields]
    list_display = field_names
    list_display_links = ['wageup',]
    def link_to_organization(self, obj):
        link = "https://aaane.wageup.com/admin/accounts/organization/"  + str(obj.wageup.id) + "/change/"
        link = reverse('admin:accounts_organization_change', args=[obj.wageup.id])
        return format_html('<a href="%s">%s</a>' % (link,obj.wageup.name))
    list_filter = ('territory_name', 'market_name')
    search_fields = ('station_name', )
    link_to_organization.allow_tags=True

@admin.register(UserActivity)
class UserActivity(admin.ModelAdmin):
    field_names = ['first_name', 'last_name', 'organization', 'last_login', 'username', 'territory', 'position_type', 'email']
    list_filter = ('position_type', 'territory')
    list_display = field_names
    search_fields = ('last_name', )
    actions=[download_csv]

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Employee._meta.fields] + ['invite_link', 'ops_link', 'surveys_link', 'check_id_link', 'last_login', 'last_app_login', 'email', 'parallel_orgs']
    list_display = field_names
    list_display_links = ['id', 'last_name']
    list_filter = ('position_type', 'no_match', OrgNameFilter, ParentEmpOrgNameFilter, EmailFilter, 'organization__facility_type', isUser, csn_fleet, isActive, isStaff)
    search_fields = ('last_name', 'organization__name', 'user__username', 'login_id')

    def provider_type(self, obj):
        return obj.organization.facility_type

    def parallel_orgs(self, obj):
        return ','.join(list(obj.parallel_organizations.all().values_list('name', flat=True)))

    def station_state(self, obj):
        if obj.organization.parent:
            return obj.organization.parent.name
        else:
            return None

    def last_login(self, obj):
        if obj.user is not None:
            return obj.user.last_login
        else:
            return None

    def last_app_login(self, obj):
        if obj.user is not None:
            return UserLogins.objects.filter(userId_id=obj.user.id, login_type='satapp').latest('login_time').login_time
        else:
            return None

    def email(self, obj):
        if obj.user:
            return obj.user.email
        else:
            try:
                invite = Invite.objects.filter(employee_id=obj.id)
                if invite:
                    return invite[0].email
            except ObjectDoesNotExist:
                return None


    def invite_link(self, obj):
        return obj.invite_link()

    def ops_link(self, obj):
        return format_html("<a href='https://orca.wageup.com/admin/dashboard/rawops/?emp_driver_id=" + str(obj.id) + "'>Go to Ops</a>")

    def surveys_link(self, obj):
        return format_html("<a href='https://orca.wageup.com/admin/dashboard/std12eraw/?emp_driver_id=" + str(obj.id) + "'>Go to Surveys</a>")

    def check_id_link(self, obj):
        return format_html("<a href='https://orca.wageup.com/admin/dashboard/checkidopsraw/?emp_driver_id=" + str(obj.id) + "'>Go to check id</a>")

    ops_link.allow_tags = True

    def apply_beta_surveys_permission(self, request, queryset):
        for e in queryset:
            e.permission.add(Permissions.objects.get(id=13))
            e.save()

    def apply_beta_mydashboard_permission(self, request, queryset):
        for e in queryset:
            e.permission.add(Permissions.objects.get(id=14))
            e.save()

    def apply_beta_maps_permission(self, request, queryset):
        for e in queryset:
            e.permission.add(Permissions.objects.get(id=20))
            e.save()

    def apply_user_tracking_permission(self, request, queryset):
        for e in queryset:
            e.permission.add(Permissions.objects.get(id=21))
            e.save()

    def feature_email_notice_user(self, request, queryset):
        for e in queryset:
            message = render_to_string('accounts/feature_email.html', {
                'first_name': e.first_name,
                'last_name': e.last_name,
                'domain': settings.FRONT_END_DOMAIN,  # TODO: change the domain
                'username': e.user.username
            })
            to_email = e.user.email
            print("SENT INVITE EMAIL TO: ", to_email)
            mail_subject = "ACA Roadside Dashboard - New Reports and Features!"
            email = EmailMessage(mail_subject, message, 'admin.noreply@wageup.com', to=[to_email, 'help@wageup.com'])
            email.send()

    def mark_as_duplicate(self, request, queryset):
        for s in queryset:
            s.duplicate = True
            s.save()

    def remove_duplicates(self, request, queryset):
        dup_selected, real_selected = False, False
        if (len(queryset) < 2):
            return
        for s in queryset:
            if s.duplicate:
                dup_selected = True
            else:
                real_selected = True
        if dup_selected == False or real_selected == False:
            return

        for s in queryset:
            if s.duplicate:
                s.delete()

    def update_user(self, request, queryset):
        for s in queryset:
            s.user = None
            s.save()

    def save_related(self, request, form, formsets, change):
        super(EmployeeAdmin, self).save_related(request, form, formsets, change)
        if form.instance.permission.all().count() == 0:
            permissions_list = {
                "Admin": [1, 9, 21],
                "Driver": [12,],
                "Executive": [1, 9, 21],
                "Fleet-Manager": [1, 9, 17, 21, 22],
                "Station-Admin": [1, 9, 21],
                "Facility-Rep": [1, 9, 21],
                "Territory-Associate": [1, 9, 21]
            }
            for p in permissions_list[form.instance.position_type]:
                form.instance.permission.add(Permissions.objects.get(id=p))

    def send_active_custom_wageup_email(self, request, queryset):
        try:
            email = CustomWageupEmail.objects.get(active=1)
            not_sent_to = []
            for s in queryset:
                to_email = s.user.email
                if to_email is None:
                    print('NO email for ', s.first_name)
                    not_sent_to.append(f'{s.first_name} {s.last_name}, \n')
                    continue
                email_details = {
                    'subject': email.subject,
                    'from': 'admin.noreply@wageup.com',
                    'to': to_email,
                    'customGoTo': {
                        'url': email.custom_url if email.custom_url is not None else 'https://ne.wageup.com/',
                        'name': email.custom_button_label if email.custom_button_label is not None else 'Click here to Register for Access'
                    },
                    'replyTo': 'admin.noreply@wageup.com',
                    'message': email.message,
                    'getInTouch': 'Need assistance?'
                }
                print('email sent to', s.first_name)
                s_email(email_details)
            # Make sure it got sent so it will send it to
            email_details = {
                'subject': email.subject,
                'from': 'admin.noreply@wageup.com',
                'to': 'help@wageup.com',
                'replyTo': 'help@wageup.com',
                'message': f'email not sent to: {not_sent_to}',
                'getInTouch': 'Need assistance?'
            }
            print(email_details)
            s_email(email_details)
        except:
            return

    actions = [update_user, download_csv, mark_as_duplicate, remove_duplicates,
               feature_email_notice_user, apply_beta_surveys_permission, apply_beta_mydashboard_permission, apply_beta_maps_permission, apply_user_tracking_permission, send_active_custom_wageup_email]




@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Organization._meta.fields if field.name != "id"]
    raw_id_fields = ('parent',)
    list_display = field_names
    list_filter = ('type', ParentOrganizationFilter)
    actions = [download_csv]
    search_fields = ('name', 'parent__name')


@admin.register(Invite)
class Invites(admin.ModelAdmin):
    field_names = [field.name for field in Invite._meta.fields if field.name != "id"]
    raw_id_fields = ("employee", "created_by_employee")

    list_display = field_names

    list_select_related = ('employee', 'created_by_employee') #TODO: implement elsewhere
    list_filter = (employeeIsUser, 'employee__organization__facility_type', EmployeeParentOrganizationFilter, 'employee__position_type', 'campaign')
    search_fields = ('employee__last_name',)

    def send_invite_email(self, request, queryset):
        for s in queryset:
            to_email = s.email
            mail_subject = "Invitation for " + s.employee.first_name + ' ' + s.employee.last_name + " to access AAA NE Roadside Dashboard"
            # email = EmailMessage(mail_subject, message, 'admin.noreply@wageup.com', to=[to_email, 'help@wageup.com'])

            message = f"""
                        <p>{s.context_p1}</p>
                        <p>{s.context_p2}</p>
                    """
            email_details = {
                'subject': mail_subject,
                'from': 'admin.noreply@wageup.com',
                'to': to_email,
                'customGoTo': {
                    'url': f'https://ne.wageup.com/invite?id={urlsafe_base64_encode(force_bytes(s.id))}',
                    'name': 'Click here to Register for Access'
                },
                'replyTo': 'admin.noreply@wageup.com',
                'message': message,
                'getInTouch': 'Need assistance?'
            }
            print(email_details)
            s_email(email_details)
            s.sent_on = dt.datetime.now()
            s.save()
            # s.email_invite()

    def send_custom_invite_email(self, request, queryset):
        for s in queryset:
            s.email_invite(template='invite_email.html')
    def send_active_custom_wageup_email(self, request, queryset):
        try:
            email = CustomWageupEmail.objects.get(active=1)
            not_sent_to = []
            for s in queryset:
                to_email = s.email
                if to_email is None:
                    print('NO email for ', s.employee.first_name)
                    not_sent_to.append(f'{s.employee.first_name} {s.employee.last_name}, \n')
                    continue
                email_details = {
                    'subject': email.subject,
                    'from': 'admin.noreply@wageup.com',
                    'to': to_email,
                    'customGoTo': {
                        'url': email.custom_url if email.custom_url is not None else 'https://ne.wageup.com/',
                        'name': email.custom_button_label if email.custom_button_label is not None else 'Click here to Register for Access'
                    },
                    'replyTo': 'admin.noreply@wageup.com',
                    'message': email.message,
                    'getInTouch': 'Need assistance?'
                }
                print('email sent to', s.employee.first_name)
                s_email(email_details)
                s.sent_on = dt.datetime.now()
                s.save()
            # Make sure it got sent so it will send it to
            email_details = {
                'subject': email.subject,
                'from': 'admin.noreply@wageup.com',
                'to': 'help@wageup.com',
                'replyTo': 'help@wageup.com',
                'message': f'email not sent to: {not_sent_to}',
                'getInTouch': 'Need assistance?'
            }
            print(email_details)
            s_email(email_details)
        except:
            return

    actions = [send_invite_email, download_csv, send_custom_invite_email, send_active_custom_wageup_email]


@admin.register(Duplicates)
class Duplicates(admin.ModelAdmin):
    field_names = [field.name for field in Duplicates._meta.fields if field.name != "id"]
    list_display = field_names
    # list_filter = ('type', ParentOrganizationFilter)
    actions = [download_csv]
    search_fields = ('name',)

@admin.register(Profile)
class Profile(admin.ModelAdmin):
    field_names = [field.name for field in Profile._meta.fields if field.name != "id"]
    list_display = field_names
    # list_filter = ('type', ParentOrganizationFilter)
    actions = [download_csv]
    search_fields = ('user__username',)

@admin.register(CustomEmail)
class CustomEmail(admin.ModelAdmin):
    field_names = [field.name for field in CustomEmail._meta.fields if field.name != "id"]
    list_display = field_names
    # list_filter = ('type', ParentOrganizationFilter)
    actions = [download_csv]
    search_fields = ('user__username',)


class UserAdmin(BaseUserAdmin):
    def delete_user_profile(self, request, queryset):
        for u in queryset:
            try:
                Profile.objects.get(user_id=u.id).delete()
            except:
                pass
    def create_profile(self, request, queryset):
        for u in queryset:
            emp = Employee.objects.get(user_id=u.id)
            if not Profile.objects.filter(user_id=u.id):
                Profile.objects.create(
                    user_id=u.id,
                    employee=emp
                )

    def create_profile_and_employee(self, request, queryset):
        for u in queryset:
            emp = Employee.objects.create(
                user_id=u.id,
                full_name=f'{u.first_name} {u.last_name}',
                first_name=u.first_name,
                last_name=u.last_name,
                organization_id=7,
                position_type='Admin',
                slug=slugify(f'{u.first_name}-{u.last_name}-{u.id}')
            )
            if not Profile.objects.filter(user_id=u.id):
                Profile.objects.create(
                    user_id=u.id,
                    employee=emp
                )
    actions = [create_profile_and_employee, delete_user_profile, create_profile]


@admin.register(CustomWageupEmail)
class CustomWageupEmailAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Invite._meta.fields if field.name != "id"]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)