import sys
sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework import generics, status
from accounts.models import *
from .models import *

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from root.utilities import combine_dicts, list_of_dicts_key_order, queryset_object_values
from django.utils.html import strip_tags
from .serializers import *
from dashboard.models import *
import requests
from arena.models import *
TREMENDOUS_TEST_API_KEY = "TEST_4c1c769686f7bac687828300543235012c4f91a24a90142161195f1c9bbccf66"
TREMENDOUS_API_KEY = "PROD_8f97df3371ee5cfcdf83952dd335087e62ae7913dc7b5fba053d66f569f03519"

TREMENDOUS_TM_FAST_APP = "PROD_11a1c7628ece370c76358dcb58871d77a4db3c85c7d0c54a5bf4b47f9dead06f"
TREMENDOUS_STATION_OWNER = "PROD_f7c1c341c48ddfcc5e99631792d2d717771e2bd0291ab6d4a7a02485c9884cba"

#older...
LAMBDA_MESSAGING_ENDPOINT = "https://ve1mc0qia6.execute-api.us-east-1.amazonaws.com/dev/"

#newer...
LAMBDA_EMAILS_ENDPOINT = "https://k8wspgj9xe.execute-api.us-east-1.amazonaws.com/default/wageupEmails-dev-emails"

STANDARD_EMAIL_REQUEST = {
    "header": "Congratulations! You received a reward from AAA",
    "from": "AAArewards@wageup.com",
    "to": ["help@wageup.com", "devin.gonier@thedgcgroup.com"],
    "subject": "Congratulations! You received a reward from AAA",
    "filesURL": [],
    "replyTo": "aaaRewards@wageup.com",
    "goTo": {
      "url": "https://aca-mtk.wageup.com",
      "name": "My ToolKit"
    },
    "imageHighlights": [],
    "articles": [
      {
        "image": "trophy.png",
        "header": "You have been rewarded for great work!",
        "text": "<p>You have been rewarded for your performance in the SpringUp! 2022 campaign at AAA is in the amount of <b>$10.00</b>!</p> It can be deposited straight into your bank account or distributed by another mechanism of your choice.\n\nTo access the funds, look for an email that you should have received from rewards@reward.tremendous.com. Click the link and follow the simple instructions to claim your reward.\n\nIf you did not receive an email from rewards@reward.tremendous.com be sure to check your spam folder. If its not there either please let us know by replying all to this email or sending us a separate email to <b>help@wageup.com</b>"
      }
    ]
}


TESTING = False

# from tremendous import Tremendous



