from accounts.models import *
from accounts.serializers import *
from django.core.management.base import BaseCommand, CommandError
import datetime as dt
from django.db.models import Count
import pandas as pd
# import glob


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        starttime = dt.datetime.now()

        # duplicated_profiles = glob.glob('/software/dgc/files/duplicated_profiles.csv')

        # df = pd.read_csv('/software/dgc/files/duplicated_profiles.csv')
        print('--------- Start -----------')
        print(starttime)
        # for row in df.iterrows():
        #     print(row[1]['employee_id'])
        #     # profiles = EmployeeProfile.objects.filter(employee_id=row[1]['employee_id'])
        #     # print(profiles)
        #     profiles = EmployeeProfile.objects.filter(employee_id=row[1]['employee_id'])[1:]
        #     for p in profiles:
        #         p.delete()

        duplicated_profiles = EmployeeProfile.objects.values('employee').annotate(duplicated=Count('employee')).filter(duplicated__gt=1)
        print(duplicated_profiles.count())
        for d in duplicated_profiles:
            profiles_to_del = EmployeeProfile.objects.filter(employee_id=d['employee'])[1:]
            for p in profiles_to_del:
                p.delete()
            print(dt.datetime.now() - starttime)
        print('--------- End -----------')