from django.db.models import Q, F, Avg, Count, Sum, Min, Max, Func, Case, CharField, Value, When
from django.db.models import Value as V
from django.db.models.functions import Cast, TruncDate, Coalesce, TruncHour, Concat, ExtractHour
from django.db.models.fields import DateField
from dashboard.models import *
from accounts.models import *

from dashboard.serializers import *
from accounts.serializers import *
import datetime as dt

'''
Directory:
1. Create Schedule for the day
2. Create Schedule for the week
3. Reports
4. Templates
5. Other
'''

weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

def get_duration(start, end):
    # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
    d_start = (start.hour + (start.minute / 60))
    d_end = (end.hour + (end.minute / 60))
    if d_start > d_end:
        duration = ((d_end + 24) - d_start)
    else:
        duration = (d_end - d_start)
    return duration

def get_end_date(start, end, date):
    if start.hour >= end.hour:
        schedule_date = date + dt.timedelta(days=1)
    else:
        schedule_date = date
    schedule_date = schedule_date.replace(hour=end.hour, minute=end.minute)
    print(end.hour, end.minute, schedule_date)
    return schedule_date



def get_service_type(tc, ls):
    print(tc, ls)
    if tc == None:
        if ls != 'All':
            return ls
        else:
            return 'Tow'
    if ls == 'All':
        if ', ' in tc:
            all_tc = tc.split(', ')
            return all_tc[0]
        elif tc == '':
            return 'Tow'
        else:
            return tc
    if ls != 'Light Service':
        if tc in ls and ', ' in tc:
            return ls
        else:
            return tc
    else:
        return tc
def get_employee_list(object):
    if object.type == 'Territory':
        org_set = object.children()
        employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
    else:
        employees = Employee.objects.filter(organization=object.employees_under).exclude(
            active=0).values_list('id', flat=True)

    employees = EmployeeProfile.objects.filter(employee_id__in=employees.values_list('id', flat=True)).exclude(
        active=0)
    employees_list = employees.values_list('employee_id', flat=True)
    return employees_list

def save_daily_schedule(date, drivers, object):
    employees_list = get_employee_list(object)
    ghost_list = PlaceholderDriver.objects.filter(organization_id=object.id).values_list('id', flat=True)
    print(date)
    SchedulerReviewByDriver.objects.filter(
        Q(date=date) & (Q(employee_id__in=employees_list) | Q(placeholder_id__in=ghost_list))).delete()

    scheduled_drivers_review = SchedulerReviewByDriver.objects.bulk_create(
        [SchedulerReviewByDriver(
            employee=d.employee,
            date=d.start_date.date(),
            starting_time=d.start_date,
            ending_time=d.end_date,
            duration=get_duration(d.start_date, d.end_date),
            tcd=d.schedule_type,
            off=False,
            placeholder=d.placeholder
        ) for d in drivers]
    )
    print('saved Daily Schedule', scheduled_drivers_review)

def get_sun_sat(date):
    if date.weekday() == 6:
        add_days = 0
    else:
        add_days = date.weekday() + 1
    sunday = date - dt.timedelta(days=add_days)
    saturday = sunday + dt.timedelta(days=6)
    return [sunday, saturday]

def get_start_date(g, weekday):
    if weekday == 'Sunday': return g.sun_start
    if weekday == 'Monday': return g.mon_start
    if weekday == 'Tuesday': return g.tue_start
    if weekday == 'Wednesday': return g.wed_start
    if weekday == 'Thursday': return g.thu_start
    if weekday == 'Friday': return g.fri_start
    if weekday == 'Saturday': return g.sat_start

def get_ghost_end_date(g, weekday):
    if weekday == 'Sunday': return g.sun_end
    if weekday == 'Monday': return g.mon_end
    if weekday == 'Tuesday': return g.tue_end
    if weekday == 'Wednesday': return g.wed_end
    if weekday == 'Thursday': return g.thu_end
    if weekday == 'Friday': return g.fri_end
    if weekday == 'Saturday': return g.sat_end

##########################################
##### 1. Create Schedule for the day #####
##########################################
def save_schedule(date, params, object):
    # saves the scheduled drivers to the schedule.
    action_url = '/dashboard/{0}?section=scheduler'.format(object.slug)
    try:
        drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()
    except:
        pass

    new_drivers = params['drivers']

    def get_proper_id(did, obj):
        if did is None:
            return None
        else:
            if obj == 'employee':
                return Employee.objects.get(id=did)
            else:
                return PlaceholderDriver.objects.get(id=did)

    all_new_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
        [TimeseriesScheduledDrivers(
            employee=get_proper_id(d['employee'], 'employee'),
            start_date=dt.datetime.strptime(d['start_date'], '%Y-%m-%d %H:%M'),
            duration=d['duration'] / 4,
            end_date=get_end_date(d['start_date'], d['duration']),
            schedule_type=d['schedule_type'],
            schedule=schedule,
            placeholder=get_proper_id(d['placeholder'], 'placeholder')
        ) for d in new_drivers]
    )
    save_daily_schedule(date, all_new_drivers, object)
    schedule.publish = params['publish']
    schedule.save()

    return {'success': True}

def use_prev_day(date, params, object):
    yesterday = date - dt.timedelta(days=1)
    yesterday_schedule = TimeseriesSchedule.objects.get(date=yesterday, organization_id=object.id)
    scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=yesterday_schedule)
    try:
        schedule = TimeseriesSchedule.objects.get_or_create(organization_id=object.id, date=date)[0]
    except:
        schedules = TimeseriesSchedule.objects.filter(organization_id=object.id, date=date)
        schedule = schedules[0]

    del_drivers_shcedule = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()

    drivers = TimeseriesScheduledDrivers.objects.bulk_create(
        [TimeseriesScheduledDrivers(
            employee=d.employee,
            start_date=d.start_date + dt.timedelta(days=1),
            end_date=d.end_date + dt.timedelta(days=1),
            duration=d.duration,
            schedule_type=d.schedule_type,
            schedule=schedule,
            placeholder=d.placeholder
        ) for d in scheduled_drivers]
    )
    save_daily_schedule(date, drivers, object)
    drivers_s = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
    output = TimeseriesScheduledDiversTemplateSerializer(drivers_s).data
    return output

