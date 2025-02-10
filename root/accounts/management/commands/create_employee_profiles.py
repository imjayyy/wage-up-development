from accounts.models import *
from accounts.serializers import *
from django.core.management.base import BaseCommand, CommandError
import datetime as dt


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        profiles = list(EmployeeProfile.objects.values_list('employee__id', flat=True))
        all_drivers = Employee.objects.filter(position_type='Driver').exclude(id__in=profiles)
        total_drivers = all_drivers.count()
        finished_drivers = 0
        today = dt.datetime.now()
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        print('--------Start---------')
        print('started at ', today)
        for d in all_drivers:
            profile = EmployeeProfile.objects.filter(employee=d.id)

            if profile.count() == 0:
                new_profile = {
                    'employee': d.id,
                    'trouble_code_type': None,
                    'active': True,
                    'employee_profile_entries': [
                        {'day_of_week': 'Monday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                        {'day_of_week': 'Tuesday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                        {'day_of_week': 'Wednesday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                        {'day_of_week': 'Thursday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                        {'day_of_week': 'Friday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                        {'day_of_week': 'Saturday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                        {'day_of_week': 'Sunday', 'start_time': dt.time(6, 0, 0), 'end_time': dt.time(14, 0, 0)},
                    ]
                }
                serializer = EmployeeProfileSerializer(data=new_profile)

                if serializer.is_valid():
                    serializer.save()
                else:
                    break
            else:
                profile = EmployeeProfile.objects.get(employee=d.id)
                entries = EmployeeProfileEntries.objects.filter(driver_profile=profile)
                if entries.count() == 0:
                    for i in days_of_week:
                        entry = EmployeeProfileEntries.objects.create(
                            driver_profile=profile,
                            day_of_week=i,
                            start_time=dt.time(6, 0, 0),
                            end_time=dt.time(14, 0, 0)
                        )
                        entry.save()
            finished_drivers += 1
            print(d.id, 'Done!', '{0}/{1}'.format(finished_drivers, total_drivers))
        print('ended at ', dt.datetime.now())
        print('--------End---------')
