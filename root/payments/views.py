from django.shortcuts import render
import sys
sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from accounts.models import *
from .models import *
from django.db.models import F
from messaging.views import send_email as s_email
from performance_points.models import PPCampaign, PPCampaignPaymentPeriod

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
from root.utilities import combine_dicts, list_of_dicts_key_order
from django.utils.html import strip_tags

from dashboard.models import *
import requests
from arena.models import *
from .wingSpanPayment import *
from email.mime.image import MIMEImage
import datetime as dt
TREMENDOUS_TEST_API_KEY = "TEST_4c1c769686f7bac687828300543235012c4f91a24a90142161195f1c9bbccf66"
TREMENDOUS_API_KEY = "PROD_8f97df3371ee5cfcdf83952dd335087e62ae7913dc7b5fba053d66f569f03519"

TREMENDOUS_TM_FAST_APP = "PROD_11a1c7628ece370c76358dcb58871d77a4db3c85c7d0c54a5bf4b47f9dead06f"
TREMENDOUS_STATION_OWNER = "PROD_f7c1c341c48ddfcc5e99631792d2d717771e2bd0291ab6d4a7a02485c9884cba"

LAMBDA_MESSAGING_ENDPOINT = "https://ve1mc0qia6.execute-api.us-east-1.amazonaws.com/dev/"
TESTING = False
PRODUCTION = True

from root.utilities import send_email


# from tremendous import Tremendous

# Sandbox environment