def user_profile_day(date, params, object):
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday = weekdays[date.weekday()]
    service_types = ['Tow', 'Battery', 'Light Service']
    ls_as = params['ls_as']
    has_ghost = params['withGhost']
    if ls_as == 'Tow':
        service_types = ['Tow', 'Tow, Light Service', 'Light Service, Tow', 'Battery', 'Light Service']
    elif ls_as == 'Battery':
        service_types = ['Tow', 'Battery', 'Battery, Light Service', 'Light Service, Battery', 'Light Service']

    try:
        schedule = TimeseriesSchedule.objects.get_or_create(organization_id=object.id, date=date)[0]
    except:
        schedules = TimeseriesSchedule.objects.filter(organization_id=object.id, date=date)
        schedule = schedules[0]

    del_drivers_shcedule = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()

    if object.type == 'Territory':
        org_set = object.children()
        employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
    else:
        employees = Employee.objects.filter(organization=object.employees_under).exclude(
            active=0).values_list('id', flat=True)
    profiles = EmployeeProfile.objects.filter(employee_id__in=employees)

    if ls_as == 'All':
        pass
    elif ls_as != 'Light Service':
        profiles = profiles.filter(Q(trouble_code_type__in=['Tow', 'Battery', 'Light Service']) | Q(trouble_code_type__contains=ls_as))
    else:
        profiles = profiles.filter(trouble_code_type__in=['Tow', 'Battery', 'Light Service'])
    profiles = profiles.values_list('id', flat=True)
    # profiles = EmployeeProfile.objects.filter(employee_id__in=employees,
    #                                           trouble_code_type__in=service_types).exclude(
    #     Q(active=0) | Q(active_not_available=1)).values_list('id', flat=True)
    entries = EmployeeProfileEntries.objects.filter(driver_profile__in=list(profiles),
                                                    day_of_week=weekday).exclude(start_time=None)

    schedule_date = date
    pto_entries = EmployeeProfileEntries.objects.filter(pto_end__gte=schedule_date,
                                                        pto_start__lte=schedule_date,
                                                        driver_profile__in=list(profiles)).values_list(
        'driver_profile__employee_id', flat=True)
    entries = entries.exclude(end_time=None)
    entries = entries.exclude(type='is not available')
    schedule_date = date
    schedule = TimeseriesSchedule.objects.get_or_create(date=schedule_date, organization_id=object.id)[0]
    scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
    if scheduled_drivers.count() > 0:
        scheduled_drivers.delete()

    all_new_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
        [TimeseriesScheduledDrivers(
            employee=e.driver_profile.employee,
            start_date=schedule_date.replace(hour=e.start_time.hour, minute=e.start_time.minute),
            end_date=get_end_date(e.start_time, e.end_time, schedule_date),
            duration=get_duration(e.start_time, e.end_time),
            schedule_id=schedule.id,
            schedule_type=get_service_type(e.driver_profile.trouble_code_type, ls_as)
        ) for e in entries if e.driver_profile.employee.id not in pto_entries]
    )
    print('drivers saved', all_new_drivers)

    ghost_days = {
        'Sunday': {'start': 'sun_start', 'end': 'sun_end', 'av': 'sun_available'},
        'Monday': {'start': 'mon_start', 'end': 'mon_end', 'av': 'mon_available'},
        'Tuesday': {'start': 'tue_start', 'end': 'tue_end', 'av': 'tue_available'},
        'Wednesday': {'start': 'wed_start', 'end': 'wed_end', 'av': 'wed_available'},
        'Thursday': {'start': 'thu_start', 'end': 'thu_end', 'av': 'thu_available'},
        'Friday': {'start': 'fri_start', 'end': 'fri_end', 'av': 'fri_available'},
        'Saturday': {'start': 'sat_start', 'end': 'sat_end', 'av': 'sat_available'},
    }



    if has_ghost is True:
        print('ghost is true')
        all_placeholders = PlaceholderDriver.objects.filter(organization_id=object.id)
        q = {ghost_days[weekday]['av']: 1}
        all_placeholders = all_placeholders.filter(**q)
        ghost_date = date
        print(all_placeholders)
        all_ghost_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
            [TimeseriesScheduledDrivers(
                placeholder=g,
                start_date=ghost_date.replace(hour=get_start_date(g, weekday).hour, minute=get_start_date(g).minute),
                end_date=get_end_date(get_start_date(g, weekday), get_ghost_end_date(g, weekday), ghost_date),
                duration=get_duration(get_start_date(g, weekday), get_ghost_end_date(g, weekday)),
                schedule_id=schedule.id,
                schedule_type=get_service_type(g.service_type, ls_as)
            ) for g in all_placeholders]
        )
        for g in all_ghost_drivers:
            all_new_drivers.append(g)
    save_daily_schedule(date, all_new_drivers, object)
    output = TimeseriesScheduledDriversSerializer(all_new_drivers, many=True)
    print(output)


    return output.data

###########################################
##### 2. Create Schedule for the week #####
###########################################
### Week using employee profiler
def schedule_with_profiler(date, params, object):
    if date.weekday() == 6:
        add_days = 0
    else:
        add_days = date.weekday() + 1
    sunday = date - dt.timedelta(days=add_days)
    saturday = sunday + dt.timedelta(days=6)
    service_types = ['Tow', 'Battery', 'Light Service']
    ls_as = params['ls_as']
    has_ghost = params['withGhost']
    # if ls_as == 'Tow':
    #     service_types = ['Tow', 'Tow, Light Service', 'Light Service, Tow', 'Battery', 'Light Service']
    # elif ls_as == 'Battery':
    #     service_types = ['Tow', 'Battery', 'Battery, Light Service', 'Light Service, Battery', 'Light Service']
    if object.type == 'Territory':
        org_set = object.children()
        employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
    else:
        employees = Employee.objects.filter(organization=object.employees_under).exclude(
            active=0).values_list('id', flat=True)
    profiles = EmployeeProfile.objects.filter(employee_id__in=employees)
    print('current light service as', ls_as)
    if ls_as == 'All':
        pass
    elif ls_as != 'Light Service':
        profiles = profiles.filter(Q(trouble_code_type__in=['Tow', 'Battery', 'Light Service']) | Q(trouble_code_type__contains=ls_as))
    else:
        profiles = profiles.filter(trouble_code_type__in=['Tow', 'Battery', 'Light Service'])

    profiles = profiles.exclude(Q(active=0) | Q(active_not_available=1)).values('id', 'employee_id')
    unique_profile = {}
    for p in profiles:
        if p['id'] not in unique_profile:
            unique_profile[p['id']] = p['employee_id']

    profiles = unique_profile
    ghost_days = {
        'Sunday': {'start': 'sun_start', 'end': 'sun_end', 'av': 'sun_available'},
        'Monday': {'start': 'mon_start', 'end': 'mon_end', 'av': 'mon_available'},
        'Tuesday': {'start': 'tue_start', 'end': 'tue_end', 'av': 'tue_available'},
        'Wednesday': {'start': 'wed_start', 'end': 'wed_end', 'av': 'wed_available'},
        'Thursday': {'start': 'thu_start', 'end': 'thu_end', 'av': 'thu_available'},
        'Friday': {'start': 'fri_start', 'end': 'fri_end', 'av': 'fri_available'},
        'Saturday': {'start': 'sat_start', 'end': 'sat_end', 'av': 'sat_available'},
    }
    for i in range(len(weekdays)):
        print('day', weekdays[i])
        entries = EmployeeProfileEntries.objects.filter(driver_profile__in=list(profiles),
                                                        day_of_week=weekdays[i]).exclude(start_time=None)
        schedule_date = sunday + dt.timedelta(days=i)
        pto_entries = EmployeeProfileEntries.objects.filter(pto_end__gte=schedule_date,
                                                            pto_start__lte=schedule_date,
                                                            driver_profile__in=list(profiles)).values_list(
            'driver_profile__employee_id', flat=True)
        entries = entries.exclude(end_time=None)
        entries = entries.exclude(type='is not available')

        schedule = TimeseriesSchedule.objects.get_or_create(date=schedule_date, organization_id=object.id)[
            0]
        scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
        print('drivers to delete', scheduled_drivers.count())
        scheduled_drivers.delete()

        all_new_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
            [TimeseriesScheduledDrivers(
                employee=e.driver_profile.employee,
                start_date=schedule_date.replace(hour=e.start_time.hour, minute=e.start_time.minute),
                end_date=get_end_date(e.start_time, e.end_time, schedule_date),
                duration=get_duration(e.start_time, e.end_time),
                schedule_id=schedule.id,
                schedule_type=get_service_type(e.driver_profile.trouble_code_type, ls_as)
            ) for e in entries if e.driver_profile.employee.id not in pto_entries]
        )

        if has_ghost == True:
            print('ghost is true')
            all_placeholders = PlaceholderDriver.objects.filter(organization_id=object.id)
            q = {ghost_days[weekdays[i]]['av']: 1}
            all_placeholders = all_placeholders.filter(**q)
            print(all_placeholders)
            ghost_date = date
            all_ghost_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                [TimeseriesScheduledDrivers(
                    placeholder=g,
                    start_date=ghost_date.replace(hour=get_start_date(g, weekdays[i]).hour,
                                                  minute=get_start_date(g, weekdays[i]).minute),
                    end_date=get_end_date(get_start_date(g, weekdays[i]), get_ghost_end_date(g, weekdays[i]), ghost_date),
                    duration=get_duration(get_start_date(g, weekdays[i]), get_ghost_end_date(g, weekdays[i])),
                    schedule_id=schedule.id,
                    schedule_type=get_service_type(g.service_type, ls_as)
                ) for g in all_placeholders]
            )
            for g in all_ghost_drivers:
                all_new_drivers.append(g)

        print('drivers saved', len(all_new_drivers))
        print(date)

        # action_display = 'Created schedule using Driver Profiler for the week of {0} for {1}'.format(
        #     sunday.strftime('%m/%d/%Y'), self.object.name)
        # ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

        save_daily_schedule(schedule_date, all_new_drivers, object)