class PaymentMethods(generics.GenericAPIView):

    def __init__(self, **kwargs):
        '''

        :params:

        testing: OPTIONAL boolean, submit to tremendous or not
        user: REQUIRED: User object,
        payment_limit: OPTIONAL
        tremendous_campaign : required Object for campaign working with,
        payment_amount: how much to pay
        payment_to: employee_id for person getting payment
        payment_method: which api to use optional
        reason: reason for payment
        notes: any notes about the payment

        :return: success message, and remaining budget
        '''
        
        self.kwargs = kwargs
        print(kwargs)
        self.testing = kwargs.get('testing', TESTING)

        self.url = "https://www.tremendous.com/api/v2" if not self.testing else "https://testflight.tremendous.com/api/v2"
        api_key = TREMENDOUS_API_KEY if not self.testing else TREMENDOUS_TEST_API_KEY

        self.client = Tremendous(api_key, self.url)
        self.user = kwargs.get('user')
        self.employee = self.user.employee()
        self.payment_limit = kwargs.get('payment_limit', 250)  # nobody can give anybody else more than this amount
        self.ppcampaign = kwargs.get('ppcampaign')
        self.campaign = kwargs.get('tremendous_campaign')
        self.pre_approved_positions = ['Executive', 'Admin', 'Territory-Associate', 'Territory-Manager']
        self.payment_to = kwargs.get('payment_to')
        self.payment_amount = kwargs.get('payment_amount')
        self.recipient_email = kwargs.get('recipient_email')

        assert self.campaign is not None, "Please specify Tremendous Campaign"
        assert self.user is not None, "Please specify User"
        assert self.payment_to is not None, "Please specify recipient employee id as payment_to"
        assert self.payment_amount is not None, "Please specify how much to pay"



    def get_users_remaining_budget(self, campaign=None, budget=None):
        if campaign is None:
            campaign = self.campaign
        try:
            self.budget = ManagerBudget.objects.get(manager=self.employee, tremendous_campaign=campaign)
        except ObjectDoesNotExist:
            if self.employee.position_type in ['Executive', 'Admin']:
                return [0, 0, 0]
            raise Exception("User is not an authorized distributor")
        spent = PaymentLog.objects.filter(payment_from=self.employee, tremendous_campaign=campaign)
        pending_approval = spent.filter(approved='PENDING').aggregate(paid=Sum('payment_amount'))['paid']
        spent = spent.filter(approved='APPROVED').aggregate(paid=Sum('payment_amount'))['paid']

        if spent is None:
            spent = 0

        if pending_approval is None:
            pending_approval = 0
        return self.budget.amount - (spent + pending_approval), self.budget.amount, spent, pending_approval

    def create_transaction(self):
        available, total, spent, pending_payments = self.get_users_remaining_budget()
        assert self.payment_amount <= self.payment_limit, f"Cant give more than ${self.payment_limit}"
        assert available >= self.payment_amount, f"Not enough funds! You only have ${round(available)} left to distribute. Please note the driver's name and email address and contact WageUp to request more funds."
        recipient = Employee.objects.get(id=self.payment_to)

        reason = self.kwargs.get('reason', '')
        notes = self.kwargs.get('notes', '')
        payment_method = self.kwargs.get('payment_method', 'TREMENDOUS_API')
        print(self.campaign.name)
        email = None
        print(recipient.user)
        if self.recipient_email:
            email = self.recipient_email
        elif Profile.objects.get(user=recipient.user).campaign_preferred_email:
            email = Profile.objects.get(user=recipient.user).campaign_preferred_email
        else:
            # email = None
            email = recipient.user.email

        assert email is not None, "EMAIL IS NONE!"

        approved = self.employee.position_type in self.pre_approved_positions

        payment = PaymentLog.objects.create(payment_from=self.employee,
                                            payment_to=recipient,
                                            payment_amount=self.kwargs.get('payment_amount'),
                                            payment_method=payment_method,
                                            tremendous_campaign=self.campaign,
                                            notes=notes,
                                            email_used=email,
                                            reason=reason,
                                            approved='APPROVED' if approved else 'PENDING',
                                            reward_status='PENDING' if approved else 'PENDING APPROVAL'
                                            )

        if payment_method == 'TREMENDOUS_API' and approved:
            return self.pay_with_tremendous(payment)

    def email_client_reason(self, payment, email):
        email = self.kwargs.get('recipient_email', email)

        note = f"""<p>{payment.payment_from.full_name} at AAA has decided to give you a reward for the following reason. </p>
        <h4>{payment.notes}</h4>""" if payment.notes else ""

        personal_payment = f"""
        <p>The reward from {payment.payment_from.full_name} at AAA is in the amount of ${payment.payment_amount:.2f}! 
        It can be deposited straight into your bank account or distributed by another mechanism of your choice.</p> 
        <p>To access the funds, look for an email that you should have received from rewards@reward.tremendous.com. 
        Click the link and follow the simple instructions to claim your reward. </p>
        <p>If you did not receive an email from rewards@reward.tremendous.com be sure to check your spam folder. 
        If its not there either please let us know by 
        <b>replying all</b> to this email or sending us a separate email to help@wageup.com </p>"""

        campaign_payment = f"""
        <p>You have been rewarded <b>${payment.payment_amount:.2f}</b> for your performance in the {self.ppcampaign.title} Driver Program. 
        Your award can be deposited straight into your bank account or redeemed as an Amazon gift card.</p> 
        <p>To access the funds, look for an email from rewards@reward.tremendous.com. 
        Click the link and follow the simple instructions to claim your reward. </p>
        <p>If you did not receive an email from rewards@reward.tremendous.com be sure to check your spam folder. 
        For further assistance, email us at help@wageup.com </p>"""


        main_text = personal_payment if not self.ppcampaign else campaign_payment
        note = note if not self.ppcampaign else ""

        message = f"""
        {note}
        {main_text}"""
        if self.ppcampaign:
            mail_subject = f"Congratulations {payment.payment_to.full_name}! You received a reward from AAA for {self.ppcampaign.title} Driver Program"
        else:
            mail_subject = f"Congratulations ! You received a reward from {payment.payment_from.full_name if not self.ppcampaign else self.ppcampaign.title} at AAA"
        STANDARD_EMAIL_REQUEST['articles'][0]['text'] = message
        STANDARD_EMAIL_REQUEST['to'] = ['help@wageup.com', email]
        STANDARD_EMAIL_REQUEST['header'], STANDARD_EMAIL_REQUEST['subject'] = mail_subject, mail_subject

        lambda_response = requests.post(LAMBDA_EMAILS_ENDPOINT, json=STANDARD_EMAIL_REQUEST)
        lambda_response = lambda_response.json()
        if lambda_response.get('message'):
            if 'Error' in lambda_response.get('message'):
                raise Exception("Lambda Error in sending message. Check logs in AWS")
        print(lambda_response, "RESPONSE FROM LAMBDA")


        # html = lambda_response['body']['html'].replace('/\\"/g', '"')
        # to_email = ['help@wageup.com', email]
        #
        # mail_subject = f"Congratulations {payment.payment_to.full_name}! You received a reward from {payment.payment_from.full_name if not self.ppcampaign else self.ppcampaign.title} at AAA"
        # plain_message = strip_tags(html)
        # mail = EmailMultiAlternatives(mail_subject, plain_message,'AAArewards@wageup.com', to_email, cc=to_email)
        # mail.mixed_subtype = 'related'
        # mail.attach_alternative(html, "text/html")
        # mail.send()

    def pay_with_tremendous(self, payment, is_approval=False):
        print(payment)
        if not payment.payment_to.user:
            assert self.kwargs.get('recipient_email', payment.email_used) is not None, "Email must be specified!"
            email = self.kwargs.get('recipient_email', payment.email_used)
        else:
            email = self.kwargs.get('recipient_email', payment.email_used)
            if email is None:
                email = payment.payment_to.user.email

        print(payment.tremendous_campaign.tremendous_id)
        order_data = {
            "external_id": payment.id,
            "payment": {
                "funding_source_id": payment.tremendous_campaign.tremendous_funding_source_id,
            },
            "reward": {
                "value": {
                    "denomination": payment.payment_amount,
                    "currency_code": "USD"
                },
                "campaign_id": payment.tremendous_campaign.tremendous_id,
                "delivery": {
                    "method": "EMAIL",
                },
                "recipient": {
                    "email": self.kwargs.get('recipient_email', email),
                    "name": payment.payment_to.full_name
                }
            }
        }
        # self.client.orders.create(order_data)
        self.client = Tremendous(payment.tremendous_campaign.api_key, self.url)
        tremendous_order = self.client.orders.create(order_data)

        print(tremendous_order)
        payment.reward_id = tremendous_order['rewards'][0]['id']
        payment.reward_status = tremendous_order['rewards'][0]['delivery']['status']
        payment.save()

        print(payment, email)

        self.email_client_reason(payment, email)

        if not is_approval:
            return {
                "status": "success",
                "remaining_budget": self.get_users_remaining_budget(),
                "payment_log": PaymentLogSerializer(payment).data
            }
        else:
            return {"status": "success", "payment_log": PaymentLogSerializer(payment).data}