class Payments(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'


    def post(self, request):
        '''

        :param request:
        purpose: create_transaction
        parameters {
            <wageup_campaign_id | tremendous_campaign_name> : <id, name>
            payment_method: <optional>
            payment_amount: 100
            payment_to: <employee_id>
            recipient_email: <optional -- assuming we have their email ... >
        }
        :return:
        '''

        self.testing = TESTING
        self.ws = WingSpanPayments()

        if request.data.get('test'):
            self.testing = True

        # self.url = "https://www.tremendous.com/api/v2" if not self.testing else "https://testflight.tremendous.com/api/v2"
        # api_key = TREMENDOUS_API_KEY if not self.testing else TREMENDOUS_TEST_API_KEY


        # self.client = Tremendous(api_key, self.url)
        self.user = request.user
        self.employee = self.user.employee()
        self.data = request.data
        self._request = request



        self.parameters = self.data.get("parameters", {})
        self.purpose = self.data.get("purpose")

        self.payment_limit = 250  # nobody can give anybody else more than this amount

        if self.parameters.get('wageup_campaign_id'):
            self.campaign = DriverCampaign.objects.get(id=self.parameters.get('wageup_campaign_id')).tremendous_campaign
        # elif self.parameters.get('tremendous_campaign_name'):
        #     self.campaign = TransactionCampaign.objects.get(name=self.parameters.get('transaction_campaign_name'))
            # self.campaign = TremendousCampaign.objects.get(name=self.parameters.get('tremendous_campaign_name'))
        else:
            self.campaign = TransactionCampaign.objects.filter(active=True)[0]
            # .exclude(name__icontains='test')[0]
            # self.campaign = TremendousCampaign.objects.all()

        self.pre_approved_positions = ['Executive', 'Admin', 'Territory-Associate', 'Territory-Manager']

        self.purpose_router = {
            'create_transaction': self.create_transaction,
            'get_logs': self.get_logs,
            'get_all_forms': self.get_all_forms,
            'get_form_questions': self.get_form_questions,
            'save_driver_review': self.save_driver_review,
            'get_campaigns': self.get_campaigns,
            'get_distributor_summary': self.get_distributor_summary,
            'get_unapproved_payments': self.get_unapproved_payments,
            'approve_payments': self.approve_payments,
            'reject_payments': self.reject_payments,
            'email_tm_approval_notice': self.email_tm_approval_notice,
            'check_available_budget': self.check_available_budget,
            'test_comms': self.test_comms,
            'check_w9_completion': self.check_w9_completion,
            'complete_w9': self.complete_w9
        }

        self.log_annotation = {
            'driver_name':F('payment_to__full_name'),
            'driver_wageup_id':F('payment_to__id'),
            'driver_aca_id':F('payment_to__raw_data_driver_id'),
            'driver_org':F('payment_to__organization__name'),
            'territory':F('payment_to__organization__parent__name'),
            'distributor':F('payment_from__full_name'),
            'distributor_org': F('payment_from__organization__name'),
            'distributor_type': F('payment_from__position_type'),
            'date':F('created_on'),
            'campaign':F('transaction_campaign__name'),
            'reward_emailed':F('reward_status'),
            'recipient_email':F('email_used'),
            }

        self.log_vals = ['driver_name', 'driver_org', 'payment_amount', 'date', 'reason', 'notes',
                'reward_emailed', 'driver_aca_id', 'driver_wageup_id', 'territory',
                'distributor', 'distributor_org', 'distributor_type', 'recipient_email', 'approved', 'approval_note']

        try:
            return Response(self.purpose_router[self.purpose](), status=status.HTTP_200_OK)
        except AssertionError as err:
            print(str(err))
            return Response(str(err), status=status.HTTP_206_PARTIAL_CONTENT)

    def test_comms(self):
        bus = {
            'user': self.user,
            'data': {
                'purpose': 'self_connection',
                'parameters': {}
            }
        }
        test = self.ws.self_connection(bus)
        return test

    def get_distributor_summary(self, focus='all'):
        campaigns = TransactionCampaign.objects.exclude(name__icontains='test') if not self.testing else TransactionCampaign.objects.filter(name__icontains='test')
        # campaigns = TremendousCampaign.objects.exclude(name__icontains='test') if not self.testing else TremendousCampaign.objects.filter(name__icontains='test')
        if self.parameters.get('campaign'):
            campaigns = campaigns.filter(name=self.parameters.get('campaign'))

        assert self.employee.organization.type != 'Station-Business', "This view is not allowed at your user level!"

        if self.employee.organization.type == 'Territory' and focus=='all':
            all_tm_payments = self.get_distributor_summary(focus='tm_only')
            my_station_payments = self.get_distributor_summary(focus='my_station_payments')

            print('all_tm_payments', all_tm_payments)

            return {
                'all_tm_payments': all_tm_payments,
                'my_station_payments': my_station_payments
            }

        out_main = {}
        for campaign in campaigns:

            payments_filter = {
                'transaction_campaign': campaign
            }

            mgmt_budget_filter = {
                'transaction_campaign': campaign
            }

            if focus == 'tm_only':
                payments_filter.update({
                    'payment_from__organization__type': 'Territory',
                })
                mgmt_budget_filter.update({
                    'manager__organization__type': 'Territory',
                })

            elif focus == 'my_station_payments':
                payments_filter.update({
                    'payment_from__organization__in': self.employee.organization.children()
                })
                mgmt_budget_filter.update({
                    'manager__organization__in': self.employee.organization.children(),
                    'manager__position_type': 'Station-Admin'
                })

            print(payments_filter)
            payments_made = list(TransactionPaymentLog.objects.filter(**payments_filter)\
                .values('payment_from')\
                .annotate(distributor=F('payment_from__full_name'),
                          total_payments_made=Sum('payment_amount'))\
                .values('distributor', 'total_payments_made',))

            [p.update({'total_payments_made': f"${round(p['total_payments_made'])}"}) for p in payments_made]
            print("payments made", payments_made)

            print(mgmt_budget_filter)
            funds_available = list(TransactionManagerBudget.objects.filter(
                **mgmt_budget_filter).annotate(
                distributor=F('manager__full_name'),
                distributor_type=F('manager__position_type'),
                distributor_organization=F('manager__organization__name'),

                initial_funds = F('amount')
            ).values('distributor', 'initial_funds', 'distributor_type', 'distributor_organization'))

            [p.update({'initial_funds': f"${round(p['initial_funds'])}"}) for p in funds_available]

            # print(funds_available)
            # print(payments_made)

            key_order = ['distributor', 'distributor_type', 'distributor_organization', 'initial_funds', 'total_payments_made']

            out = list_of_dicts_key_order(combine_dicts([payments_made, funds_available], lookup_field='distributor'), key_order=key_order)
            [o.update({'total_payments_made': 0}) for o in out if o['total_payments_made'] is None]
            out_main[campaign.name] = out
        return out_main
    def get_unapproved_payments(self):
        print('getting unapproved payments')

        if self.employee.position_type not in self.pre_approved_positions:
            raise Exception("You Do not have the authority to approve this request.")

        payments = TransactionPaymentLog.objects.filter(payment_from__organization__parent=self.employee.organization,
                                             approved='PENDING').annotate(**self.log_annotation).order_by('-date').values(*self.log_vals + ['id'])

        return payments

    def reject_payments(self):
        print('approving payment')
        assert self.data.get('payment_id_list') is not None, "Need A Payment Id"
        assert self.employee.position_type in self.pre_approved_positions, "You are not authorized to approve this!"

        payments = PaymentLog.objects.filter(id__in=self.data.get('payment_id_list'))

        for payment in payments:
            payment.approved = 'REJECTED'
            payment.reward_status = 'REJECTED'
            payment.approved_by = self.employee
            payment.approval_note = self.data.get('approval_note')
            payment.rejection_reason = self.data.get('rejection_reason')
            payment.save()

    def approve_payments(self):
        print('approving payment')
        assert self.data.get('payment_id_list') is not None, "Need A Payment Id"
        assert self.employee.position_type in self.pre_approved_positions, "You are not authorized to approve this!"

        payments = TransactionPaymentLog.objects.filter(id__in=self.data.get('payment_id_list'))

        for payment in payments:
            payment.approved = 'APPROVED'
            payment.reward_status = 'PENDING'
            payment.approved_by = self.employee
            payment.approval_note = self.data.get('approval_note')
            payment.save()
            self.payment_approved(payments)
            # self.pay_with_tremendous(payment, is_approval=True)

    def get_logs(self):
        campaigns = {}
        campaign_objects = TransactionCampaign.objects.exclude(name__icontains='test') if not self.testing else TransactionCampaign.objects.filter(name__icontains='test')
        # campaign_objects = TransactionCampaign.objects.exclude(name__icontains='test') if not self.testing else TransactionCampaign.objects.filter(name__icontains='test')
        for campaign in campaign_objects.order_by('-id'):
            logs = []
            available, total, spent, pending = 0, 0, 0, 0
            try:
                self.budget = TransactionManagerBudget.objects.get(manager=self.employee, transaction_campaign=campaign)
                available, total, spent, pending = self.get_users_remaining_budget(campaign=campaign)

            except ObjectDoesNotExist:
                self.budget = None
                if self.employee.position_type in ['Executive', 'Admin']:
                    pass
                else:
                    continue

            logs = TransactionPaymentLog.objects.filter(transaction_campaign=campaign).annotate(**self.log_annotation)
            all_logs=False
            if self.budget:
                my_logs = logs.filter(payment_from=self.employee).order_by('-date')
                my_station_logs = logs.filter(approved_by=self.employee).order_by('-date')
                my_station_logs = list(my_station_logs.values(*self.log_vals))
                [l.update({'payment_amount': f"${round(l['payment_amount'])}"}) for l in my_station_logs]
            elif self.employee.position_type in ['Executive', 'Admin']:
                my_logs = logs.order_by('-date')
                my_station_logs = []
                all_logs=True
            else:
                raise Exception("You do not have the right permissions for this view.")

            if self.employee.position_type in ['Admin']:
                my_logs = logs.order_by('-date')
                my_station_logs = []
                all_logs = True

            my_logs = list(my_logs.values(*self.log_vals))
            [l.update({'payment_amount': f"${round(l['payment_amount'])}"}) for l in my_logs]



            campaigns[campaign.name] = {
                'campaign_name': campaign.name,
                'campaign_id': campaign.id,
                'available_funds': available,
                'total_funds': total,
                'spent_funds': spent,
                'pending_funds': pending,
                'logs': my_logs,
                'myStationLogs': my_station_logs,
                'all_logs': all_logs
            }
        return campaigns

    def get_campaigns(self):
        campaigns = {}
        active_campaign = None
        has_campaigns = False
        campaigns_list = TransactionCampaign.objects.exclude(name__icontains='Test')
        # campaigns_list = TremendousCampaign.objects.all()
        print(campaigns_list.values())
        for campaign in campaigns_list:
            try:
                self.budget = TransactionManagerBudget.objects.get(manager=self.employee, transaction_campaign=campaign)
                has_campaigns = True
            except ObjectDoesNotExist:
                pass
            available, total, spent, pending_approval = self.get_users_remaining_budget(campaign=campaign)
            campaigns[campaign.name] = {
                'campaign_name': campaign.name,
                'campaign_id': campaign.id,
                'available_funds': available,
                'total_funds': total,
                'spent_funds': spent,
                'pending_approval': pending_approval
            }
            print(campaign)
            if active_campaign is None and campaign.active:
                active_campaign = campaigns[campaign.name]
        print('get_campaigns', {'campaigns': campaigns, 'active_campaign': active_campaign, 'has_campaigns': has_campaigns})
        return {'campaigns': campaigns, 'active_campaign': active_campaign, 'has_campaigns': has_campaigns}

    def get_users_remaining_budget(self, campaign=None, budget=None):
        if campaign is None:
            campaign = self.campaign
        try:
            self.budget = TransactionManagerBudget.objects.get(manager=self.employee, transaction_campaign=campaign)
        except ObjectDoesNotExist:
            if self.employee.position_type in ['Executive', 'Admin', 'Territory-Associate']:
                return [0, 0, 0, 0]
            raise Exception("User is not an authorized distributor")
        except ValueError:
            raise Exception('User does not have a budget')

        spent = TransactionPaymentLog.objects.filter(payment_from=self.employee, transaction_campaign=campaign)
        pending_approval = spent.filter(approved='PENDING').aggregate(paid=Sum('payment_amount'))['paid']
        spent = spent.filter(approved='APPROVED').aggregate(paid=Sum('payment_amount'))['paid']

        if spent is None:
            spent = 0

        if pending_approval is None:
            pending_approval = 0
        return self.budget.amount - (spent + pending_approval), self.budget.amount, spent, pending_approval

    def email_tm_approval_notice(self):
        parent = self.employee.organization.get_parent_to('Territory')
        managers = Employee.objects.filter(organization=parent.id)
        manager_emails = managers.values_list('user__email', flat=True)
        manager_emails = [m for m in manager_emails if m is not None]
        # print(manager_emails)

        # manager_emails = ['devin.gonier@thedgcgroup.com', 'dgonier@gmail.com']

        for m in manager_emails:
            request = {
                "header": "You have Fast-App Approvals Pending",
                "from": "fast-app-payments@wageup.com",
                "to": m,
                "goTo": {
                    "name": "Fast App",
                    "url": "https://aca-fast.wageup.com/"
                },
                "subject": "You have Fast-App Approvals Pending",
                "articles": [
                    {
                        "image": "fastApp.png",
                        "header": "You have payments waiting",
                        "text": "Please login to Fast App and Navigate to Check Rewards Given to Approve These payments."
                    }
                ]
            }

            send_email(request)

    def create_transaction(self):
        '''
        :parameter: {
            payment_amount: int,
            payment_to: int (employee id),
            reason: string, (optional)
            notes: string, (optional)
            recipient_email: string, (optional)
            tag: string, (transaction tag)
        :return:
        '''
        print('crete transaction', self.campaign)
        available, total, spent, pending_payments = self.get_users_remaining_budget()
        assert self.parameters.get('payment_amount') <= self.payment_limit, f"Cant give more than ${self.payment_limit}"
        assert available >= self.parameters.get('payment_amount'), f"Not enough funds! You only have ${round(available)} left to distribute. Please note the driver's name and email address and contact WageUp to request more funds."
        recipient = Employee.objects.get(id=self.parameters.get('payment_to'))
        reason = self.parameters.get('reason', '')
        notes = self.parameters.get('notes', '')
        payment_method = self.parameters.get('payment_method', 'WINGSPAN_API')
        if self.parameters.get('recipient_email'):
            email = self.parameters.get('recipient_email')
        else:
            assert 'No Email Provided'
            return {}

        approved = self.employee.position_type in self.pre_approved_positions
        try:
            transaction_tag = TransactionPaymentTag.objects.get(tag=self.parameters.get('tag'))
        except:
            transaction_tag = None
        try:
            pay_period = PPCampaignPaymentPeriod.objects.get(id=self.parameters.get('pay_period'))
        except:
            pay_period = None

        try:
            pp_campaign = PPCampaign.objects.get(id=self.parameters.get('pp_campaign'))
        except:
            pp_campaign = None
        try:
            employee_record = WingSpanUserEmployee.objects.get(employee_id=recipient.id, production=PRODUCTION)
        except:
            recipient_email = email
            bus = {
                'user': self.user,
                'data': {
                    'purpose': 'addWingSpanUser',
                    'parameters': {
                        'email': recipient_email,
                        'recipient_id': recipient.id
                    }
                }
            }
            self.ws.inside_job(bus)
            employee_record = WingSpanUserEmployee.objects.get(employee_id=recipient.id, production=PRODUCTION)
        if employee_record.collaborator_id is None:
            bus = {
                'user': self.user,
                'data': {
                    'purpose': 'create_collaborator',
                    'parameters': {
                        'recipient_id': recipient.id,
                        'email': email
                    }
                }
            }
            self.ws.inside_job(bus)
            # self.ws.createCollaborator(employee_record, False)

        assert not TransactionPaymentLog.objects.filter(payment_from=self.employee,
                                            payment_to=recipient,
                                            payment_amount=self.parameters.get('payment_amount'),
                                            payment_method=payment_method,
                                            transaction_campaign=self.campaign,
                                            notes=notes,
                                            email_used=email,
                                            created_on__gte=dt.date.today(),
                                                        pp_campaign=pp_campaign,
                                                        pp_campaign_pay_period=pay_period
                                         ), "This is very likely a duplicate!"

        payment = TransactionPaymentLog.objects.create(payment_from=self.employee,
                                            payment_to=recipient,
                                            payment_amount=self.parameters.get('payment_amount'),
                                            payment_method=payment_method,
                                            transaction_campaign=self.campaign,
                                            notes=notes,
                                            email_used=email,
                                            reason=reason,
                                            pp_campaign=pp_campaign,
                                            pp_campaign_pay_period=pay_period,
                                            approved='APPROVED' if approved else 'PENDING',
                                            reward_status='PENDING' if approved else 'PENDING APPROVAL'
                                            )
        tag = self.parameters.get('transaction_tag', None)
        if tag:
            tag = TransactionPaymentTag.objects.get(id=tag)
            payment.transaction_tag = tag
            payment.save()
        if not approved:
            # todo: send email to corresponding manager (Done)
            # todo: need to test
            try:
                self.email_tm_approval_notice()
            except Exception as e:
                print(e)

            return {
                "status": "success",
                "remaining_budget": self.get_users_remaining_budget(),
            }

        if payment_method == 'WINGSPAN_API' and approved:
            self.payment_approved(payment)

        if payment_method == 'TREMENDOUS_API' and approved:
            self.pay_with_tremendous(payment)

    def create_email_queue(self, payment):
        QueueUpPaymentEmail.objects.create(payment=payment)


    def email_client_reason(self, payment, email):
        email = self.parameters.get('recipient_email', email)

        note = f"""<p>{payment.payment_from.full_name} at AAA has decided to give you a reward for the following reason. </p>
        <h4>{payment.notes}</h4>""" if payment.notes else ""

        #TODO: fill this in
        employee_record = WingSpanUserEmployee.objects.get(employee_id=payment.payment_to.id, production=PRODUCTION)
        is_onboarded = employee_record.onboarded

        message = f"""
        <h1>Congratulations!</h1> 
        <h3>You have been rewarded for great work!</h3>
        {note}
        <p>{payment.payment_from.full_name} at AAA has decided to give you a reward for the following reason:</p
        <p><b>{payment.reason}</b></p>
        <p>The reward from {payment.payment_from.full_name} at AAA is in the amount of ${payment.payment_amount}! Your award will be distributed according to the payout method you chose in the MyToolKit App. If you have not chosen a payout method, you can do so now in the MTK App. </p> 
        <p>You can get cash instantly (within 24 hours) – or as a deposit to your bank account (2-3 business days) - or you can choose to receive a gift card from your choice of multiple vendors.</p>
        <p>To access the funds, watch your inbox for an email from team@wingspan.com (could take up to 24 hours to receive).</p>
        <p>If you chose to get an Instant Payout to your Debit Card, 
        you should have the award in within 24 hours (less 1% fee); 
        if you chose Bank Deposit, the award will be deposited directly 
        to your account in 2-3 business days; if you chose to take your award as a gift card, you’ll get an email with a link to select a gift card brand within 24 hours. </p>
        <p>If you did not receive an email from team@wingspan.com be sure to check your spam folder. 
        If it's not there or you have issues, please let us know by email at help@wageup.com. Please note: It could take up to 24 hours for the award email to arrive to your inbox.</p>"""

        if not is_onboarded:
            message += f"""
            <br><p>Looks like you have not registered to or finished setting up your payment distribution option. You can do this by going to the MyToolKit App (link below).</p>
            """


        html = {
            'intro_text' : message
        }

        # lambda_response = requests.post(LAMBDA_MESSAGING_ENDPOINT, json={'data': [html]})
        # lambda_response = lambda_response.json()
        # print(lambda_response, "RESPONSE FROM LAMBDA")
        # html = lambda_response['body']['html'].replace('/\\"/g', '"')
        to_email = ['help@wageup.com', email]

        mail_subject = f"Congratulations {payment.payment_to.full_name}! You received a reward from {payment.payment_from.full_name} at AAA"
        plain_message = strip_tags(html)



        for to in to_email:
            email_details = {
                'subject': mail_subject,
                'from': 'AAArewards@wageup.com',
                'to': to,
                'goTo': {
                    'url': 'https://aca-mtk.wageup.com' if is_onboarded else 'https://aca-mtk.wageup.com?onboard=1',
                    'name': 'View Rewards' if is_onboarded else 'Setup Bank Settings to Recieve Payments'
                },
                'replyTo': 'AAArewards@wageup.com',
                'message': message,
                'image': 'mytoolkit.png'
            }
            s_email(email_details)
        # mail = EmailMultiAlternatives(mail_subject, plain_message,'AAArewards@wageup.com', to_email, cc=to_email)
        # mail.mixed_subtype = 'related'
        # mail.attach_alternative(html, "text/html")
        # mail.send()

    def payment_approved(self, payment):
        email = self.parameters.get('recipient_email', None)
        if email is None:
            try:
                email = payment.payment_to.profile.get().campaign_preferred_email if payment.payment_to.profile.get().campaign_preferred_email else payment.payment_to.user.email
            except ObjectDoesNotExist:
                email = payment.payment_to.user.email
            except:
                assert 'No email provided'
                return {}
        bus = {
            'user': self.user,
            'data': {
                'purpose': 'makePayment',
                'parameters': {
                    'payment_amount': payment.payment_amount,
                    'recipient_id': payment.payment_to.id,
                    # 'tag': payment.transaction_tag.tag,
                    'notes': payment.notes,
                    'reason': payment.reason,
                    'tag': payment.transaction_tag.id
                }
            }
        }
        _pay = self.ws.inside_job(bus)
        payment.invoice_number = _pay['invoiceNumber']
        payment.transaction_id = _pay['payableId']
        payment.save()

        # self.email_client_reason(payment, email)
        self.create_email_queue(payment)
        out = {
            "status": "success",
            "remaining_budget": self.get_users_remaining_budget(),
        }
        return out


    def pay_with_tremendous(self, payment, is_approval=False):
        print(payment)
        if not payment.payment_to.user:
            assert self.parameters.get('recipient_email', payment.email_used) is not None, "Email must be specified!"
            email = self.parameters.get('recipient_email', payment.email_used)
        else:
            email = self.parameters.get('recipient_email', payment.email_used)
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
                    "email": self.parameters.get('recipient_email', email),
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
            }
        else:
            return {status: "success"}

    def get_all_forms(self):
        all_forms = ReviewForm.objects.all().values('id', 'name')
        return all_forms

    def get_form_questions(self):
        form_ = ReviewForm.objects.get(id=self.parameters.get('form_id'))
        questions = form_.questions.all().values('id', 'question', 'type', 'details', 'info')
        return questions

    def save_driver_review(self):
        '''
        {
            purpose: 'save_driver_review',
            parameters: {
                employee_id: int,
                questions: [
                    {
                        'question_id': int, (question id)
                        'answer': string, (answer for question)
                    }
                ]
            }
        }
        '''
        employee = Employee.objects.get(id=self.parameters.get('employee_id'))
        q_and_a = self.parameters.get('questions')
        additional_notes = q_and_a.pop(-1)
        review = ReviewDriver.objects.create(
            employee=employee,
            reviewed_by=self.employee,
            additional_notes=additional_notes['answer']
        )

        review_questions = ReviewDriverQuestion.objects.bulk_create([
            ReviewDriverQuestion(
                review=review,
                question=ReviewQuestion.objects.get(id=q['question_id']),
                answer=q['answer']
            ) for q in q_and_a
        ])

        output = {'success': True}

        return output
    def check_if_function_works(self, parm):
        print('the function works', parm)
    def check_available_budget(self):
        campaign_funds = TransactionCampaign.objects.filter(active=True, source=True)[0]
        # campaign_funds = TremendousCampaign.objects.filter(active=True, source=True)[0] # should only have one row with active and source = true
        self.campaign = campaign_funds
        [available, starting_amount, spent, pending] = self.get_users_remaining_budget()
        # manager_budget = ManagerBudget.objects.get(manager=self.employee)
        return {'available_amount': available, 'starting_amount': starting_amount, 'amount_spent': spent, 'amount_pending': pending}

    def check_w9_completion(self):

        try:
            ws_user = WingSpanUserEmployee.objects.get(employee=self.employee, production=True)
            current_year = dt.date.today().year
            w9_record = WingSpanUserW9.objects.get_or_create(wingspanUserId=ws_user, year=current_year)[0]
            return {'need_w9': w9_record.needs_w9()}
        except:
            return {'need_w9': False}

    def complete_w9(self):
        ws_user = WingSpanUserEmployee.objects.get(employee=self.employee, production=True)
        current_year = dt.date.today().year
        w9_record = WingSpanUserW9.objects.get_or_create(wingspanUserId=ws_user, year=current_year)[0]
        w9_record.complete = True
        ws_user.save()
        return {'complete': True}

    def send_need_w9_completion_email(self, payment_info):
        message = f"""<p>Hello ACA Driver!  Congratulations for being one of the top awarded Drivers from AAA Club Alliance!
            Over the course of this calendar year the awards issued to you by ACA have met or exceeded $600. 
            We are required by the IRS to collect a W9 from you once you reach the $600 threshold.</p>
            <br><br>
            <p>Please click on the link below to sign in to the MyToolKit App to complete your W9.  
                Click the <b>REFRESH</b> button prior to logging in to be able to see the W9 form.</p>
            <br><br>
            <p>If you have any questions, please reach out to us at: help@wageup.com</p>
            """

        html = {
            'intro_text': message
        }

        to_email = ['help@wageup.com', payment_info.email_used]

        mail_subject = f"Congratulations {payment_info.payment_to.full_name}! First, you have to complete your W9."
        plain_message = strip_tags(html)

        for to in to_email:
            email_details = {
                'subject': mail_subject,
                'from': 'AAArewards@wageup.com',
                'to': to,
                'goTo': {
                    'url': 'https://aca-mtk.wageup.com',
                    'name': 'MyToolKit App'
                },
                'replyTo': 'AAArewards@wageup.com',
                'message': message,
                'image': 'mytoolkit.png'
            }
            s_email(email_details)