##########################################
############# 3. Reports #################
##########################################
def schedule(date, params, object):
    [sunday, saturday] = get_sun_sat(date)
    employees_list = get_employee_list(object)
    ghost_drivers = PlaceholderDriver.objects.filter(organization_id=object.id).values_list('id', flat=True)
    week_schedule = SchedulerReviewByDriver.objects.filter(Q(date__range=[sunday.date(), saturday.date()]),
                                                           Q(employee_id__in=employees_list) | Q(
                                                               placeholder_id__in=ghost_drivers))
    unpublished = TimeseriesSchedule.objects.filter(organization_id=object.id,
                                                    date__range=[sunday.date(), saturday.date()], publish=False)
    output_unpub = unpublished.values('id', 'date', 'publish')
    output = []
    output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
        total_hours=Sum('duration'),
        alt_name=F('placeholder__name'),
        full_name=F('employee__full_name'))
                           .values('date', 'starting_time',
                                   'ending_time', 'duration',
                                   'tcd', 'full_name', 'total_hours', 'alt_name').order_by('full_name',
                                                                                           'alt_name'))
    from itertools import groupby
    dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
    for k, v in groupby(output_schedule,
                        key=lambda x: x['full_name'] if (x['full_name'] is not None) else x['alt_name']):
        sorted_schedule = list(v)
        overnight_time = ''
        for s in sorted_schedule:
            starting_hour = int(s['starting_time'].strftime('%H'))
            ending_hour = int(s['ending_time'].strftime('%H'))
            # if starting_hour > ending_hour:
                # display_value = s['starting_time']
            display_value = f"{s['starting_time'].strftime('%H')}@@ {s['starting_time'].strftime('%I:%M %p')} - {s['ending_time'].strftime('%I:%M %p')}"
            s.update({'display': display_value})
            # try:
            #     s.update({'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
            #         '%H:%M')
            #                          + ' -\n' + s['ending_time'].strftime('%H:%M')
            #                          + '\n(' + s['tcd'] + ')'})
            # except:
            #     s.update({'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
            #         '%H:%M')
            #                          + ' -\n' + s['ending_time'].strftime('%H:%M')})

        missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off'}
                         for d in dates if d not in
                         [d['date'] for d in sorted_schedule]]

        sorted_schedule = sorted_schedule + missing_dates
        sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

        output.append({'schedule': sorted_schedule[0],
                       'total_hours': sum([x['total_hours'] for x in sorted_schedule[0]])})
    try:
        template_schedule = TimeseriesScheduleTemplate.objects.filter(organization_id=object.id)[0]
        output_template = TimeseriesScheduleTemplateSerializer(template_schedule).data
    except:
        output_template = None

    template_list = TimeseriesScheduleTemplate.objects.filter(organization_id=object.id).values('id',
                                                                                                     'template_name')
    return {'schedule': output, 'schedule_dates': dates, 'unpublished': output_unpub,
            'template_schedule': output_template, 'all_templates': template_list}

def weekly_schedule_split(date, params, object):
    [sunday, saturday] = get_sun_sat(date)
    employees_list = get_employee_list(object)
    ghost_drivers = PlaceholderDriver.objects.filter(organization_id=object.id).values_list('id', flat=True)
    week_schedule = SchedulerReviewByDriver.objects.filter(Q(date__range=[sunday.date(), saturday.date()]),
                                                           Q(employee_id__in=employees_list) | Q(
                                                               placeholder_id__in=ghost_drivers))
    output = []
    output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
        total_hours=Sum('duration'),
        alt_name=F('placeholder__name'),
        full_name=F('employee__full_name'))
                           .values('date', 'starting_time',
                                   'ending_time', 'duration',
                                   'tcd', 'full_name', 'total_hours', 'alt_name').order_by('full_name',
                                                                                           'alt_name'))
    from itertools import groupby
    dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
    week_split = {}
    for i in range(len(dates)):
        day_schedule = SchedulerReviewByDriver.objects.filter(Q(date=dates[i]),
                                                              Q(employee_id__in=employees_list) | Q(
                                                                  placeholder_id__in=ghost_drivers))

        overnight_start_time = dt.datetime.combine(dates[i], dt.datetime.min.time())
        overnight = SchedulerReviewByDriver.objects.filter(
            Q(date=dates[i] - dt.timedelta(days=1)) & Q(ending_time__gt=overnight_start_time),
            Q(employee_id__in=employees_list) | Q(placeholder_id__in=ghost_drivers))
        overnight_schedule = list(overnight.values('employee_id', 'date').annotate(
            total_hours=Sum('duration'),
            alt_name=F('placeholder__name'),
            full_name=F('employee__full_name'))
                                  .values('date', 'starting_time',
                                          'ending_time', 'duration',
                                          'tcd', 'full_name', 'total_hours', 'alt_name').order_by('-ending_time',
                                                                                                  'tcd', 'full_name',
                                                                                                  'alt_name'))
        day_schedule = list(day_schedule.values('employee_id', 'date').annotate(
            total_hours=Sum('duration'),
            alt_name=F('placeholder__name'),
            full_name=F('employee__full_name'))
                            .values('date', 'starting_time',
                                    'ending_time', 'duration',
                                    'tcd', 'full_name', 'total_hours', 'alt_name').order_by('starting_time', 'tcd',
                                                                                            'full_name',
                                                                                            'alt_name'))
        print('overnight scheduler', overnight_schedule)
        if overnight_schedule:
            [day_schedule.insert(0, x) for x in overnight_schedule]
            # day_schedule = overnight_schedule.extend(day_schedule)

        week_split[dates[i].strftime('%Y-%m-%d')] = day_schedule
    for k, v in groupby(output_schedule,
                        key=lambda x: x['full_name'] if (x['full_name'] is not None) else x['alt_name']):
        sorted_schedule = list(v)
        for s in sorted_schedule:
            try:
                s.update({'display': s['starting_time'].strftime('%H:%M')
                                     + '-' + s['ending_time'].strftime('%H:%M')
                                     + ' (' + s['tcd'] + ')'})
            except:
                s.update({'display': s['starting_time'].strftime('%H:%M')
                                     + '-' + s['ending_time'].strftime('%H:%M')})

        missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off'}
                         for d in dates if d not in
                         [d['date'] for d in sorted_schedule]]

        sorted_schedule = sorted_schedule + missing_dates
        sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

        output.append({'schedule': sorted_schedule[0],
                       'total_hours': sum([x['total_hours'] for x in sorted_schedule[0]])})

    return {'full_schedule': output, 'split_schedule': week_split}

# publish function for my tool kit drivers/users can see their schedule
def publish(date, params, object):
    # params['publish'] = an array of TimeseriesSchedule ids
    pub_schedule = TimeseriesSchedule.objects.filter(id__in=params['publish'])
    for p in pub_schedule:
        p.publish = True
        p.save()

    return {'schedule_published': True}

