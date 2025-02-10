from accounts.models import *
from accounts.serializers import *
from django.core.management.base import BaseCommand, CommandError
import datetime as dt


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        permissions_to_add = [1, 18, 21, 22]
        accounts = Employee.objects.filter(position_type='Fleet-Manager')
        for a in accounts:
            permissions = Permissions.objects.filter(id__in=permissions_to_add)
            for p in permissions:
                if p not in a.permission.all():
                    a.permission.add(p)
                    print(f'added {p.name} to {a.full_name}')