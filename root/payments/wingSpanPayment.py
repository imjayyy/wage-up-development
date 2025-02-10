import sys

from requests import RequestException

sys.path.insert(0, 'root')
import requests

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

TESTING = False
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJYRzZRVHc3dUh0UFlja0tMWGdvcjJrIiwic2Vzc2lvbklkIjoidmpKODF6bUdJVHlCbk1QeUl5SGxmayIsImlhdCI6MTY2OTA2NzU1MX0.IGriwrndBNes-kBO_ZfyddcEBEWMF_vNIw1fLTw9BS0"
# prod_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJZRlQ2TTlqMkZ4bVR0TlZqbDdGS1NWIiwic2Vzc2lvbklkIjoicnA3Wk5mcmJINWFYZ1R6aW9fWEs0MCIsImlhdCI6MTY3NDA2MjgxMH0.ozpcyc1WhmA1HzhQReEpSywxMxMSiQ4ArBUcr9C5Xxs"
prod_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJZRlQ2TTlqMkZ4bVR0TlZqbDdGS1NWIiwic2Vzc2lvbklkIjoic3doUHk0V3BJdnFJdTZjdkpPazFSViIsImlhdCI6MTY5ODI1MTkwNn0.jilzXGt9lQllCOyqAJMPVVlARvdmrGw-meqNMe9pPWg"
# client_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJTVm9PRXVGZEh6MTVlSzFnMWRSUmZGIiwic2Vzc2lvbklkIjoibnhWMWNtMHNGdjkwSTNVWUE5Q1pDRiIsImlhdCI6MTY3NDc3NDEzOH0.WK2z_f6RsgvfeimZMQs7pylxwDQA2H1ggL4VNsEgMjs"

driver_parent_user = 'HIsZ87rHIhaEv6v75WBFRF'
PRODUCTION = True

'''
The flow is this:
1. create an organization for each client.
2. create an organization for each role (e.g. manager vs. driver) --- THIS DOESNT WORK --- 
3. Create a recipient and associate them with role e.g. driver-client; billy-bob --> driver --> ACA
4. Get Token for that User
5. Pass that token to the front end for the iframe

'''

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from accounts.models import Employee, Profile

from django.contrib.auth.models import User
from .models import *