# DAILY CALL VOLUME/DRIVERS NEEDED
def summed_predictions(date, params, object):
    view_type = params['view_by']
    start_date = date
    end_date = date + dt.timedelta(days=13, hours=23, minutes=59)
    tc = params['trouble_code']
    metric = params['metric']  # volume_pred or total_drivers

    if object.facility_type != 'Fleet' and object.type == 'Territory':
        data_for = [child.id for child in object.children()]
        data_for.append(object.id)
    else:
        if 'fleetAvl' in params:
            data_for = params.get('fleetAvlId', object.id)
        else:
            data_for = object.id

    if view_type == 'four_hour':
        try:
            predictions = TimeseriesPredictionsHourly.objects.filter(organization_id__in=data_for)
        except:
            predictions = TimeseriesPredictionsHourly.objects.filter(organization_id=data_for)
    else:
        try:
            predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id__in=data_for)
        except:
            predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id=data_for)

    # for territory level that is not fleet
    if object.type == 'Territory' and object.facility_type != 'Fleet':
        output = {}
        if tc == 'all':
            if metric == 'volume_pred':
                total_pred = predictions.filter(sc_dt__range=[start_date, end_date]) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date') \
                    .annotate(total=Sum(metric)) \
                    .order_by('date')

                predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'organization_id') \
                    .annotate(total_predictions=Sum(metric)) \
                    .order_by('organization_id')
            else:
                predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'organization_id') \
                    .annotate(max_tow=Coalesce(Max(metric, filter=Q(code='Tow')), 0),
                              max_bat=Coalesce(Max(metric, filter=Q(code='Battery')), 0),
                              max_ls=Coalesce(Max(metric, filter=Q(code='Other')), 0)) \
                    .annotate(total_predictions=F('max_tow') + F('max_bat') + F('max_ls')) \
                    .order_by('organization_id')

        else:
            print('list of code', tc)
            if tc == 'tow_light_service':
                code = ['Tow', 'Other']
            elif tc == 'battery_light_service':
                code = ['Battery', 'Other']
            elif tc == 'Light Service':
                code = ['Other']
            else:
                code = [tc]

            if metric == 'volume_pred':
                predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'organization_id') \
                    .annotate(total_predictions=Sum(metric)) \
                    .order_by('organization_id')
            else:
                predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'organization_id')
                if tc == 'tow_light_service':
                    predictions = predictions \
                        .annotate(max_tow=Max(metric, filter=Q(code='Tow')),
                                  max_ls=Max(metric, filter=Q(code='Other'))) \
                        .annotate(total_predictions=F('max_tow') + F('max_ls')) \
                        .order_by('organization_id')

                elif tc == 'battery_light_service':
                    predictions = predictions \
                        .annotate(max_bat=Max(metric, filter=Q(code='Battery')),
                                  max_ls=Max(metric, filter=Q(code='Other'))) \
                        .annotate(total_predictions=F('max_bat') + F('max_ls')) \
                        .order_by('organization_id')
                elif tc == 'Light Service':
                    predictions = predictions \
                        .annotate(total_predictions=Max(metric, filter=Q(code='Other'))) \
                        .order_by('organization_id')
                else:
                    predictions = predictions \
                        .annotate(total_predictions=Max(metric, filter=Q(code=tc))) \
                        .order_by('organization_id')
                print(predictions)
        total_summed = {}
        for p in predictions:
            if p['organization_id'] in output:
                output[p['organization_id']]['data'].append(
                    {'value': p['total_predictions'], 'label': p['date']})
                if str(p['date'].strftime('%Y-%m-%d')) in total_summed:
                    total_summed[str(p['date'].strftime('%Y-%m-%d'))]['value'] += p['total_predictions']
                else:
                    total_summed[str(p['date'].strftime('%Y-%m-%d'))] = {'label': p['date'],
                                                                         'value': p['total_predictions']}
            else:
                organization = Organization.objects.get(id=p['organization_id'])
                output[p['organization_id']] = {
                    'rowLink': '/dashboard/{0}?section=scheduler'.format(organization.slug),
                    'data': [
                        {'label': 'Station-Business', 'value': organization.name},
                        {'label': p['date'], 'value': p['total_predictions']}
                    ]
                }
                if str(p['date'].strftime('%Y-%m-%d')) in total_summed:
                    total_summed[str(p['date'].strftime('%Y-%m-%d'))]['value'] += p['total_predictions']
                else:
                    total_summed[str(p['date'].strftime('%Y-%m-%d'))] = {'label': p['date'],
                                                                         'value': p['total_predictions']}
        # total_value = list([{'value': t['value'], 'label': t['label']} for t in total_summed])
        total_value = list(total_summed.values())

        output['9999999'] = {
            'rowLink': '#',
            'data': [
                {'label': 'Station-Business', 'value': 'Total'},
                *total_value
            ]
        }
        return list(output.values())

    else:
        output = {}
        if tc == 'all':
            if metric == 'volume_pred':
                predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'sc_dt', 'organization_id') \
                    .annotate(total_predictions=Sum(metric)) \
                    .order_by('sc_dt')
            else:
                predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'sc_dt', 'organization_id') \
                    .annotate(max_tow=Coalesce(Max(metric, filter=Q(code='Tow')), 0),
                              max_bat=Coalesce(Max(metric, filter=Q(code='Battery')), 0),
                              max_ls=Coalesce(Max(metric, filter=Q(code='Other')), 0)) \
                    .annotate(total_predictions=F('max_tow') + F('max_bat') + F('max_ls')) \
                    .order_by('sc_dt')
                # .annotate(total_predictions=(((0, F('max_tow'))[isinstance(F('max_tow'), int)]) +
                #                              ((0, F('max_bat'))[isinstance(F('max_bat'), int)])))\

                # .annotate(total_predictions=(0 if F('max_tow') is None else F('max_tow')) +
                #                             (0 if F('max_bat') is None else F('max_bat')) +
                #                             (0 if F('max_ls') is None else F('max_ls'))) \

        else:
            if tc == 'tow_light_service':
                code = ['Tow', 'Other']
            elif tc == 'battery_light_service':
                code = ['Battery', 'Other']
            elif tc == 'Light Service':
                code = ['Other']
            else:
                code = [tc]

            print('trouble code', tc)

            if metric == 'volume_pred':
                predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'sc_dt', 'organization_id') \
                    .annotate(total_predictions=Sum(metric)) \
                    .order_by('sc_dt')
            else:
                predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                    .annotate(date=Cast('sc_dt', DateField())) \
                    .values('date', 'sc_dt', 'organization_id')

                if tc == 'tow_light_service':
                    predictions = predictions \
                        .annotate(max_tow=Max(metric, filter=Q(code='Tow')),
                                  max_ls=Max(metric, filter=Q(code='Other'))) \
                        .annotate(total_predictions=F('max_tow') + F('max_ls')) \
                        .order_by('sc_dt')

                elif tc == 'battery_light_service':
                    predictions = predictions \
                        .annotate(max_bat=Max(metric, filter=Q(code='Battery')),
                                  max_ls=Max(metric, filter=Q(code='Other'))) \
                        .annotate(total_predictions=F('max_bat') + F('max_ls')) \
                        .order_by('sc_dt')
                elif tc == 'Light Service':
                    predictions = predictions \
                        .annotate(total_predictions=Max(metric, filter=Q(code='Other'))) \
                        .order_by('sc_dt')
                else:
                    predictions = predictions \
                        .annotate(total_predictions=Max(metric, filter=Q(code=tc))) \
                        .order_by('sc_dt')
        print(predictions)
        for p in predictions:
            if str(p['sc_dt'].strftime('%I%p')) in output:
                if p['total_predictions'] is None:
                    total_pred = 0
                elif p['total_predictions'] < 0:
                    total_pred = 0
                else:
                    total_pred = p['total_predictions']
                output[str(p['sc_dt'].strftime('%I%p'))]['data'].append({
                    'value': total_pred,
                    'label': p['date']
                })
            else:
                output[str(p['sc_dt'].strftime('%I%p'))] = {
                    'rowLink': '#',
                    'data': [
                        {'label': 'Time', 'value': p['sc_dt'].strftime('%I%p')},
                        {'label': p['date'], 'value': p['total_predictions']}
                    ]
                }
        return list(output.values())

