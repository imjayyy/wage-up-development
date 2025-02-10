from payments.models import *
from payments.views import Payments
from accounts.models import Employee
from payments.wingSpanPayment import WingSpanPayments
from performance_points.models import PPCampaign, PPCampaignPaymentPeriod
import pandas as pd
import math

from django.core.management.base import BaseCommand, CommandError
import datetime as dt


class Command(BaseCommand):
    help = ''

    def get_reg_winners(self):
        return []
    def set_up_params(self, employee_id, email_to, amount):
        print("using employee id not raw data driver_id")
        emp = Employee.objects.get(id=employee_id)
        # emp = Employee.objects.get(raw_data_driver_id=employee_id)
        if not email_to:
            send_email = emp.user.email
        else:
            send_email = email_to
        return {
            "payment_to": emp.id,
            "payment_amount": amount,
            "reason": f"Congratulations! You have earned a ${amount} award for High-5 To Roadside Campaign!",
            "notes": "",
            "payment_method": "WINGSPAN_API",
            "recipient_email": send_email,
            "transaction_tag": 3,
            "pp_campaign": 4,
            "pay_period": 6
          }


    def test_params(self):
        return {
            "payment_to": 81982,
            "payment_amount": 2,
            "reason": f"Congratulations! You have earned a ${2} award for AAANE Spring Up Driver Campaign!",
            "notes": "test script 5",
            "payment_method": "WINGSPAN_API",
            "recipient_email": "shannon.callow+543@wageup.com",
            "transaction_tag": 2,
            "pp_campaign": 4,
            "pay_period": 7
        }
    def handle(self, *args, **options):
        payment_view = Payments()
        ws = WingSpanPayments()
        payment_view.employee = Employee.objects.get(id=83676)
        payment_view.user = payment_view.employee.user
        payment_view.ws = ws
        payment_view.testing = False
        payment_view.payment_limit = 600
        payment_view.campaign = TransactionCampaign.objects.filter(active=True)[0]
        payment_view.pre_approved_positions = ['Executive', 'Admin', 'Territory-Associate', 'Territory-Manager']
        df = pd.read_csv('/Users/agustindiaz-barriga/software/wageup/rdb/files/aaane_payments/may-scores-for-driver-payments2-6.22.24.csv', delimiter=',', header=0)
        print(df.head())
        total_winners = 0
        total_amount = 0


        # amount = 1
        # employee_id = 40570
        # employee_email = 'shannon.callow@wageup.com'
        # print(f'{employee_id} getting paid ${amount} email: {employee_email}')
        # total_winners += 1
        # total_amount += int(amount)
        # params = self.set_up_params(employee_id, employee_email, amount)
        # payment_view.parameters = params
        # payment_view.create_transaction()
        # payment_view.check_if_function_works(params)


        for d in range(len(df)):
            amount = df.values[d][13]
            if amount == 0 or math.isnan(amount):
                continue
            employee_id = int(df.values[d][0])
            # employee_email = df.values[d][2]
            employee_email = False
            print(f'{employee_id} getting paid ${amount} email: {employee_email}')
            try:
                total_winners += 1
                total_amount += int(amount)
                params = self.set_up_params(employee_id, employee_email, amount)
                payment_view.parameters = params
                payment_view.create_transaction()
                payment_view.check_if_function_works(params)
            except:
                continue
        print(f'total amount awarded: {total_amount} total winners: {total_winners}')
        # for testing
        # payment_view.parameters = self.test_params()
        # print(payment_view.parameters)
        # payment_view.create_transaction()

        # employees = self.get_reg_winners()
        # for e in employees:
        #     payment_view.parameters = self.set_up_params(e['id'], e['user_email'])