class WingSpanPayments(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def __init__(self):
        self.defaultEngagementId = None
        self.wingspanUser = None
        self.requestingUser = None
        self.requestingEmployee = None
        self.parameters = None
        self.clientToken = None
        self.url = None
        self.session = None
        self.engagementAssociation = None
        # Will update in future. Should be tied to specific campaign
        self.engagementId = 'ORsEG8FLFua9g3aq7bD1Ck'

    def post(self, request, *args, **kwargs):
        print('this is the requesting user', request.user)
        print('this is the request', request.data)
        self.parameters = request.data.get('parameters', {})

        self.requestingUser = request.user
        print('this is the requesting user', self.requestingUser)
        self.requestingEmployee = self.requestingUser.employee()
        self.clientToken = None
        self.setupSession()
        self.authenticate()
        print('This is the purpose', request.data.get('purpose'))
        if not request.data.get('purpose'):
            return Response(self.getMyToken(), status=status.HTTP_200_OK)

        purpose_functions = {
            'checkStatus': lambda: self.checkStatus(),
            'onboardingComplete': lambda: self.onboardingComplete(),
            'getToken': lambda: self.getMyToken(),
            'addWingSpanUser': lambda: self.addEntity(),
            'makePayment': lambda: self.makePayment(),
            'self_connection': lambda: self.self_connection(),
            'checkForEmailDuplicates': lambda: self.checkForEmailDuplicates(),
            'resendRewardToWingspan': lambda: self.resendRewardToWingspan(),
            'updateWingSpanEmail': lambda: self.updateWingSpanEmail(
                request.data.get("token"),
                request.data.get("user"),
                request.data.get("parameters")
            )
        }

        return Response(purpose_functions[request.data.get('purpose')](), status=status.HTTP_200_OK)

    def inside_job(self, params):
        print('this should be similar to request', params)
        self.parameters = dict(params['data']['parameters'])
        self.requestingUser = params['user']
        self.requestingEmployee = self.requestingUser.employee()
        self.setupSession()
        # self.authenticate()
        #
        if not params['data'].get('purpose'):
            return self.getMyToken()

        return {
            'checkStatus': self.checkStatus,
            'onboardingComplete': self.onboardingComplete,
            'getToken': self.getMyToken,
            'addWingSpanUser': self.addEntity,
            'makePayment': self.makePayment,
            'self_connection': self.self_connection,
            'create_collaborator': self.createCollaborator,
            'checkForEmailDuplicates': self.checkForEmailDuplicates
        }[params['data'].get('purpose')]()

    def onboardingComplete(self):
        user = WingSpanUserEmployee.objects.get(employee=self.requestingEmployee, production=PRODUCTION)
        user.onboarded = True
        user.date_onboarded = dt.date.today()
        user.save()

    def checkStatus(self):
        onboarded = WingSpanUserEmployee.objects.get(employee=self.requestingEmployee, production=PRODUCTION).onboarded
        print('onboarded', onboarded)
        return onboarded


    def getEmail(self, employee, user):
        print('employee', employee)
        print('user', user)
        try:
            profile = Profile.objects.get(employee=employee)
            if profile.campaign_preferred_email:
                return profile.campaign_preferred_email
            else:
                return user.email
        except Exception as e:
            print(e)
            if MultipleObjectsReturned:
                print('HELLO')
                print('this is the error user email we return', user.email)
                return user.email
            print('Print user and employee', user, employee)
            print('Get email error', e)
            return None

    def checkForEmailDuplicates(self):
        email = self.getEmail(self.requestingEmployee, self.requestingUser)
        duplicate = False
        emps = WingSpanUserEmployee.objects.filter(employee_id__isnull=False, onboarded=True)
        for e in emps:
            print('THIS IS E', e)
            emp = e.employee
            if not emp:
                continue
            if email == self.getEmail(emp, emp.user):
                print('this is the user email', email)
                print('this is checking duplicate email', self.getEmail(emp, emp.user))
                duplicate = True
                WingSpanUserEmployee.objects.filter(onboarded=False, employee=self.requestingEmployee).delete()
                break

        if duplicate:
            return 'duplicate email'
        print('CHECKING FOR EMAIL DUPLICATES', duplicate)
        return 'unique email'


    def updateWingSpanEmail(self, token, user, parameters, attempts=0):
        print(user, parameters, attempts, token)


        # resp = self.checkForEmailDuplicates()
        # if 'duplicate email' in resp:
        #     return {'error': 'duplicate email'}

        try:
            print('self', user, self)
            if not user or user == 'undefined' or user == '':
                if attempts > 0:
                    raise RequestException('Wingpsan User not found')
                attempts += 1
                WingSpanUserEmployee.objects.filter(employee=self.requestingEmployee).delete()
                newUser = self.addEntity(email=self.requestingUser.email, emp=self.requestingEmployee)
                d = self.getMyToken()
                return self.updateWingSpanEmail(d.get('token'), newUser.wingspanUserId, parameters, attempts)
            url = 'https://api.wingspan.app/users/user/'
            resp = requests.patch(f'{url}{user}', json=parameters, headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {token}'
                })

            print('response', resp.text)

            return resp.json()

        except RequestException as e:
            print('Error during request:', e)
            return {'error': str(e)}

    def getClientToken(self):
        url = "https://stagingapi.wingspan.app" if TESTING else "https://api.wingspan.app"
        print("driver parent user", driver_parent_user)
        # prod_token = requests.get(f'{url}/users/users/session/token/{driver_parent_user}')
        print('URL:', f'{url}/users/organization/user/{driver_parent_user}/session')
        print('HEADERS:', {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {prod_token}'
        })
        resp = requests.get(f'{url}/users/organization/user/{driver_parent_user}/session', headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {prod_token}'
        })

        print('Token Response', resp.json())
        self.clientToken = resp.json()['token']
        return self.clientToken


    def setupSession(self, token=None):
        print('NEW SESSION CALLED')
        self.url = "https://stagingapi.wingspan.app" if TESTING else "https://api.wingspan.app"
        if not token:
            token = self.getClientToken()

        print('session default token is: ', token)
        self.session = requests.session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        })


    def makePayment(self):
        self.targetEmployee = Employee.objects.get(id=self.parameters.get('recipient_id'))

        # self.createCollaborator()
        # print(self.collaborator)

        self.createPayable()
        print(self.payable)
        self.approvePayment()
        print(self.paymentStatus)
        return self.paymentStatus

    def authenticate(self, token=None):
        if token is None:
            token = self.clientToken or self.getClientToken()
        print('token', token)
        r = self.session.get(f'{self.url}/users/session/token/{token}')
        user_r = r.json()

        if 'error' in user_r:
            new_token = self.getMyToken()
            r = self.session.get(f'{self.url}/users/session/token/{new_token}')
            user_r = r.json()
        try:
            print('AUTHENTICATION RESPONSE', user_r)
            self.wingspanUser = WingSpanUserEmployee.objects.get(wingspanUserId=user_r.get('userId'), production=PRODUCTION)

            print(self.wingspanUser)
        except:
            self.addEntity()
            self.wingspanUser = WingSpanUserEmployee.objects.get(wingspanUserId=user_r.get('userId'),
                                                                 production=PRODUCTION)

    def getEngagementUserID(self, employee, count=0, email_used=None):
        try:
            ws_emp = WingSpanUserEmployee.objects.get(employee_id=employee.id, production=PRODUCTION)
            if ws_emp.wingspanUserId is None:
                print('Adding new wingspan entity for employee', employee)
                self.addEntity(emp=employee, email=employee.user.email)
            return ws_emp.wingspanUserId

        except ObjectDoesNotExist:
            if count > 1:
                raise Exception("Infinite Loop detected aborting!")
            if email_used is None:
                self.addEntity(emp=employee, email=employee.user.email)
            else:
                self.addEntity(emp=employee, email=email_used)
            return self.getEngagementUserID(employee, count=count+1)
        except Exception as E:
            print("problem with employee!", employee)
            print(E)
            raise Exception("Problem getting collaborator")


    def getMyToken(self):
        # userID = self.getCollaboratorUserID(self.requestingEmployee).get('wingspan_user_id')
        userID = self.getEngagementUserID(self.requestingEmployee)
        print('THIS IS USER ID', userID)
        url = f"{self.url}/users/organization/user/{userID}/session"
        print('this is the get my token url', url)
        r = self.session.get(url=url)
        print('this is session r', r)
        data = r.json()
        print(data)
        assert not data.get('error'), f"Problem with getting session token: {data.get('error')}"
        self.tokenResponse = data
        print('This is get my token data', data)
        return data



    def addEntity(self, email=None, emp=None):
        if emp is None:
            self.targetEmployee = Employee.objects.get(id=self.parameters.get('recipient_id'))
        email = self.parameters.get('email') if email is None else email
        emp = self.targetEmployee if emp is None else emp

        print('creating new entity', email)

        url = f'{self.url}/users/organization/user'
        r = self.session.post(url=url, json={
            'email': email,
        })

        self.newEntity = r.json()
        print(self.newEntity)

        if self.newEntity.get('error') == "User for email already exists":
            self.newEntity = self.getUserByEmail(email)
            print(self.newEntity)

        # associate the org

        url = f"{self.url}/users/organization/user/{self.newEntity.get('userId')}/associate"
        r2 = self.session.post(url=url, json={
            "parentUserId": driver_parent_user
        })

        self.association = r2.json()

        headers = {
            'X-WINGSPAN-USER': driver_parent_user,
        }

        # new engagement association
        url = f"{self.url}/payments/payee"
        r3 = self.session.post(url=url, json={
            "email": email,
        }, headers=headers)
        self.engagementAssociation = r3.json()
        print('ENGAGEMENT ASSOCIATION', self.engagementAssociation)
        payeeId = self.engagementAssociation.get('payeeId')
        print('PAYEE ID', payeeId)
        url = f"{self.url}/payments/payee/{payeeId}/engagement"
        r4 = self.session.get(url, headers=headers)

        def get_payer_payee_engagement_id(data, engagement_name="Default Engagement"):
            for item in data:
                if item.get("engagementName") == engagement_name:
                    return item.get("payerPayeeEngagementId")
            return None  # Return None if no match is found

        self.defaultEngagementId = get_payer_payee_engagement_id(r4.json())
        print("Default Engagement:", self.defaultEngagementId)
        w, created = WingSpanUserEmployee.objects.get_or_create(employee=emp, production=PRODUCTION)
        print("WingSpanUserEmployee created:", created)
        if not created:
            print(self.newEntity)
            print(self.association)
            if not self.newEntity.get('userId'):
                raise Exception(self.newEntity)
            print("USER ID IS BEING REPLACED", w.wingspanUserId, " IS REPLACED WITH ", self.newEntity.get('userId'))
        elif WingSpanUserEmployee.objects.filter(wingspanUserId=self.newEntity.get('userId')).exists():
            w.delete()
            raise Exception("Someone with that email has already signed up for WingSpan!")
        w.wingspanUserId = self.newEntity.get('userId')
        w.collaborator_id = self.defaultEngagementId
        print("Before save:", w.collaborator_id)
        w.save()
        print("After save:", WingSpanUserEmployee.objects.get(pk=w.pk).collaborator_id)

        self.wingspanUser = w

        # if w.collaborator_id is None:
        #     collab_id = self.createCollaborator(True)
        #     w.collaborator_id = collab_id
        #     w.save()

        return w

    def getCollaboratorUserIDFromWS(self, userId):
        email = self.parameters.get('email') if userId.employee.user is None else userId.employee.user.email
        r = self.session.post(url=f'{self.url}/payments/collaborator', json={
            'memberEmail': email,
            'memberName': userId.employee.full_name,
            'memberCompany': userId.employee.organization.name,
            'clientId': userId.wingspanUserId
        })
        print('THIS IS COLAB FROM WINGSPAN', r)
        return r.json()

    def getCollaboratorUserID(self, employee, count=0, email_used=None):
        try:
            ws_emp = WingSpanUserEmployee.objects.get(employee_id=employee.id, production=PRODUCTION)
            print('WINGSPAN USER EMPLOYEE', ws_emp)
            if ws_emp.wingspanUserId is None:
                if email_used is None:
                    wp_emp = self.addEntity(emp=employee, email=employee.user.email)
                else:
                    wp_emp = self.addEntity(emp=employee, email=email_used)
            if ws_emp.collaborator_id is None:
                print('collaborator return', self.getCollaboratorUserIDFromWS(ws_emp))
                ws_emp.collaborator_id = self.getCollaboratorUserIDFromWS(ws_emp)['collaboratorId']
                ws_emp.save()
            return  {'collaborator_id': ws_emp.collaborator_id, 'wingspan_user_id': ws_emp.wingspanUserId}
        except ObjectDoesNotExist:
            if count > 1:
                raise Exception("Infinite Loop detected aborting!")
            if email_used is None:
                self.addEntity(emp=employee, email=employee.user.email)
            else:
                self.addEntity(emp=employee, email=email_used)
            return self.getCollaboratorUserID(employee, count=count+1)
        except Exception as E:
            print("problem with employee!", employee)
            print(E)
            raise Exception("Problem getting collaborator")




    def createPayable(self):
        print(self.targetEmployee)
        url = f'{self.url}/payments/payable'
        tag = self.parameters.get('tag', None)
        if tag:
            tag = TransactionPaymentTag.objects.get(id=tag).tag
        payable_params = {
            "currency": "USD",
            "invoiceNotes": f'<p>{self.parameters.get("notes", "")}</p><p>If you would like to update your email address or change your payout method for future payments, please login to the MyToolKit App, and go to Payments: <a href="https://aaane-mtk.wageup.com/login/">https://aaane-mtk.wageup.com/login/</a></p>',
            # "attachments": {
            #     "customAttachmentIds": []
            # },
            "client": {
                "payDate": dt.datetime.now().strftime('%Y-%m-%dT%H:%M:00')
            },
            "creditFeeHandling": {
                "memberPays": 0,
                "clientPays": 100
            },
            "metadata": {
                "employeeID": self.targetEmployee.id,
                "tag": tag
            },
            "collaboratorId": self.getCollaboratorUserID(self.targetEmployee).get('collaborator_id'),
            "lineItems": [
                {
                    "description": self.parameters.get('reason', 'Payment'),
                    "totalCost": self.parameters.get('payment_amount'),
                    "reimbursableExpense": False
                }
            ],
            "dueDate": (dt.datetime.now() + dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:00'),
            "clientsPays": 100,
            "memberPays": 0,
        }
        r = self.session.post(url=url,json=payable_params)

        self.payable = r.json()
        return self.payable


    def approvePayment(self):
        url = f'{self.url}/payments/payable/{self.payable.get("payableId")}'
        payment_params = {
            "status": "Open",
            "client": {"workflowStatus": "Approved"}
        }
        r = self.session.patch(url=url,json=payment_params
        )
        self.paymentStatus = r.json()

    def getUserByEmail(self, email):
        print('This is get user by email', email)
        email = email.lower()
        print('This is the url', self.url)
        url = f"{self.url}/users/user/email/{email}"
        r = self.session.get(url)
        self.collaborator = r.json()
        print('Retreived user by email', r.json())
        return r.json()

    def self_connection(self, request):
        print('Connection worked', request)
        return {'success': True}

    def createCollaborator(self, return_obj=False):
        # self.setupSession()
        # self.authenticate()
        if self.wingspanUser is None:
            print(self.parameters.get('recipient_id'))
            self.wingspanUser = WingSpanUserEmployee.objects.get(employee_id=self.parameters.get('recipient_id'), production=PRODUCTION)
        print(self.wingspanUser)
        collaborator_id = self.getCollaboratorUserID(self.wingspanUser.employee).get('collaborator_id')
        if collaborator_id is None:
            url = f'{self.url}/payments/collaborator'
            r = self.session.post(url=url, json={
                'clientId': self.wingspanUser.wingspanUserId,
                'memberEmail': self.wingspanUser.employee.user.email if self.wingspanUser.employee.user is not None else self.wingspanUser.employee.unverified_email,
                'memberName': self.wingspanUser.employee.full_name,
                'memberCompany': self.wingspanUser.employee.organization.name
            })
            self.collaborator = r.json()
            if return_obj:
                return self.collaborator['collaboratorId']
        else:
            return collaborator_id

        # creating collaborator just with email?

    def resendRewardToWingspan(self):
        non_payables = TransactionPaymentLog.objects.filter(invoice_number=None, payment_method='WINGSPAN_API', transaction_id=None)
        print('rewardToWingspan hit', non_payables.count(), non_payables.values('payment_method'))

        for p in non_payables:
            print(p.payment_to)
            self.parameters = {
                'email': p.email_used
            }
            url = f'{self.url}/payments/payable'
            payable_params = {
                "currency": "USD",
                "invoiceNotes": f'<p>{p.notes}</p><p>If you would like to update your email address or change your payout method for future payments, please login to the MyToolKit App, and go to Payments: <a href="https://aca-mtk.wageup.com/login/">https://aca-mtk.wageup.com/login/</a></p>',
                # "attachments": {
                #     "customAttachmentIds": []
                # },
                "client": {
                    "payDate": dt.datetime.now().strftime('%Y-%m-%dT%H:%M:00')
                },
                "creditFeeHandling": {
                    "memberPays": 0,
                    "clientPays": p.payment_amount
                },
                "metadata": {
                    "employeeID": p.payment_to.id,
                    "tag": p.transaction_tag.tag
                },
                "collaboratorId": self.getCollaboratorUserID(p.payment_to, email_used=p.email_used).get('collaborator_id'),
                "lineItems": [
                    {
                        "description": p.reason if p.reason is not None else 'Payment',
                        "totalCost": p.payment_amount,
                        "reimbursableExpense": False
                    }
                ],
                "dueDate": (dt.datetime.now() + dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:00')
            }
            r = self.session.post(url=url, json=payable_params)

            self.payable = r.json()
            self.approvePayment()

            p.invoice_number = self.paymentStatus.get('invoiceNumber')
            p.transaction_id = self.paymentStatus.get('payableId')
            p.save()
            QueueUpPaymentEmail.objects.create(payment=p)

        return {'message': 'success!'}