# COMPARISON REPORT
def comparison(date, params, object):
    start_date = date - dt.timedelta(days=15)
    end_date = date + dt.timedelta(days=14)

    annot_d = {}
    metrics = {}
    for tcd in ['all', 'Tow', 'Battery', 'Other']:
        metrics[tcd] = {}
        for m in ['volume_pred', 'actual_volume', 'holiday_impacts', 'weather_impacts']:
            annot_d[f'{m}_{tcd}'] = Sum(m) if tcd == 'all' else Sum(m, filter=Q(code=tcd.capitalize()))
            metrics[tcd][m] = {'groupName': f"{tcd.capitalize()} {m.upper().replace('_', ' ')}", 'data': []}
        metrics[tcd]['diff'] = {'groupName': f'{tcd.capitalize()} Difference', 'data': []}
    print(metrics)

    view_by = params['view_by']
    predictions_for = object.id
    if 'fleetAvl' in params:
        predictions_for = params.get('fleetAvlId', object.id)

    historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=predictions_for,
                                                               sc_dt__range=[start_date,
                                                                             end_date]).order_by('sc_dt')

    class FourHourSplit(Func):
        template = """Floor(HOUR(%(expressions)s)/4)* 4"""

    view_by_grouping = {
        'day': TruncDate('sc_dt'),
        'four_hour': Concat(TruncDate('sc_dt'), V(' '), FourHourSplit('sc_dt'), output_field=CharField()),
        'hour': F('sc_dt')
    }
    historical = historical.annotate(date=view_by_grouping[view_by]).values('date').annotate(**annot_d).order_by()
    try:
        weather_holiday_baseline = round(historical.aggregate(Avg('volume_pred_all'))['volume_pred_all__avg'])
    except:
        weather_holiday_baseline = 0

    final_out = []
    for i, event in enumerate(historical):
        try:
            label = event['date'].strftime('%Y-%m-%dT%H:00:00Z')
        except AttributeError:
            hour = event['date'][event['date'].find(' ') + 1:]
            if len(hour) == 1:
                hour = '0' + hour
            label = event['date'][0:event['date'].find(' ')] + 'T' + hour + ':00:00Z'
            # label = event['date']
        for tcd, d in metrics.items():
            for metric, out in d.items():
                value = event.get(f'{metric}_{tcd}')
                time_type = 'Day_and_Hour_of_Week' if view_by != 'day' else 'Day_of_Week'
                if value is not None:
                    value = round(
                        value) + 1 * weather_holiday_baseline if 'weather' in metric or 'holiday' in metric else round(
                        value)
                if metric != 'diff':
                    metrics[tcd][metric]['data'].append({
                        'label': label,
                        'value': value,
                        'time_type': time_type
                    })
            # print(metrics[tcd]['volume_pred']['data'][i]['value'] - metrics[tcd]['actual_volume']['data'][i]['value'])
            try:
                diff = abs(
                    metrics[tcd]['volume_pred']['data'][i]['value'] - metrics[tcd]['actual_volume']['data'][i]['value'])
            except TypeError:
                diff = None
            metrics[tcd]['diff']['data'].append({
                'label': label,
                'value': diff
            })

    for tcd, d in metrics.items():
        for metric, out in d.items():
            final_out.append(metrics[tcd][metric])
    return final_out

# ADHEARENCE METRIC TABLE
def compare_metrics(date, params, object):
    start_date = dt.datetime.strptime(params.get('start_date', date - dt.timedelta(days=15)), '%Y-%m-%d')
    end_date = dt.datetime.strptime(params.get('end_date', date), '%Y-%m-%d')
    employees = Employee.objects.filter(organization=object.employees_under).exclude(
        active=0).values_list('id', flat=True)
    osat = DashboardAggregations.objects.filter(organization_id=object.id,
                                                sc_dt__range=[dt.datetime.combine(start_date, dt.datetime.min.time()),
                                                              dt.datetime.combine(end_date, dt.datetime.min.time())])
    historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=object.id,
                                                               sc_dt__range=[start_date, end_date]).order_by('sc_dt')
    annot_d = {
        'total_volume': Sum('volume_pred'),
        'total_actual_volume': Sum('actual_volume'),
        'driver_target': Sum('total_drivers')
    }
    historical = historical.values('sc_dt').annotate(
        **annot_d).order_by()
    average_volume = round(historical.aggregate(Avg(F('total_volume')))['total_volume__avg'], 0)
    print('this is the average volume', average_volume)
    scheduled_drivers = SchedulerReviewByDriver.objects \
        .filter(employee__in=employees,
                starting_time__range=[start_date, end_date],
                ending_time__range=[start_date, end_date]).values()
    # .values('date')\
    # .annotate(scheduled_drivers=Count('date')).values('date', 'scheduled_drivers')
    metrics = {'osat': [], 'total_volume': [], 'total_actual_volume': [], 'driver_scheduled': [], 'driver_target': []}
    annot_vals = ['total_volume', 'total_actual_volume', 'driver_target']
    all_hours = []
    for i, event in enumerate(historical):
        try:
            label = event['sc_dt'].strftime('%Y-%m-%dT%H:00:00Z')
        except AttributeError:
            hour = event['sc_dt'][event['sc_dt'].find(' ') + 1:]
            if len(hour) == 1:
                hour = '0' + hour
            label = event['sc_dt'][0:event['sc_dt'].find(' ')] + 'T' + hour + ':00:00Z'
        if label not in all_hours:
            all_hours.append(label)
        for a in annot_vals:
            if a in metrics:
                metrics[a].append({
                    'label': label,
                    'value': event[a],
                    'time_type': 'Day_of_Week'
                })
            else:
                metrics[a] = [{
                    'label': label,
                    'value': event[a],
                    'time_type': 'Day_of_Week'
                }]
    for o in osat.values('sc_dt', 'ata_median'):
        try:
            label = o['sc_dt'].strftime('%Y-%m-%dT%H:00:00Z')
        except AttributeError:
            hour = o['sc_dt'][o['sc_dt'].find(' ') + 1:]
            if len(hour) == 1:
                hour = '0' + hour
            label = o['sc_dt'][0:o['sc_dt'].find(' ')] + 'T' + hour + ':00:00Z'
        metrics['osat'].append({
            'label': label,
            'value': round(o['ata_median'] / 60, 2) + average_volume if o['ata_median'] is not None else None,
            'time_type': 'Day_of_Week'
        })
    for hour in all_hours:
        drivers_scheduled_count = 0
        d_hour = dt.datetime.strptime(hour, '%Y-%m-%dT%H:00:00Z')
        for d in scheduled_drivers:
            if d['starting_time'].replace(tzinfo=None) <= d_hour and d['ending_time'].replace(tzinfo=None) >= d_hour:
                drivers_scheduled_count = drivers_scheduled_count + 1
        metrics['driver_scheduled'].append({
            'label': hour,
            'value': drivers_scheduled_count,
            'time_type': 'Day_of_Week'
        })
    final_out = []
    for tcd, d in metrics.items():
        final_out.append({
            'groupName': tcd,
            'data': d
        })
    return final_out

