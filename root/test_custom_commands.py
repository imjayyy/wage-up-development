import os
import sys
cmd = ['manage.py', 'update_index', "--start", "2021-01-07", "--end", "2021-01-19"]

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
try:
    from django.core.management import ManagementUtility
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc
utility = ManagementUtility(
    cmd
)
print(utility.argv)
utility.execute()