class PaymentsEmailSend(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'

    def post(self, request, *args, **kwargs):
        send_date = dt.date.today()

        queue_emails = QueueUpPaymentEmail.objects.filter(sent=False)
        for q in queue_emails:
            note = f"""<p>{q.payment.payment_from.full_name} at AAA has decided to give you a reward for the following reason. </p>
                    <h4>{q.payment.notes}</h4>""" if q.payment.notes else ""
            employee_record = WingSpanUserEmployee.objects.get(employee_id=q.payment.payment_to.id, production=PRODUCTION)
            is_onboarded = employee_record.onboarded

            current_year = dt.date.today().year
            w9_record = WingSpanUserW9.objects.get_or_create(wingspanUserId=employee_record, year=current_year)[0]
            need_w9 = w9_record.needs_w9()
            employee = Employee.objects.get(id=q.payment.payment_to.id)
            mtk_registered = True if employee.user is not None else False





            to_email = ['help@wageup.com', q.payment.email_used]
            print(q.payment.transaction_tag)
            if q.payment.transaction_tag and q.payment.transaction_tag.id == 1:
                mail_subject = f"Your August AAA High-5 to Roadside Award!"
                message = f"""
                <p><b>{q.payment.reason}</b></p>
                """
            elif q.payment.transaction_tag and q.payment.transaction_tag.id == 2:
                mail_subject = f"AAA NE Summer Battery Program"
                message = f"""
                <p><b>{q.payment.reason}</b></p>
                """
            else:
                mail_subject = f"Congratulations {q.payment.payment_to.full_name} You received a reward from {q.payment.payment_from.full_name}!"
                message = f"""<h3>You have been rewarded for great work!</h3>
                   <p>{q.payment.payment_from.full_name} has decided to send you a reward for the following reason:</p>
                   <p><b>{q.payment.reason}</b></p>
                   <p><i>{q.payment.notes}</i></p>"""

            if need_w9:
                message += """Congratulations on being one of the top Drivers at AAA!  Your latest award has put your earnings at or over $600.  Per IRS Guidelines, we are now required to collect W9 information from you.<br>
                You can complete the W9 form on a secure form within the MyToolKit App: <a href="https://aaane-mtk.wageup.com/login/">https://aaane-mtk.wageup.com/login/</a>
                """

            if is_onboarded and mtk_registered:
                message += self.AllRegistered(q)
            elif mtk_registered and not is_onboarded:
                message += self.MTKRegisteredNotWS(q)
            else:
                message += self.NothingRegistered(q)

            html = {
                'intro_text': message
            }
            plain_message = strip_tags(html)

            for to in to_email:
                email_details = {
                    'subject': mail_subject,
                    'from': 'AAArewards@wageup.com',
                    'to': to,
                    'goTo': {
                        'url': 'https://aaane-mtk.wageup.com/' if is_onboarded else 'https://aaane-mtk.wageup.com?onboard=1',
                        'name': 'MyToolKit App'
                    },
                    'replyTo': 'AAArewards@wageup.com',
                    'message': message,
                    'image': 'mytoolkit.png'
                }
                s_email(email_details)

            q.sent = True
            q.date_sent = send_date
            q.save()

        return Response({'message': f'All Emails Sent: {queue_emails.count()}'}, status=status.HTTP_200_OK)

    def AllRegistered(self, q):
        message = f"""
            <p><b>For details regarding the timing of receiving your award, watch your inbox for an email from team@wingspan.com</b></p>
            <p>If you choose to get an Instant Payout to your Debit Card, you should have the award the same business day (less 1% fee); if you chose Bank Deposit, the award will be deposited directly to your account in 2-3 business days; if you chose to take your award as a gift card, you’ll get an email with a link to select a gift card brand. </p>
            <p>If you did not receive an email from team@wingspan.com be sure to check your spam folder. If it's not there or you have issues, please let us know by email at help@wageup.com. <b>Please note: It could take up to 24 hours for the award email to arrive to your inbox.</b></p>
            """

        return message

    def MTKRegisteredNotWS(self, q):
        message = f"""
           <p style="border: solid #000 thin; padding: 5px; background: #222"><b>In order to receive your award, you need to login to your MyToolKit account and choose a payout option.  Click the link below to go to the MTK App – and get registered today!</b><br>You can get cash instantly (within 24 hours) – or as a deposit to your bank account (2-3 business days) - or you can choose to receive a gift card from your choice of multiple vendors.</p>
           <p><b>For details regarding the timing of receiving your award, watch your inbox for an email from team@wingspan.com</b></p>
           <p>If you choose to get an Instant Payout to your Debit Card, you should have the award the same business day (less 1% fee); if you chose Bank Deposit, the award will be deposited directly to your account in 2-3 business days; if you chose to take your award as a gift card, you’ll get an email with a link to select a gift card brand. </p>
           <p>If you did not receive an email from team@wingspan.com be sure to check your spam folder. If it's not there or you have issues, please let us know by email at help@wageup.com. <b>Please note: It could take up to 24 hours for the award email to arrive to your inbox.</b></p>
           """
        return message

    def NothingRegistered(self, q):
        message = f"""
           <p style="border: solid #000 thin; padding: 5px; background: #222"><b>In order to receive your award, you need to create a MyToolKit account and choose a payout option!  Click the link below to go to the MTK App – and get registered today!</b><br>You can get cash instantly (within 24 hours) – or as a deposit to your bank account (2-3 business days) - or you can choose to receive a gift card from your choice of multiple vendors.</p>
           <p><b>Once you get registered, watch your inbox for an email from team@wingspan.com with details regarding your award and when you can expect to receive it!</b></p>
           <p>If you choose to get an Instant Payout to your Debit Card, the award will be deposited the same business day (less 1% fee); if you choose Bank Deposit, the award will be deposited directly to your account in 2-3 business days; if you choose to take your award as a gift card, you’ll get an email with a link to select a gift card brand.</p>
           <p>If you did not receive an email from team@wingspan.com be sure to check your spam folder. If it's not there or you have issues, please email us at help@wageup.com.<b>Please note: It could take up to 24 hours for the award email to arrive to your inbox.</b></p>
           """
        return message

    def need_w9_copy(self, q):
        message = f"""
            <p style="border: solid #000 thin; padding: 5px; background: #222"><b>In order to receive your award, you need to create a MyToolKit account and choose a payout option!  Click the link below to go to the MTK App – and get registered today!</b><br>You can get cash instantly (within 24 hours) – or as a deposit to your bank account (2-3 business days) - or you can choose to receive a gift card from your choice of multiple vendors.</p>
            <p><b>Once you get registered, watch your inbox for an email from team@wingspan.com with details regarding your award and when you can expect to receive it!</b></p>
            <p>If you choose to get an Instant Payout to your Debit Card, the award will be deposited the same business day (less 1% fee); if you choose Bank Deposit, the award will be deposited directly to your account in 2-3 business days; if you choose to take your award as a gift card, you’ll get an email with a link to select a gift card brand.</p>
            <p>If you did not receive an email from team@wingspan.com be sure to check your spam folder. If it's not there or you have issues, please email us at help@wageup.com.<b>Please note: It could take up to 24 hours for the award email to arrive to your inbox.</b></p>
        """

    def High5CampaingEmail(self, q):
        message = f"""
        
        """