# COMPARE PREDICTED VOLUME, ACTUAL VOLUME ETC... *************
def comparison_report(date, params, object):
    start_date = date - dt.timedelta(days=15)
    end_date = date + dt.timedelta(days=14)
    view_by = params.get('view_by', 'four_hour')
    obj_id = object.id

    annot_d = {
        'total_volume': Sum('volume_pred'),
        'total_actual_volume': Sum('actual_volume'),
        'driver_target': Sum('total_drivers')
    }

    if params.get('fleetAvl', False):
        obj_id = params.get('fleetAvlId', object.id)

    historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=obj_id,
                                                                   sc_dt__range=[start_date,
                                                                                 end_date]).order_by('sc_dt')

    class FourHourSplit(Func):
        template = """Floor(HOUR(%(expressions)s)/4)* 4"""

    view_by_grouping = {
        'day': TruncDate('sc_dt'),
        'four_hour': Concat(TruncDate('sc_dt'), V(' '), FourHourSplit('sc_dt'), output_field=CharField()),
        'hour': F('sc_dt')
    }
    historical = historical.annotate(date=view_by_grouping[view_by]).values('date').annotate(**annot_d).values('date', 'code', 'total_volume', 'total_actual_volume', 'driver_target').order_by()

    def convert_date(d):
        if view_by == 'four_hour':
            return d.split(' ')[0]
        if view_by == 'hour':
            return d.date()
        if view_by == 'day':
            return d

    def convert_time(tm):
        if view_by == 'hour':
            return tm.time()
        if view_by == 'day':
            return 'Day'
        time = int(tm.split(' ')[1])
        if time == 0:
            return '12AM'
        if time == 12:
            return '12PM'
        if time > 12:
            return f'{time - 12}PM'
        else:
            return f'{time}AM'
    # print(historical.values())
    overall_list = {}
    tow_list = []
    bat_list = []
    other_list = []
    print('historical predictions', view_by)
    for h in historical:
        h_date = convert_date(h['date'])
        h_time = convert_time(h['date'])
        h_data = {
            'date': h_date,
            'time': h_time,
            'service_type': h['code'] if h['code'] != 'Other' else 'Light Service',
            'prediction': round(h['total_volume']),
            'actual': round(h['total_actual_volume']),
            'predictions-actual': round(h['total_volume']) - round(h['total_actual_volume']),
            'variance': abs(round(h['total_volume']) - round(h['total_actual_volume']))
        }
        if h['code'] == 'Tow':
            print(h_data)
            tow_list.append(h_data)
        elif h['code'] == 'Battery':
            bat_list.append(h_data)
        else:
            other_list.append(h_data)

        if h['date'] in overall_list:
            overall_list[h['date']]['prediction'] = overall_list[h['date']]['prediction'] + round(h['total_volume'])
            overall_list[h['date']]['actual'] = overall_list[h['date']]['actual'] + round(h['total_actual_volume'])
            overall_list[h['date']]['predictions-actual'] = overall_list[h['date']]['prediction'] - overall_list[h['date']]['actual']
            overall_list[h['date']]['variance'] = abs(overall_list[h['date']]['prediction'] - overall_list[h['date']]['actual'])
        else:
            overall_list[h['date']] = {
                'date': h_date,
                'time': h_time,
                'service_type': 'All',
                'prediction': round(h['total_volume']),
                'actual': round(h['total_actual_volume']),
                'predictions-actual': round(h['total_volume']) - round(h['total_actual_volume']),
                'variance': abs(round(h['total_volume']) - round(h['total_actual_volume']))
            }
            # overall_list[h['date']]['service_type'] = 'All'
        # print(tow_list[:5])

    overall_list = list(overall_list.values())
    output = [overall_list, tow_list, bat_list, other_list]
    return output

def new_expectations(date, params, object):
    # EXPECTATION FOR THE WEEK ************************
    add_days = 0
    if date.weekday() == 6:
        add_days = 0
    else:
        add_days = date.weekday() + 1
    sunday = date - dt.timedelta(days=add_days)
    today = dt.datetime.now()
    today = today - dt.timedelta(hours=today.hour, minutes=today.minute, seconds=today.second)
    expectations = []
    for i in range(int(7)):
        expect_day = TimeseriesExpectations.objects.get_or_create(organization_id=object.id,
                                                                  date=sunday + dt.timedelta(days=i))[0]
        expectations.append(expect_day)
    try:
        output = TimeseriesExpectationsSerializer(expectations, many=True).data
    except Exception as e:
        print(e)
    return output

def full_report(date, params, object):
    [sunday, saturday] = get_sun_sat(date)
    print("monday", sunday, 'sunday', saturday)
    employees_list = get_employee_list(object)
    ghost_drivers = PlaceholderDriver.objects.filter(organization_id=object.id).values_list('id',
                                                                                                 flat=True)
    week_schedule = SchedulerReviewByDriver.objects.filter(Q(date__range=[sunday.date(), saturday.date()]),
                                                           Q(employee_id__in=employees_list) | Q(
                                                               placeholder_id__in=ghost_drivers))
    ls_as = params['ls_as']
    output = []
    output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
        total_hours=Sum('duration'),
        alt_name=F('placeholder__name'),
        driver_number=F('employee__raw_data_driver_id'),
        full_name=F('employee__full_name'))
                           .values('date', 'starting_time',
                                   'ending_time', 'duration',
                                   'tcd', 'full_name', 'total_hours', 'alt_name').order_by('full_name',
                                                                                           'alt_name'))
    from itertools import groupby
    dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
    for k, v in groupby(output_schedule,
                        key=lambda x: x['full_name'] if (x['full_name'] is not None) else x['alt_name']):
        sorted_schedule = list(v)
        for s in sorted_schedule:
            try:
                s.update({'display': s['starting_time'].strftime('%H:%M')
                                     + '-' + s['ending_time'].strftime('%H:%M')
                                     + '(' + s['tcd'] + ')'})
            except:
                s.update({'display': s['starting_time'].strftime('%H:%M')
                                     + '-' + s['ending_time'].strftime('%H:%M')})

        missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off'}
                         for d in dates if d not in
                         [d['date'] for d in sorted_schedule]]

        sorted_schedule = sorted_schedule + missing_dates
        sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

        output.append({'schedule': sorted_schedule[0],
                       'total_hours': sum([x['total_hours'] for x in sorted_schedule[0]])})
    predictions_for = object.id
    if 'fleetAvl' in params:
        predictions_for = params.get('fleetAvlId', object.id)
    if params['scheduler_type']:
        if params['scheduler_type'] == 'hourly':
            predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id=predictions_for)
        else:
            predictions = TimeseriesPredictionsHourly.objects.filter(organization_id=predictions_for)
    else:
        predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id=predictions_for)
    saturday = saturday + dt.timedelta(hours=23)
    predictions = predictions.filter(sc_dt__range=[sunday.date(), saturday])
    print('full report LS as', ls_as)
    if ls_as == 'All':
        print('this is ls as all')
        tow_prediction = predictions.values('sc_dt') \
            .annotate(total_vol=Sum('volume_pred'),
                      total_actual=Sum('actual_volume'),
                      all_drivers=Sum('total_drivers'),
                      all_drivers_low=Sum('total_drivers_wait_15')) \
            .values('sc_dt', 'total_vol', 'total_actual', 'all_drivers', 'all_drivers_low').order_by('sc_dt')
        print(tow_prediction.query)
        bat_prediction = []
        ls_prediction = []
    else:
        if ls_as == 'Tow':
            tow_prediction = predictions.exclude(code='Battery') \
                .values('sc_dt') \
                .annotate(total_vol=Sum('volume_pred'),
                          total_actual=Sum('actual_volume'),
                          all_drivers=Sum('total_drivers'),
                          all_drivers_low=Sum('total_drivers_wait_15')) \
                .values('sc_dt', 'total_vol', 'total_actual', 'all_drivers', 'all_drivers_low').order_by('sc_dt')
        else:
            tow_prediction = predictions.filter(code='Tow') \
                .values('sc_dt', 'code', 'volume_pred', 'actual_volume', 'total_drivers', 'total_drivers_wait_15').order_by('sc_dt')
        if ls_as == 'Battery':
            bat_prediction = predictions.exclude(code='Tow') \
                .values('sc_dt') \
                .annotate(total_vol=Sum('volume_pred'),
                          total_actual=Sum('actual_volume'),
                          all_drivers=Sum('total_drivers'),
                          all_drivers_low=Sum('total_drivers_wait_15')) \
                .values('sc_dt', 'total_vol', 'total_actual', 'all_drivers', 'all_drivers_low').order_by('sc_dt')
        else:
            bat_prediction = predictions.filter(code='Battery') \
                .values('sc_dt', 'code', 'volume_pred', 'actual_volume', 'total_drivers', 'total_drivers_wait_15')
        if ls_as == 'Light Service':
            ls_prediction = predictions.filter(code='Other') \
                .values('sc_dt', 'code', 'volume_pred', 'actual_volume', 'total_drivers', 'total_drivers_wait_15').order_by('sc_dt')
        else:
            ls_prediction = []

    tow_drivers = []
    bat_drivers = []
    ls_drivers = []
    date_times = []
    for p in predictions:
        if p.sc_dt not in list(date_times):
            date_times.append(p.sc_dt)
            sched = week_schedule.filter(Q(starting_time__lte=p.sc_dt) & Q(ending_time__gt=p.sc_dt))
            if ls_as == 'All':
                tow_count_d = sched.count()
                bat_count_d = 0
                ls_count_d = 0
            else:
                if ls_as == 'Tow':
                    tow_count_d = sched.filter(Q(tcd__icontains='Tow') | Q(tcd__icontains='Light Service')).count()
                else:
                    tow_count_d = sched.filter(tcd__icontains='Tow').count()
                if ls_as == 'Battery':
                    bat_count_d = sched.filter(Q(tcd__icontains='Battery') | Q(tcd__icontains='Light Service')).count()
                else:
                    bat_count_d = sched.filter(tcd__icontains='Battery').count()
                if ls_as == 'Light Service':
                    ls_count_d = sched.filter(tcd__icontains='Light Service').count()
                else:
                    ls_count_d = 0
            tow_drivers.append({'sc_dt': p.sc_dt, 'driver_count': tow_count_d})
            bat_drivers.append({'sc_dt': p.sc_dt, 'driver_count': bat_count_d})
            ls_drivers.append({'sc_dt': p.sc_dt, 'driver_count': ls_count_d})
    return {
        'full_schedule': output,
        'tow_pred': tow_prediction,
        'bat_pred': bat_prediction,
        'ls_pred': ls_prediction,
        'tow_driver_count': tow_drivers,
        'bat_driver_count': bat_drivers,
        'ls_driver_count': ls_drivers
    }

