from django.contrib import admin
from .models import *
from root.utilities import download_csv, send_custom_email
from dashboard.models import Std12EReduced
# Register your models here.
from django.contrib import messages
from .views import Arena
from .campaign_metrics import CampaignMetricsHelper
from django.db.models import Count, F, Value as V
from django.db.models import IntegerField,CharField
import datetime as dt

admin.autodiscover()
admin.site.enable_nav_sidebar = False

@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Competition._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Conference._meta.fields if field.name != "id"]
    actions = [download_csv]

@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Division._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Team._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(TeamRanking)
class TeamRankingAdmin(admin.ModelAdmin):
    field_names = [field.name for field in TeamRanking._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    field_names = [field.name for field in Round._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    fields = ['round', 'updated', 'teams', 'division', 'tournament_match']
    list_display = ('round', 'updated', 'get_teams', 'division', 'tournament_match')
    actions = [download_csv]
    def get_teams(self, obj):
        return " vs ".join(obj.teams.all().values_list('name', flat=True))

@admin.register(MatchScores)
class MatchScoresAdmin(admin.ModelAdmin):
    field_names = [field.name for field in MatchScores._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]


@admin.register(ScoreComponent)
class ScoreComponentAdmin(admin.ModelAdmin):
    field_names = [field.name for field in ScoreComponent._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(MatchScoreComponents)
class MatchScoreComponentsAdmin(admin.ModelAdmin):
    field_names = [field.name for field in MatchScoreComponents._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(TeamOrganizationScores)
class TeamOrganizationScoresAdmin(admin.ModelAdmin):
    field_names = [field.name for field in TeamOrganizationScores._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]


@admin.register(TeamEmployeeScores)
class TeamEmployeeScoresAdmin(admin.ModelAdmin):
    field_names = [field.name for field in TeamEmployeeScores._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]


class hasEmail(admin.SimpleListFilter):
    parameter_name = 'email'
    title = 'HAS EMAIL'

    def lookups(self, request, model_admin):

        return (
            ('yes', ('Yes')),
            ('no',  ('No')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(email__isnull=False)

        if self.value() == 'no':
            return queryset.filter(email__isnull=True)

class isRegistered(admin.SimpleListFilter):
    parameter_name = 'registered'
    title = 'Is Registered'

    def lookups(self, request, model_admin):

        return (
            ('yes', ('Yes')),
            ('no',  ('No')),
        )


    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_registered=True)

        if self.value() == 'no':
            return queryset.filter(is_registered=False)

class registrationGroupFilter(admin.SimpleListFilter):
    parameter_name = 'registration_group'
    title = 'Campaign Registration'

    def lookups(self, request, model_admin):
        return (
            ('Reg Grp. Nov', ('Reg Grp. Nov')),
            ('Reg Grp. Dec', ('Reg Grp. Dec')),
            ('Reg Grp. Jan', ('Reg Grp. Jan')),
            ('Reg Grp. Feb', ('Reg Grp. Feb')),
            ('NOT REGISTERED', ('Not Registered'))
        )

    def queryset(self, request, queryset):
        if self.value() in ['Reg Grp. Nov', 'Reg Grp. Dec', 'Reg Grp. Jan', 'Reg Grp. Feb', 'NOT REGISTERED']:
            return queryset.filter(registration_group=self.value())

class cohortStation(admin.SimpleListFilter):
    parameter_name = 'hh5_station_cohort'
    title = 'Station Cohort'

    def lookups(self, request, model_admin):
        return (
            ('Core 65 original', ('Core 65 Original')),
            ('Core 65 expansion', ('Core 65 expansion')),
            ('New 25', ('New 25')),
            ('Other expansion', ('Other'))
        )

    def queryset(self, request, queryset):
        if self.value() in ['Core 65 original', 'Core 65 expansion', 'New 25', 'Other expansion']:
            return queryset.filter(hh5_station_cohort=self.value())

@admin.register(CampaignType)
class CampaignTypeAdmin(admin.ModelAdmin):
    field_names = [field.name for field in CampaignType._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(CampaignMetrics)
class CampaignMetricsAdmin(admin.ModelAdmin):
    field_names = [field.name for field in CampaignMetrics._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

@admin.register(DriverCampaign)
class DriverCampaignAdmin(admin.ModelAdmin):
    exclude = ('slug ',)
    readonly_fields = ['slug']


    field_names = [field.name for field in DriverCampaign._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'site_metrics':
            kwargs['queryset'] = CampaignMetrics.objects.filter(show_on_site_options=True)
        return super(DriverCampaignAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(DriverPayments)
class DriverPaymentsAdmin(admin.ModelAdmin):
    field_names = [field.name for field in DriverPayments._meta.fields if field.name != "id"]
    search_fields = ('driver__full_name',)
    list_filter = ('pay_period__campaign__title',)
    list_display = field_names + ['driver_name', 'driver_org', 'driver_wageup_id', 'driver_aca_id', 'driver_email']

    def driver_name(self, queryset):
        return queryset.driver.full_name

    def driver_org(self, queryset):
        return queryset.driver.organization.name

    def driver_wageup_id(self, queryset):
        return queryset.driver.id

    def driver_aca_id(self, queryset):
        return queryset.driver.login_id

    def driver_email(self, queryset):
        try:
            return queryset.driver.user.email
        except:
            return None

    actions = [download_csv]


@admin.register(PaymentFactors)
class PaymentFactorsAdmin(admin.ModelAdmin):
    field_names = [field.name for field in PaymentFactors._meta.fields if field.name != "id"]
    list_display = field_names + ['driver_name', 'driver_org', 'driver_wageup_id', 'driver_aca_id']
    # search_fields = ('driver__full_name',)

    def driver_name(self, queryset):
        return queryset.driver.full_name

    def driver_org(self, queryset):
        return queryset.driver.organization.name

    def driver_wageup_id(self, queryset):
        return queryset.driver.id

    def driver_aca_id(self, queryset):
        return queryset.driver.login_id

    actions = [download_csv]


@admin.register(PayPeriod)
class PayPeriodAdmin(admin.ModelAdmin):
    field_names = [field.name for field in PayPeriod._meta.fields if field.name != "id"]
    list_display = field_names
    list_filter = ('campaign__title', )


    def mark_paid(self, request, queryset):
        for q in queryset:
            dp = DriverPayments.objects.filter(pay_period=q)
            dp.already_paid = True
            dp.paid_on = dt.datetime.now()
            dp.save()

    def calculate_payment_period_from_site(self, request, queryset):
        for pay_period in queryset:
            arena = Arena()
            arena.user = request.user
            arena.data = {
                'pay_period': pay_period.id,
                'slug': pay_period.campaign.slug
            }
            data = arena.get_registered_data_with_payperiod()
            # for d in data:
            #     print(d)
            # return
            # lookup = {
            #     3 : "Total Earnings (Jul 01 - Aug 30)",
            #     '4a' : "This Period Earnings (Jul 01 - Aug 30)",
            #     '4b': "This Period Earnings (Aug 01 - Aug 30)",
            #     6:  'This Period Earnings (Jun 01 - Aug 31)'
            # }

            def get_necessary_data(x):
                payment = [x for x in x['driverMetrics'] if 'this period earnings' in x['metricTitle'].lower()]
                # paymentb = [x for x in x['driverMetrics'] if x['metricTitle'] == lookup[pay_period.id]]
                # if x['registration_cohort__id'] == 3:
                #     payment = paymenta
                # else:
                #     payment = paymentb
                # payment = paymenta if paymenta != 'N/A' else paymentb
                if len(payment) > 0:
                    payment = payment[0].get('metricValue')
                    payment = float(payment.replace('$', '')) if payment != 'N/A' else 0

                else:
                    print(x)
                    payment = 0
                return {'driver_id': x['driver_id'], 'registration_group_id': x['registration_cohort__id'], 'payment': payment}

            payments = map(get_necessary_data, data)
            # payments = map(get_necessary_data, test)
            driver_payments = {}
            for p in payments:
                if p['payment'] > pay_period.campaign.pay_cap:
                    p['payment'] = pay_period.campaign.pay_cap
                driver_payments[p['driver_id']] = {
                    'payment': p['payment'],
                    'driver_id': p['driver_id'],
                    'pay_period_id': pay_period.id,
                    'registration_group_id': p['registration_group_id']
                }

            dp_q = DriverPayments.objects.filter(already_paid=False, pay_period=pay_period)
            dp_q.delete()
            bulk_dp_q = [DriverPayments(**payment_d) for driver, payment_d in driver_payments.items()]
            DriverPayments.objects.bulk_create(bulk_dp_q)

    def calculate_payment_period(self, request, queryset):
        for pay_period in queryset:
            print(pay_period)
            reg_groups = RegistrationCohort.objects.filter(campaign=pay_period.campaign)
            payment_converter = json.loads(pay_period.campaign.payment_converter)
            metrics = list(pay_period.campaign.metrics.all())
            print(metrics)


            for group in reg_groups:
                drivers = DriverCampaignRegistration.objects.filter(campaign=pay_period.campaign, registration_cohort=group).values_list('driver_id', flat=True)
                # get surveys for group
                print(pay_period.upload_from_date, pay_period.upload_to_date, group.start, group.end)
                surveys = Std12EReduced.objects.filter(is_valid_record=True,
                                                       distribution='Email',
                                                       date_updated_surveys__gte=pay_period.upload_from_date,
                                                       date_updated_surveys__lt=pay_period.upload_to_date,
                                                       sc_dt_surveys__gte=group.start,
                                                       emp_driver_id__in=drivers).annotate(name=F('emp_driver_id__display_name')).values('emp_driver_id_id','name')

                # get metrics and calculate them, then setup payments
                arena = Arena()
                arena.metricData,pf = [],[]
                arena.pay_period = pay_period
                arena.campaign = pay_period.campaign
                arena.surveys = surveys
                driver_payments = {}
                campaign_metrics = CampaignMetricsHelper(arena=arena)
                for m in list(metrics):
                    if m.name not in payment_converter.keys() and m.key not in payment_converter.keys():
                        pass
                    md = campaign_metrics.get_metric_data(m, annotation_only=True)
                    print(md)
                    md['aggregation']['driver_id'] = F('emp_driver_id_id')
                    md['aggregation']['metric_name'] = V(m.name, output_field=CharField())
                    vals = [md['payment_field'], 'driver_id', 'metric_name']
                    print(md['filter'])
                    md_data = list(surveys.filter(**md['filter']).annotate(**md['aggregation']).values(*vals))
                    for d in md_data:
                        print(md['payment_field'], d, d[md['payment_field']], payment_converter)

                        try:
                            payment = d[md['payment_field']] * payment_converter[m.name]
                        except:
                            payment = d[md['payment_field']] * payment_converter[m.key]

                        print(payment, )
                        if not driver_payments.get(d['driver_id']):
                            driver_payments[d['driver_id']] = {
                                'payment': payment,
                                'driver_id': d['driver_id'],
                                'pay_period_id': pay_period.id,
                                'registration_group_id': group.id
                                }
                        else:
                            driver_payments[d['driver_id']]['payment'] += payment

                        if driver_payments[d['driver_id']]['payment'] > pay_period.campaign.pay_period_cap:
                            driver_payments[d['driver_id']]['payment'] = pay_period.campaign.pay_period_cap

                        pf.append({
                            'name': d['metric_name'],
                            'driver_id': d['driver_id'],
                            'payment_value': payment,
                            'upload_from_date': pay_period.upload_from_date,
                            'upload_to_date': pay_period.upload_to_date,
                            'start_date': group.start,
                            'count': d[md['payment_field']]
                        })

                # delete any records we are about tom modify
                dp_q = DriverPayments.objects.filter(already_paid=False, registration_group=group, pay_period=pay_period)
                pf_q = PaymentFactors.objects.filter(driver_payment__in=dp_q)
                pf_q.delete()
                dp_q.delete()

                # bulk insert new driver payment records
                bulk_dp_q = [DriverPayments(**payment_d) for driver, payment_d in driver_payments.items()]
                DriverPayments.objects.bulk_create(bulk_dp_q)

                # bulk insert new payment factors records
                driver_payment_ids = list(DriverPayments.objects.filter(pay_period=pay_period, registration_group=group)\
                    .values('driver_id', 'id'))
                driver_payments_d = {}
                for dpi in driver_payment_ids:
                    driver_payments_d[dpi['driver_id']] = dpi['id']

                [d.update({'driver_payment_id': driver_payments_d[d['driver_id']]}) for d in pf]
                PaymentFactors.objects.bulk_create([PaymentFactors(**q) for q in pf])

                # driver_payouts
            messages.add_message(request, messages.SUCCESS,
                                 'Success. The relevant PaymentFactors and DriverPayments Fields were updated!')
            pay_period.updated = dt.datetime.now()
            pay_period.save()

    actions = [download_csv, calculate_payment_period, mark_paid, calculate_payment_period_from_site]

@admin.register(RegistrationCohort)
class RegistrationCohortAdmin(admin.ModelAdmin):
    field_names = [field.name for field in RegistrationCohort._meta.fields if field.name != "id"]
    field_names.append('service_event_end')
    list_display = field_names
    list_filter = ('campaign__title',)
    readonly_fields = ['service_event_end']
    def service_event_end(self, obj):
        return obj.campaign.end

    actions = [download_csv]


@admin.register(DriverCampaignRegistration)
class DriverCampaignRegistrationAdmin(admin.ModelAdmin):
    field_names = [field.name for field in DriverCampaignRegistration._meta.fields if field.name != "id"]
    list_display = field_names
    actions = [download_csv]
    list_filter = ('campaign__title', )


@admin.register(CampaignEligibility)
class CampaignEligibilityAdmin(admin.ModelAdmin):
    field_names = [field.name for field in CampaignEligibility._meta.fields if field.name != "id"]
    list_display = field_names + ['territory']
    raw_id_fields = ("organization", )
    list_filter = ('campaign__title', )


    def territory(self, object):
        return object.organization.parent.parent.name

    actions = [download_csv]


@admin.register(CampaignRegistrationStatus)
class DriverCampaignRegistrationStatusAdmin(admin.ModelAdmin):

    field_names = [field.name for field in CampaignRegistrationStatus._meta.fields if field.name not in ['driver_id', 'id']]
    list_display = field_names
    list_display.insert(2, 'aaane_driver_id')
    list_display.insert(3, 'wageup_driver_id')

    search_fields = ('driver_name', 'organization', 'territory', 'raw_data_driver_id')
    list_filter = ['campaign_title', 'is_registered', 'registration_date', hasEmail]

    def aaane_driver_id(self, obj):
        return obj.driver.raw_data_driver_id

    def wageup_driver_id(self, obj):
        return obj.driver_id

    def unregister_driver(self, request, queryset):
        for q in queryset:
            d = DriverCampaignRegistration.objects.filter(driver_id=q.driver_id, campaign__title=q.campaign_title)
            d.delete()

    def register_driver_amazon(self, request, queryset):
        for q in queryset:
            campaign = DriverCampaign.objects.get(title=q.campaign_title, active=True)
            registration_cohort = RegistrationCohort.objects.get(registration_start__lte=dt.datetime.today(),
                                                                 end__gt=dt.datetime.today(),
                                                                 campaign=campaign)
            reg = DriverCampaignRegistration.objects.create(
                registration_cohort=registration_cohort,
                campaign=campaign,
                driver_id=q.driver_id,
                preferred_payment_method='amazon gift card',
                registration_date=dt.datetime.now()
            )

    def register_driver_bank(self, request, queryset):
        for q in queryset:
            campaign = DriverCampaign.objects.get(title=q.campaign_title, active=True)
            registration_cohort = RegistrationCohort.objects.get(registration_start__lte=dt.datetime.today(),
                                                                 end__gt=dt.datetime.today(),
                                                                 campaign=campaign)
            reg = DriverCampaignRegistration.objects.create(
                registration_cohort=registration_cohort,
                campaign=campaign,
                driver_id=q.driver_id,
                preferred_payment_method='bank deposit',
                registration_date=dt.datetime.now()
            )

    def exclude_driver(self, request, queryset):
        for q in queryset:
            exclude = DriverCampaignExclusion.objects.create(employee_id=q.driver_id)

    def register_duplicate_driver(self, request, queryset):

        for driver in queryset:
            # get driver with user account

            campaign = DriverCampaign.objects.get(title=driver.campaign_title)
            driver_emp = Employee.objects.get(id=driver.driver_id)

            related_user_employee = None
            for related_employee in driver_emp.get_related_employee():
                if related_employee.user is not None:
                    related_user_employee = related_employee
                    break

            print(related_user_employee)
            if related_user_employee is None:
                messages.add_message(request, messages.WARNING, 'That didnt work. There are no related employees with user accounts for {}'.format(driver.employee.full_name))
                break

            related_campaign_registration = DriverCampaignRegistration.objects.get(driver=related_user_employee, campaign=campaign)

            dcr = DriverCampaignRegistration.objects.create(
                campaign = campaign,
                driver =driver_emp,
                registration_cohort=related_campaign_registration.registration_cohort,
                registration_date = related_campaign_registration.registration_date,
                preferred_payment_method= related_campaign_registration.preferred_payment_method
            )

    actions = [download_csv, register_driver_amazon,
               register_driver_bank, exclude_driver,
               unregister_driver, register_duplicate_driver]

# @admin.register(hh5_drivers)
# class HH5_DriversAdmin(admin.ModelAdmin):
#     field_names = [field.name for field in hh5_drivers._meta.fields if field.name != "id"]
#     list_display = field_names
#     ordering = ('-date_joined', 'station_name')
#     list_filter = (hasEmail, isRegistered, registrationGroupFilter, cohortStation)
#     search_fields = ('driver_name', 'station_name', 'org__parent__name', 'registration_group')
#     list_display.insert(2, 'territory')
#     list_display.insert(1, 'driver_employee_id')
#
#     def send_employee_custom_email_hh5(self, request, queryset):
#         for q in queryset:
#             email = q.email
#             send_custom_email(request, q, email, 'hh5')
#
#
#     def mark_registered(self, request, queryset):
#         for driver in queryset:
#             CampaignUser.objects.create(
#                 reward='amazon',
#                 email=driver.employee.user.email,
#                 campaign_id=1,
#                 user=driver.employee.user,
#                 employee = driver.employee,
#                 updated = dt.datetime.now(), #TODO: note may have a timezone issue here
#             )
#
#     def mark_registered_duplicate(self, request, queryset):
#         for driver in queryset:
#             # get driver with user account
#             related_user = None
#             for related_employee in driver.employee.get_related_employee():
#                 if related_employee.user is not None:
#                     related_user = related_employee.user
#                     break
#
#             print(related_user)
#             if related_user is None:
#                 messages.add_message(request, messages.WARNING, 'That didnt work. There are no related employees with user accoutn for {}'.format(driver.employee.full_name))
#                 break
#
#             related_campaign_user = CampaignUser.objects.get(user=related_user)
#
#             cu = CampaignUser.objects.create(
#                 reward=related_campaign_user.reward,
#                 email=related_campaign_user.email,
#                 campaign_id=1,
#                 user=related_user,
#                 employee=driver.employee,
#                 updated=related_campaign_user.updated,  # TODO: note may have a timezone issue here
#             )
#
#             cu.updated = related_campaign_user.updated
#             cu.save()
#
#
#
#     def save_model(self, request, obj, form, change):
#         print(obj.email)
#         print(obj.employee.id)
#         if change:
#             try:
#                 user = obj.employee.user
#                 user.email = obj.email
#                 user.save()
#                 messages.add_message(request, messages.INFO, 'Email was updated successfully')
#             except Exception as e:
#                 messages.add_message(request, messages.WARNING, 'That didnt work. Is this person a user already?')
#                 print(e)
#
#
#         # super(HH5_DriversAdmin, self).save_model(request, obj, form, change)
#
#     def make_reward_bank(self, request, queryset):
#         for driver in queryset:
#             camp_driver = CampaignUser.objects.get(employee=driver.employee)
#             camp_driver.reward = 'bank'
#             camp_driver.save()
#
#     def make_reward_amazon(self, request, queryset):
#         for driver in queryset:
#             camp_driver = CampaignUser.objects.get(employee=driver.employee)
#             camp_driver.reward = 'amazon'
#             camp_driver.save()
#
#     def email_campaign_invite(self, request, queryset):
#         for q in queryset:
#             print(q)
#             q.email_campaign_invite()
#
#     def email_campaign_invite_using_registration_email(self, request, queryset):
#         for q in queryset:
#             print(q)
#             q.email_campaign_invite_using_registration_email()
#
#     def email_core_hh5_extension_email(self, request, queryset):
#         for q in queryset:
#             print(q)
#             q.email_core_hh5_extension_email()
#
#     actions = [download_csv,
#                email_campaign_invite,
#                email_campaign_invite_using_registration_email,
#                email_core_hh5_extension_email,
#                mark_registered,
#                mark_registered_duplicate,
#                make_reward_amazon,
#                make_reward_bank,
#                send_employee_custom_email_hh5
#                ]
