import os
import sys
import django
import pandas as pd

sys.path.append('/Users/patrickpoole/Desktop/wageup/django/root')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from accounts.models import EligibleDriver, Employee


def dump_eligible_drivers():
    df = pd.read_excel(
        "https://wageup-patrick.s3.amazonaws.com/survey_eligible_drivers/aaane_oct_driver_eligible.xlsx")

    for index, row in df.iterrows():
        driver_name = row['DRIVER FULL NAME']  # Adjust this to the corresponding field that matches with Employee
        driver_id = row['DRIVER ID']
        driver_org = row['STATION']
        recipient_email = row['Email']

        # Make sure to handle the case when an Employee with the given username doesn't exist
        try:
            employee = Employee.objects.get(id=driver_id)
            EligibleDriver.objects.create(
                employee=employee,
                driver_name=driver_name,
                driver_id=driver_id,
                driver_org=driver_org,
                recipient_email=recipient_email
            )
        except Employee.DoesNotExist:
            print(f"Employee with username {driver_name} does not exist.")


# Call this function to execute it
if __name__ == "__main__":
    dump_eligible_drivers()