####################################
########## 4. Templates ############
####################################
def get_templates(date, params, object):
    template_id = params['template_id']
    templates = TimeseriesScheduleTemplate.objects.filter(organization_id=object.id)
    if template_id:
        template = TimeseriesScheduleTemplate.objects.get(id=template_id)
    else:
        templates = TimeseriesScheduleTemplate.objects.filter(organization_id=object.id)
        if templates.count() > 1:
            template = templates[0]
        elif templates.count() == 0:
            template = TimeseriesScheduleTemplate.objects.create(organization_id=object.id, name='Default')
        else:
            template = templates[0]
            # templates = templates.exclude(id=template.id)

    output = {
        'current_template': TimeseriesScheduleTemplateSerializer(template).data,
        'all_templates': templates.values('id', 'template_name')
    }
    return output

def delete_template(date, params, object):
    template = TimeseriesScheduleTemplate.objects.get(id=params['template_id']).delete()
    all_templates = TimeseriesScheduleTemplate.objects.filter(organization_id=object.id)
    if all_templates.count() > 0:
        template = TimeseriesScheduleTemplateSerializer(all_templates[0]).data
    else:
        template = None

    return {'all_templates': all_templates.values('id', 'template_name'), 'template': template}

def generate_from_template(date, params, object):
    process = params['process']
    if process == 'save_template':
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        [sunday, saturday] = get_sun_sat(date)
        employees_list = get_employee_list(object)
        is_create = params['create']
        week_schedule = SchedulerReviewByDriver.objects.filter(employee_id__in=employees_list,
                                                               date__range=[sunday.date(), saturday.date()]) \
            .exclude(off=True)
        if is_create:
            schedule_temp = TimeseriesScheduleTemplate.objects.create(
                organization_id=object.id,
                template_name=params['template_name']
            )
        else:
            schedule_temp = TimeseriesScheduleTemplate.objects.get(id=params['temp_id'])
        # schedule_temp = TimeseriesScheduleTemplate.objects.get_or_create(organization_id=self.object.id)[0]
        old_drivers_temp = TimeseriesScheduledDiversTemplate.objects.filter(template=schedule_temp).delete()
        new_drivers_temp = TimeseriesScheduledDiversTemplate.objects.bulk_create(
            [TimeseriesScheduledDiversTemplate(
                template=schedule_temp,
                day_of_week=weekdays[d.date.weekday()],
                start_time=d.starting_time,
                end_time=d.ending_time,
                duration=d.duration,
                schedule_type=d.tcd,
                employee=Employee.objects.get(id=d.employee_id),
            ) for d in week_schedule]
        )
        serializers_temp = TimeseriesScheduleTemplateSerializer(schedule_temp)

        all_temps = TimeseriesScheduleTemplate.objects.filter(organization_id=object.id).values('id',
                                                                                                     'template_name')
        return {'template': serializers_temp.data, 'all_templates': all_temps}
    else:
        [sunday, saturday] = get_sun_sat(date)
        # sunday = sunday.replace(hour=0, minute=0)
        weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        temp_id = params['template_id']
        template = TimeseriesScheduleTemplate.objects.get(id=temp_id)
        if object.type == 'Territory':
            org_set = object.children()
            employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
        else:
            employees = Employee.objects.filter(organization=object.employees_under).exclude(
                active=0).values_list('id', flat=True)

        profiles = EmployeeProfile.objects.filter(employee_id__in=employees).exclude(
            Q(active=0) | Q(active_not_available=1)).values('id', 'employee_id')

        unique_profile = {}
        for p in profiles:
            if p['id'] not in unique_profile:
                unique_profile[p['id']] = p['employee_id']

        profiles = unique_profile
        for i in range(len(weekdays)):
            new_date = sunday + dt.timedelta(days=i)
            temp_drivers = TimeseriesScheduledDiversTemplate.objects.filter(template=template,
                                                                            day_of_week=weekdays[i]) \
                .values('employee',
                        'start_time',
                        'end_time',
                        'duration',
                        'schedule_type')
            schedule = TimeseriesSchedule.objects.get_or_create(organization_id=object.id, date=new_date)[
                0]
            pto_entries = EmployeeProfileEntries.objects.filter(pto_end__gte=new_date,
                                                                pto_start__lte=new_date,
                                                                driver_profile__in=list(profiles)).values_list(
                'driver_profile__employee_id', flat=True)
            prev_schedule_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()
            scheduled_drivers = TimeseriesScheduledDrivers.objects.bulk_create([
                TimeseriesScheduledDrivers(
                    schedule=schedule,
                    employee=Employee.objects.get(id=t['employee']),
                    start_date=new_date + dt.timedelta(hours=t['start_time'].hour,
                                                       minutes=t['start_time'].minute),
                    end_date=get_end_date(t['start_time'], t['end_time'], new_date),
                    duration=get_duration(t['start_time'], t['end_time']),
                    schedule_type=t['schedule_type']
                ) for t in temp_drivers if t['employee'] not in pto_entries
            ])
            save_daily_schedule(new_date, scheduled_drivers, object)

        employees_list = get_employee_list(object)
        week_schedule = SchedulerReviewByDriver.objects.filter(date__range=[sunday.date(), saturday.date()],
                                                               employee_id__in=employees_list)
        output = []
        output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
            total_hours=Sum('duration'),
            full_name=F('employee__full_name'))
                               .values('date', 'starting_time',
                                       'ending_time', 'duration',
                                       'tcd', 'full_name', 'total_hours').order_by('full_name'))
        from itertools import groupby
        dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
        for k, v in groupby(output_schedule, key=lambda x: x['full_name']):
            sorted_schedule = list(v)
            for s in sorted_schedule:
                try:
                    s.update(
                        {'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
                            '%H:%M')
                                    + '-\n' + s['ending_time'].strftime('%H:%M')
                                    + '\n(' + s['tcd'] + ')'})
                except:
                    s.update(
                        {'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
                            '%H:%M')
                                    + '-\n' + s['ending_time'].strftime('%H:%M')})

            missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off'}
                             for d in dates if d not in
                             [d['date'] for d in sorted_schedule]]

            sorted_schedule = sorted_schedule + missing_dates
            sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

            output.append({'schedule': sorted_schedule[0],
                           'total_hours': sum([x['total_hours'] for x in sorted_schedule[0]])})
        try:
            template_schedule = TimeseriesScheduleTemplate.objects.get(organization_id=object.id)
            output_template = TimeseriesScheduleTemplateSerializer(template_schedule).data
        except:
            output_template = None



        return {'schedule': output, 'template_schedule': output_template, 'schedule_dates': dates}
####################################
########### 5. Other ###############
####################################
def placeholder_handler(date, params, object):
    handle = params['handle']
    if handle == 'create':
        ghost = params['ghost']
        ph = PlaceholderDriver.objects.create(
            name=ghost['name'],
            organization_id=object.id,
            sun_start='00:00:00',
            sun_end='00:00:00',
            mon_start='00:00:00',
            mon_end='00:00:00',
            tue_start='00:00:00',
            tue_end='00:00:00',
            wed_start='00:00:00',
            wed_end='00:00:00',
            thu_start='00:00:00',
            thu_end='00:00:00',
            fri_start='00:00:00',
            fri_end='00:00:00',
            sat_start='00:00:00',
            sat_end='00:00:00',
            sun_available=True,
            mon_available=True,
            tue_available=True,
            wed_available=True,
            thu_available=True,
            fri_available=True,
            sat_available=True,
        )
        ph.save()
    elif handle == 'save_changes':
        ghosts = params['ghosts']
        for ghost in ghosts:
            ph = PlaceholderDriver.objects.get(id=ghost['id'])
            ph.name = ghost['name']
            ph.service_type = ghost['service_type']
            ph.sun_start = ghost['sun_start'] if ghost['sun_available'] else None
            ph.sun_end = ghost['sun_end'] if ghost['sun_available'] else None
            ph.mon_start = ghost['mon_start'] if ghost['mon_available'] else None
            ph.mon_end = ghost['mon_end'] if ghost['mon_available'] else None
            ph.tue_start = ghost['tue_start'] if ghost['tue_available'] else None
            ph.tue_end = ghost['tue_end'] if ghost['tue_available'] else None
            ph.wed_start = ghost['wed_start'] if ghost['wed_available'] else None
            ph.wed_end = ghost['wed_end'] if ghost['wed_available'] else None
            ph.thu_start = ghost['thu_start'] if ghost['thu_available'] else None
            ph.thu_end = ghost['thu_end'] if ghost['thu_available'] else None
            ph.fri_start = ghost['fri_start'] if ghost['fri_available'] else None
            ph.fri_end = ghost['fri_end'] if ghost['fri_available'] else None
            ph.sat_start = ghost['sat_start'] if ghost['sat_available'] else None
            ph.sat_end = ghost['sat_end'] if ghost['sat_available'] else None
            ph.sun_available = ghost['sun_available']
            ph.mon_available = ghost['mon_available']
            ph.tue_available = ghost['tue_available']
            ph.wed_available = ghost['wed_available']
            ph.thu_available = ghost['thu_available']
            ph.fri_available = ghost['fri_available']
            ph.sat_available = ghost['sat_available']
            ph.save()
        return {'success': 'True'}
    elif handle == 'update':
        ghost = params['ghost']
        ph = PlaceholderDriver.objects.get(id=ghost['id'])
        ph.name = ghost['name']
        ph.service_type = ghost['service_type']
        ph.sun_start = ghost['sun_start']
        ph.sun_end = ghost['sun_end']
        ph.mon_start = ghost['mon_start']
        ph.mon_end = ghost['mon_end']
        ph.tue_start = ghost['tue_start']
        ph.tue_end = ghost['tue_end']
        ph.wed_start = ghost['wed_start']
        ph.wed_end = ghost['wed_end']
        ph.thu_start = ghost['thu_start']
        ph.thu_end = ghost['thu_end']
        ph.fri_start = ghost['fri_start']
        ph.fri_end = ghost['fri_end']
        ph.sat_start = ghost['sat_start']
        ph.sat_end = ghost['sat_end']
        ph.save()
    elif handle == 'delete':
        ph = PlaceholderDriver.objects.get(id=params['ghost_id'])
        ph.delete()
    elif handle == 'bulk':
        print('placeholder driver bulk action', params['ghosts'])
        ghosts = PlaceholderDriver.objects.filter(id__in=params['ghosts'])
        bulk_action = params['bulk_action']
        for g in ghosts:
            if bulk_action == 'unavailable' or bulk_action == 'available':
                pass
            elif bulk_action == 'delete':
                g.delete()
            else:
                if bulk_action not in g.service_type:
                    print(g.service_type)
                    if ',' not in g.service_type and g.service_type == None:
                        g.service_type = bulk_action
                    else:
                        g.service_type = f'{g.service_type}, {bulk_action}'
            g.save()
    else:
        holders = PlaceholderDriver.objects.filter(organization_id=object.id)
        if holders.count() > 0:
            output = holders.values(
                'id',
                'name',
                'service_type',
                'sun_start',
                'sun_end',
                'mon_start',
                'mon_end',
                'tue_start',
                'tue_end',
                'wed_start',
                'wed_end',
                'thu_start',
                'thu_end',
                'fri_start',
                'fri_end',
                'sat_start',
                'sat_end',
                'sun_available',
                'mon_available',
                'tue_available',
                'wed_available',
                'thu_available',
                'fri_available',
                'sat_available'
            )
        else:
            output = []
        return output

def drivers(date, params, object):
    # Gets the scheduled drivers
    # drivers = schedule.get_scheduled_drivers()
    try:
        schedule = TimeseriesSchedule.objects.get_or_create(organization_id=object.id, date=date)[0]
    except:
        schedules = TimeseriesSchedule.objects.filter(organization_id=object.id, date=date)
        schedule = schedules[0]
        for s in schedules:
            if s.id != schedule.id:
                s.delete()
    drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).order_by('start_date')
    print('drivers', drivers)
    # prev_output = TimeseriesScheduledDriversSerializer(prev_drivers, many=True).data
    output = TimeseriesScheduledDriversSerializer(drivers, many=True)
    output_schedule = {'id': schedule.id, 'date': schedule.date, 'publish': schedule.publish}
    return {'drivers': output.data, 'schedule_info': output_schedule}

def get_overnight_drivers(date, prams, object):
    prev_day = date - dt.timedelta(days=1)
    print(prev_day)
    try:
        prev_day_schedule = TimeseriesSchedule.objects.get(date=prev_day, organization_id=object.id)
        print(prev_day_schedule)
    except:
        return {'overnight_drivers': []}
    date_time = date.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_duration_on(end):
        duration = end.hour + (end.minute / 60)
        return duration

    overnight_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=prev_day_schedule, end_date__gte=date_time) \
        .exclude(end_date=date_time) \
        .annotate(text=F('employee__full_name')) \
        .values('id', 'end_date', 'schedule', 'schedule_type', 'placeholder', 'text')
    [o.update({'start_date': date_time, 'duration': get_duration_on(o['end_date']), 'overnight': True}) for o in
     overnight_drivers]
    return {'overnight_drivers': overnight_drivers}

def navigate_down(date, params, object):

    club_regions = []
    markets = []
    territories = []
    sb = []
    facility_type = object.type


    pass