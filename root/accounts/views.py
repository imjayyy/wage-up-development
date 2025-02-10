from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework_simplejwt import serializers as jwt_serializers
from . import jwt_serializers as custom_jwt_serializers
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from functools import partial
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .serializers import *
from django.contrib.auth.models import User
import datetime as dt
from django.http import HttpResponse
from rest_framework.parsers import JSONParser
from .models import *
from django.core.exceptions import ObjectDoesNotExist
from .tokens import account_activation_token
from django.conf import settings
from django.shortcuts import redirect
# from onboarding.models import *
# from onboarding.serializers import DemoPageSerializer
from rest_framework.permissions import BasePermission
from django.core.exceptions import MultipleObjectsReturned
from dashboard.models import *
from messaging.models import Announcements
from messaging.serializers import AnnouncementSerializer
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from django_rest_passwordreset.signals import reset_password_token_created, pre_password_reset
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.encoding import force_bytes, force_str
import logging
from .actions_logger import ActionsLogger
from django.db.models import F, Q
from messaging.views import send_email
import re
import os

logger = logging.getLogger('custom')

def employee(self):
    return Employee.objects.get(user_id=self.id)

User.add_to_class('employee', employee)

class RequestMethodBasedPermission(BasePermission):

    def __init__(self, allowed_methods):
        self.allowed_methods = allowed_methods

    def has_permission(self, request, view):
        if request.method in self.allowed_methods:
            return request.method in self.allowed_methods
        elif request.user and request.user.is_authenticated:
            return True

#@method_decorator(ratelimit(key='ip', rate='1/m', method='POST'), name='post')

class SurveyView(APIView):
    def post(self, request, *args, **kwargs):
        # Handle survey submission logic here
        # Process request.data, validate and save the survey data to the database

        # Assuming you have a Survey model and a SurveySerializer
        print('request data', request.data)
        serializer = SurveySerializer(data=request.data)
        if serializer.is_valid():
            employee_id = request.data.get('employee_id')  # Assuming you pass the employee_id from the frontend
            try:
                employee = Employee.objects.get(id=employee_id)
            except Employee.DoesNotExist:
                return Response({'message': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
            # Create and save the Survey instance here
            survey = Survey(
                employee=employee,
                employee_first_name=employee.first_name,
                employee_last_name=employee.last_name,
                employee_email=employee.user.email if employee.user else None,
                mtk_satisfaction=request.data.get('mtk_satisfaction', None),
                mtk_recommendation_likelihood=request.data.get('mtk_recommendation_likelihood', None),
                mtk_job_improvements=request.data.get('mtk_job_improvements', []),
                mtk_usage_frequency=request.data.get('mtk_usage_frequency', None),
                mtk_ease_of_use=request.data.get('mtk_ease_of_use', None),
                mtk_importance=request.data.get('mtk_importance', None),
                mtk_inspiration=request.data.get('mtk_inspiration', None),
                mtk_improvement_response=request.data.get('mtk_improvement_response', ''),
                mtk_testimonial=request.data.get('mtk_testimonial', ''),
            )
            survey.save()

            return Response({'message': 'Survey submitted successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class Login(generics.GenericAPIView):

    permission_classes = ()
    authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'

    def __init__(self):
        self.APP_VERSION = MobileAppVersion.objects.get(current_release=True).version

    def get_authenticate_header(self, request):
        return '{0} realm="{1}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,)

    def user_data(self, request):
        try:
            if 'email' in request.data:
                try:
                    user = User.objects.get(email=request.data['email'])
                except MultipleObjectsReturned:
                    return "Multiple User accounts with that email. " \
                           "Please try using a username or tech_id.", None
                except ObjectDoesNotExist:
                    return "No User found with that email. " \
                           "Please try using a username or tech_id. " \
                           "If you have not registered yet, please register.", None
            elif 'employee__login_id' in request.data:
                user = None
                employee = None
                try:
                    user = User.objects.get(employee__login_id=request.data['employee__login_id'])
                except MultipleObjectsReturned:
                    return "Multiple User accounts with that Tech ID. Please try using a username or email.", None
                except ObjectDoesNotExist:
                    try:
                        employee = Employee.objects.get(login_id=request.data['employee__login_id'])
                    except MultipleObjectsReturned:
                        employees = Employee.objects.filter(login_id=request.data['employee__login_id'])

                        employee = DashboardAggregations.objects.filter(employee__in=employees)

                        if len(employee)>0:
                            employee = employee.order_by('-sc_dt').first().employee
                        else:
                            employee =Employee.objects.filter(login_id=request.data['employee__login_id']).order_by('-updated_auto').first()

                        #employee = DashboardNew.objects.filter(employee__in=employees).order_by('-sc_dt').first().employee
                    except ObjectDoesNotExist:
                        try:
                            print('trying to get user via username with tech id')
                            user = User.objects.get(username=request.data['employee__login_id'])
                            request.data['username'] = request.data['employee__login_id']
                        except ObjectDoesNotExist:

                            return "No Employee found with that Tech ID. " \
                                   "Either the tech id was entered wrong, " \
                                   "or we need to find your employee information by " \
                                   "other means and update our records. Please Select Create Account to Proceed or Contact Us with the phone icon in the top right.", None
                    if user:
                        print('user found')
                        pass
                    elif employee:
                        return ('No User, but Employee', EmployeeSerializer(employee).data), None
                    else:
                        return "No Employee found with that Tech ID. Either the tech id was entered wrong, " \
                               "or we need to find your employee information by other means and update our records. " \
                               "Please Select Create Account to Proceed or Contact Us with the phone icon in the top right.", None
                    # except:
                    #     return "No User found with that Tech ID. Please try using a username or email. If you have not registered yet, please register."
            else:
                try:
                    user = User.objects.get(username=request.data['username'])
                except ObjectDoesNotExist:
                    return "No User found with that username. If your a driver and its been more than 3 months since you logged in, please re-register. Click the blinking blue button to setup (or re-register) an account.", None
            self.prev_last_login = user.last_login
            user.last_login = dt.datetime.utcnow()

            try:
                prof = Profile.objects.get(user=user)
                history = prof.site_visits
                print(history)
                prof.site_visits = history + 1
                prof.save()
            except:
                print("couldnt modify counts")
            user.save()
            return user.id, user
        except ObjectDoesNotExist:
            return False, None

    #@method_decorator(ratelimit(key='ip', rate='1000/m', method='POST'))
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        print("request user", self.request.user)

        user_id, user = self.user_data(request)
        print(user_id, user)
        if isinstance(user_id, str):
            return Response(user_id, status=status.HTTP_206_PARTIAL_CONTENT)

        if isinstance(user_id, tuple):
            return Response(user_id, status=status.HTTP_200_OK)

        if not user_id:
            return Response("The username you entered was invalid", status=status.HTTP_206_PARTIAL_CONTENT)

        try:
            employee = Employee.objects.get(user_id=user_id)
            employee_data = EmployeeSerializer(employee).data
            try:
                employee_duplicates = employee.cross_territory_duplicates()
                employee_data['duplicates'] = employee_duplicates
            except Exception as e:
                print(e, 'issue with assigning duplicate')
        except ObjectDoesNotExist:
            return Response("Something is wrong with your credentials. An employee is not assigned to this username and password. "
                            "Please contact us using the button at the top for help. Were sorry this happened.", status=status.HTTP_206_PARTIAL_CONTENT)
            # employee_data = {"Employee": "No Employee Assigned to this User"}

        # Check if user is eligible for survey and doesn't already have a record
        eligible_exists = EligibleDriver.objects.filter(driver_id=employee.id).exists()
        survey_exists = Survey.objects.filter(employee_id=employee.id).exists()

        surveyEligible = eligible_exists and not survey_exists
        employee_data['surveyEligible'] = surveyEligible

        # employee_data['completedTraining'] = completedTraining

        try:
            profile = Profile.objects.get(user_id=user_id)
            profile_data = ProfileSerializer(profile).data
        except ObjectDoesNotExist:
            profile_data = {'Profile': "No Profile Assigned to this User"}

        # try:
        #     try:
        #         seen_demos = UserDemoHistory.objects.filter(user_id=user_id, seen=True).values_list('page', flat=True)
        #     except ObjectDoesNotExist:
        #         seen_demos = []
        #     possible_demos = DemoPage.objects.exclude(id__in=seen_demos)
        #     demo_data = DemoPageSerializer(possible_demos, many=True).data
        #     pages = {}
        #     print(demo_data)
        #     for p in demo_data:
        #         pages[p['name']] = {}
        #         # for c in sorted(p['content'], key=lambda x: x['order']):
        #         for c in p['content']:
        #             pages[p['name']][c['object_id']] = {
        #                 "content": c['html_content'],
        #                 "object_id": c['object_id'],
        #                 "order": c['order'],
        #                 "include": c['include']}
        #     demo_data = {'Demos': pages}
        #
        # except ObjectDoesNotExist:
        #     demo_data = {'Demos': "User has seen all demos."}

        # logger.debug('login attempt')
        # logger.log("what is this", 'testing')
        # logger.warning('test warning')
        # logger.warning("Log level is set to {0}".format(logging.getLevelName(logger.level)))

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # logger.error('invalid token')
            print("TOKEN ERROR!")
            raise InvalidToken(e.args[0])

        output = {**profile_data, **serializer.validated_data, **employee_data}
        output['prev_last_login'] = self.prev_last_login
        print('output', output)


        if 'sat_app' in request.data:
            today = dt.datetime.today()
            notifications = []
            new_version = False
            if 'version' in request.data:
                user_app_v = request.data['version']
                if user_app_v != self.APP_VERSION:
                    new_version_banner = {
                            'id': None,
                            'message': f'This is an old version. Please uninstall this app. Click "Go Now" to open the new version. Follow the prompts to install it on your device.',
                            'starts': today,
                            'ends': today,
                            'position_type': 'Driver',
                            'link': 'https://aaane-mtk.wageup.com/login/',
                            'link_text': 'Go Now.',
                            'link_external': True,
                            'read': [],
                            'type': 'is-info',
                            'banner': True,
                            'platform': 'App'
                        }
                    new_version = True
                    notifications.append(new_version_banner)
            unfiltered_announcements = (
                Q(starts__lte=today) &
                 Q(ends__gte=today) &
                 Q(position_types__in=[employee.position_type, 'everyone']) &
                 (Q(platform='App') | Q(platform='Global'))
            )
            org_filter_clause = (
                Q(target_by_station_states__in=[employee.organization.parent, employee.organization]) |
                 Q(target_by_station_business__in=[employee.organization]) |
                 Q(target_by_facility_rep__in=employee.organization.parallel_parents.all()) |
                 Q(target_by_hubs__in=employee.organization.parallel_parents.all())
            )
            notify = Announcements.objects.filter(
                unfiltered_announcements |
                (unfiltered_announcements &
                 (org_filter_clause |
                 (~Q(position_types__in=['Driver', 'Station-Admin'])))))\
                .exclude(read__id__in=[user_id])
            if notify.count() > 0:
                notify = AnnouncementSerializer(notify, many=True).data
                for n in notify:
                    notifications.append(n)

                if new_version == False:
                    is_banner = True
                    for n in notify:
                        if n['banner'] == True:
                            is_banner = False
                            break
            else:
                if new_version == False:
                    is_banner = True
            try:
                prevLog = UserLogins.objects.filter(userId=user, login_type='satapp').latest('id')
                print(prevLog)
                if employee.position_type == 'Driver':
                    surveys = Std12EReduced.objects.filter(date_updated_surveys__gte=prevLog.login_time,
                                                           emp_driver_id=employee.id).count()
                    print('number of surveys', surveys)
                    if surveys > 0:
                        notifications.append({
                            'id': None,
                            'message': f'Since your last login, you have {surveys} new surveys.',
                            'starts': today,
                            'ends': today,
                            'position_type': 'Driver',
                            'link': 'Surveys',
                            'link_text': 'Go To Surveys',
                            'link_external': False,
                            'read': [],
                            'type': 'is-info',
                            'banner': is_banner,
                            'platform': 'App'
                        })
            except:
                pass

            if new_version:
                for n in list(notifications[1:]):
                    if n['banner'] == True:
                        n['banner'] = False

            output['notifications'] = notifications
            newLog = UserLogins(userId=user, login_time=dt.datetime.utcnow(), login_type='satapp')
            ActionsLogger(user, 'User', 'New Login on App', 'App Login')
        else:
            newLog = UserLogins(userId=user, login_time=dt.datetime.utcnow(), login_type='website')
            ActionsLogger(user, 'User', 'New Login on Website', 'Web Login')
        newLog.save()
        return Response(output, status=status.HTTP_200_OK)

    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    serializer_class = custom_jwt_serializers.TokenObtainPairSerializer


class RefreshToken(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    serializer_class = jwt_serializers.TokenRefreshSerializer

    www_authenticate_realm = 'api'

    def get_authenticate_header(self, request):
        return '{0} realm="{1}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,
        )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # raise InvalidToken(e.args[0])
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class CreateUser(generics.GenericAPIView):
    """

    POST -- Expects:
    invite_id as id
    username as username
    password as password
    ACCESS TOKEN IS OBVIOUSLY NOT NECESSARY BUT EMPLOYEE ID COMES FROM INVITE
    WE ALSO RUN A CHECK OF EMAIL AGAINST INVITE EMAIL

    CONFIRM EMAIL ADDRESS TO ACTIVATE

    """

    permission_classes = ()
    authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'

    def update_permissions(self, employee):
        # try:
        permissions = {
            "Admin": [1, 9, 21],
            "Driver": [12,],
            "Executive": [1, 9, 21],
            "Fleet-Manager": [1, 9, 17, 21, 22],
            "Station-Admin": [1, 9, 21],
            "Facility-Rep": [1, 9, 21],
            "Territory-Associate": [1, 9, 21]
        }
        if not employee.no_match:
            for p in permissions[employee.position_type]:
                employee.permission.add(Permissions.objects.get(id=p))
        return employee
        # except:
        print("something went wrong when adding permissions")
        return employee

    def update_groups(self, employee):
        groups = {
            "Admin": [1, 2, 3, 6, 7, 10, 12, 16, 17],
            "Executive": [1, 2, 3, 6, 7, 10, 12, 16, 17],
            "Appeals-Access": [1, 2, 3, 6, 7, 10, 12, 16, 17],
            "Territory-Associate": [1, 2, 3, 7, 10, 12, 17],
            "Fleet-Manager": [2, 6, 16]
        }
        if not employee.no_match:
            position = employee.position_type
            if position == 'Driver':
                if employee.organization.facility_type == 'Fleet':
                    employee.group.add(EmployeeGroup.objects.get(id=16))
                else:
                    employee.group.add(EmployeeGroup.objects.get(id=17))
            elif position == 'Station-Admin':
                if employee.organization.facility_type == 'AAR':
                    employee.group.add(EmployeeGroup.objects.get(id=1))
                elif employee.organization.facility_type == 'PSP':
                    employee.group.add(EmployeeGroup.objects.get(id=7))
                    employee.group.add(EmployeeGroup.objects.get(id=3))
                else:
                    employee.group.add(EmployeeGroup.objects.get(id=7))
            else:
                for g in groups[position]:
                    employee.group.add(EmployeeGroup.objects.get(id=g))
        return employee
    def get_authenticate_header(self, request):
        return '{0} realm="{1}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,
        )

    def username_unique_check(self, data):
        print('CHECKING USERNAME')
        username = data['username']
        num_results = User.objects.filter(username=username).count()
        if num_results > 0:
            print("USERNAME ALREADY TAKEN")
            return 0
        else:
            print("USERNAME IS NEW")
            return 1

    def receive_verified_email(self, uidb64, token):
        print('uidb', uidb64)
        print('token', token)
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()

        return redirect(settings.FRONT_END_DOMAIN + '/login/')

    def send_verify_email(self, user):
        message = render_to_string('accounts/create_user_verify_email.html', {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'domain': settings.BACK_END_DOMAIN, #TODO: change the domain
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        })
        to_email = user.email
        mail_subject = "Veryify your email to join WageUp dashboard"
        email = EmailMessage(mail_subject, message, 'admin@wageup.com', to=[to_email])
        # email.send() TODO: this is not super necessary
        print("SENT VERIFY EMAIL TO: ", user.email)
        return True

    def create_user(self, data):

        invite = Invite.objects.get(pk=data['id'])
        invite_data = InviteSerializer(invite).data
        combined_data = {**data, **invite_data}

        print("COMBINED DATA", combined_data)

        user_serializer = CreateUserSerializer(data=combined_data)
        if user_serializer.is_valid():
            u = user_serializer.data
            print("SERIALIAZED", u)
            user = User.objects.create_user(
                email=u['email'],
                username=u['username'],
                password=u['password'],
                first_name=combined_data['employee']['first_name'],
                last_name=combined_data['employee']['last_name'],
                is_active=True
            )
        else:
            return False

        print("USER", user)
        verified = self.send_verify_email(user)
        print("EMPLOYEE ID", combined_data['employee'])
        if verified:

            employee = Employee.objects.get(id=combined_data['employee']['id'])



            employee = self.update_permissions(employee) #TODO: FINISH THIS
            # employee = self.update_groups(employee)



            employee.user = user
            if 'login_id' in combined_data['employee']:
                employee.login_id=combined_data['employee']['login_id']
            employee.save()
            print(employee)
            print("EMPLOYEE TABLE UPDATED")

            invites = Invite.objects.filter(employee=employee)
            for i in invites:
                i.already_used = True
                i.save()
            print(" INVITES FOR THIS EMPLOYEE ARE NOW INACTIVE")

            emp_serializer = EmployeeSerializer(employee)
            return emp_serializer.data

        else:
            return HttpResponse("SOMETHING WENT WRONG", status=500)

    def get_employee_by_login_or_native_id(self, data):
        print('get employee by login or native id', data)
        employee_set = Employee.objects.filter(Q(login_id=data['employee_id']) | Q(id=data['employee_id'])).order_by('-latest_activity_on')
        print(employee_set, 'login_id response')
        employee_set = [e for e in employee_set if e.last_name == data['last_name']]
        if employee_set:
            print('returning latest employee based on login id')
            return employee_set[0]
        else:
            try:
                employee_set = Employee.objects.get(id=data['employee_id'])
                print('returning employee based on id in employee table')
            except ValueError:
                employee_set = []
            except ObjectDoesNotExist:
                employee_set = []
            if employee_set:
                return employee_set
            else:
                return None


    def get_employee_by_first_last_name(self, data):
        employee_set = Employee.objects.filter(first_name=data['first_name'], last_name=data['last_name']).order_by('-latest_activity_on')
        if employee_set:
            return employee_set[0]
        else:
            return None

    def create_employee_with_flag(self, data):



        data["organization"] = data.get('organization_id')
        data["permission"] = [11,]
        data["registered_by"] = 1
        data["no_match"] = True
        data["position_type"] = "Driver"
        data["org_name_help"] = data.get('org_name_help')

        print(data['organization'])
        org = Organization.objects.get(id=data['organization'])
        if org.type == 'Territory' and org.facility_type=="Fleet":
            new_org = org.children().filter(type='Station-Business')[0].employees_under_id
            data['organization'] = new_org


       # necessary_params = ['organization', 'first_name', 'last_name', 'position_type', "permission"]
        serializer = AddEmployeeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            print(serializer.data)
            return serializer.data

        else:
            print(serializer.errors)
            return {'id': None}



    def check_id_name_match(self, data):
        print('CHECK ID NAME MATCH DATA', data)
        if 'employee_id' in data:
            if data['employee_id'] is not None:
                employee = self.get_employee_by_login_or_native_id(data)
            else:
                employee = self.get_employee_by_first_last_name(data)
        else:
            employee = self.get_employee_by_first_last_name(data)
        if not employee:
            return 0

        our_name = re.sub(r'\W+', '', employee.last_name.lower())
        print('our name', our_name)
        if data['last_name'].lower() in ['sr', 'jr', 'ii', 'iii']:
            raise Exception("Last name cant just be abbreviation like sr, or jr needs last name too")

        if re.sub(r'\W+', '', data['last_name'].lower()) in our_name:
            return employee
        else:
            return 0



    def create_user_by_login_id(self, data):

        employee = self.get_employee_by_login_or_native_id(data)

        '''if 'login_id' in data:
            num_results = Employee.objects.filter(login_id=data['login_id']).count()
            if num_results > 0:
                return None

            employee.login_id = data['login_id']
            employee.save()'''
        ### todo: if groups are being used uncomment this
        # try:
        #     employee = self.update_groups(employee)
        # except:
        #     pass

        try:
            employee = self.update_permissions(employee)
        except:
            pass

        if 'login_id' in data:
            employee.login_id = data['login_id']
            employee.save()

        emp_data = EmployeeSerializer(employee).data

        combined_data = {**data, **emp_data}



        if combined_data.get('no_match'):
            del combined_data['no_match']

        print("COMBINED", combined_data)

        user_serializer = CreateUserSerializer(data=combined_data)
        if user_serializer.is_valid():
            u = user_serializer.data
            print("SERIALIAZED", u)
            user = User.objects.create_user(
                email=u['email'],
                username=u['username'],
                password=u['password'],
                first_name=combined_data['first_name'],
                last_name=combined_data['last_name'],
                is_active=True,
            )
            profile = Profile.objects.create(
                user=user,
                employee=employee,
                last_activity=dt.datetime.now()
            )
        else:
            return False

        print("USER", user)
        verified = self.send_verify_email(user)


        employee.user = user
        employee.login_id = combined_data['login_id']

        employee.save()
        print("EMPLOYEE TABLE UPDATED")

        emp_serializer = EmployeeSerializer(employee)
        return emp_serializer.data


    #we use this in the case of the form when an employee matches.
    # we have all the data we need from the from, so we are going to pass it
    # directly to the employee object.


    def post(self, request, *args, **kwargs):
        data = request.data
        uname_is_unique = None

        if "employee_id_check" in data:
            emp = self.check_id_name_match(data)  # returns employee object or 0
            if not emp:
                return HttpResponse(0)
            else:
                empData = EmployeeSerializer(emp).data
                return Response(empData)

        if 'username' in request.data:
            uname_is_unique = self.username_unique_check(data)

        if 'username_check' in request.data:
            return HttpResponse(uname_is_unique)

        #TODO: check if invite is active

        if not uname_is_unique:
            return HttpResponse("Username is already taken", status=409)

        print(data)
        if 'employee_id' in data:
            if data['employee_id'] is None:
                employee = self.create_employee_with_flag(data)
                data["employee_id"] = employee['id']

            if data['employee_id'] is not None:
                user_data = self.create_user_by_login_id(data)
                #if user_data is None:
                    #return HttpResponse("Login ID is already taken.", status=413)

        else:
            user_data = self.create_user(data)

        if not user_data:
            return HttpResponse("Something went wrong when creating a user")



        output = user_data

        return Response(output, status=status.HTTP_200_OK)

    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    serializer_class = jwt_serializers.TokenObtainPairSerializer


@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'token': reset_password_token.key.upper(),
        'reset_password_url': "{}?token={}".format('https://aaane-mtk.wageup.com/reset-password', reset_password_token.key)
    }

    # render email text
    email_html_message = render_to_string('accounts/user_reset_password.html', context)
    email_plaintext_message = render_to_string('accounts/user_reset_password.txt', context)

    email = {
        'to': reset_password_token.user.email,
        'subject': "Password Reset for {title}".format(title="the MTK and Roadside Dashboard"),
        'from': f'"noreply@wageup.com"',
        'goTo': {
          'name': 'Reset Password',
          'url':   "{}?token={}".format('https://aaane-mtk.wageup.com/reset-password', reset_password_token.key)
        },
        'replyTo': False,
        'message': email_plaintext_message,
        'image': 'message.png'
    }

    send_email(email)



    # msg = EmailMultiAlternatives(
    #     # title:
    #     "Password Reset for {title}".format(title="the MTK and Roadside Dashboard"),
    #     # message:
    #     email_plaintext_message,
    #     # from:
    #     "noreply@wageup.com",
    #     # to:
    #     [reset_password_token.user.email]
    # )
    # msg.attach_alternative(email_html_message, "text/html")
    # msg.send()

@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
@receiver(pre_password_reset)
def password_reset_notify_email_changed(sender, instance, user,new_email, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    context = {
        'current_user': user,
        'username': user.username,
        'email': new_email
    }

    # render email text
    email_html_message = render_to_string('accounts/user_email_changed_notification.html', context)
    email_plaintext_message = render_to_string('accounts/user_reset_password.txt', context)

    msg = EmailMultiAlternatives(
        # title:
        "Email Reset for {title}".format(title="the AAA My Toolkit App and Roadside Dashboard"),
        # message:
        email_plaintext_message,
        # from:
        "noreply@wageup.com",
        # to:
        [user.email]
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()

class ModelQueries:
    class Employee:
        class List(generics.ListCreateAPIView):
            permission_classes = ()
            authentication_classes = ()

            serializer_class = EmployeeSerializer


            def get(self, request):
                queryset = Employee.objects.all()

            def post(self, request):

                if 'employee_lookup' in request.data:
                    return Response(EmployeeSerializer(Employee.objects.get(id=request.data['employee_lookup'])).data, status=status.HTTP_202_ACCEPTED)

                if 'org_id' in request.data:
                    organization = Organization.objects.get(id=request.data["org_id"])
                    if 'all_types' in request.data:
                        queryset = organization.employees(emp_type=False).exclude(active=0)
                        print("GETTING ALL EMPLOYEES FOR ORG", queryset)
                    elif organization.type == 'Facility-State':
                        org_set = organization.children()
                        queryset = Employee.objects.filter(organization__in=org_set).exclude(active=0)
                    else:
                        queryset = Employee.objects.filter(organization=organization.employees_under).exclude(active=0)
                        # queryset = Employee.objects.filter(parallel_organizations__in=[organization]).exclude(active=0) # for maybe State?
                    if 'driver_profile' in request.data and request.data['driver_profile'] == True:
                        # employee_list = queryset.values_list('id', flat=True)
                        # print('accounts view, employee under:',organization.employees_under)
                        # profiles = EmployeeProfile.objects.filter(employee__in=employee_list).exclude(active=0).values_list('employee', flat=True)
                        # # employees = profiles
                        # queryset = queryset.filter(id__in=profiles).order_by('first_name', 'last_name')
                        # data = EmployeeProfileAllSerializer(queryset, many=True).data
                        if request.data['is_driver'] == True:
                            driver_id = request.data['driver_id']
                            queryset = queryset.filter(id=driver_id)
                        else:
                            queryset = queryset.exclude(employee_profile__active=0).order_by('first_name', 'last_name')

                        return Response(self.get_driver_profile_data(queryset))
                    # if 'request_time_off' in request.data and request.data['profile_save_changes'] is True:
                    if 'profile_save_changes' in request.data and request.data['profile_save_changes'] == True:
                        drivers = request.data['parameters']['drivers']
                        drivers_list = [d['id'] for d in drivers]
                        profiles = EmployeeProfile.objects.filter(employee_id__in=drivers_list)
                        for d in drivers:
                            profile = profiles.get(employee_id=d['id'])
                            profile.trouble_code_type = d['tcd']
                            profile.active_not_available = d['active_not_available']
                            profile.save()

                        entries = request.data['parameters']['entries']
                        entry_list = [e['id'] for e in entries]
                        profile_entries = EmployeeProfileEntries.objects.filter(id__in=entry_list)

                        for e in entries:
                            entry = profile_entries.get(id=e['id'])
                            entry.type = e['type']
                            entry.start_time = e['start_time']
                            entry.end_time = e['end_time']
                            entry.save()

                        return Response({'success': True, 'message': 'Employee profiles have been saved!'})

                    if 'profile_bulk' in request.data:
                        params = request.data['parameters']
                        profiles = EmployeeProfile.objects.filter(employee__in=params['apply_to'])
                        if params['bulk_action'] == 'delete':
                            for p in profiles:
                                p.active = False
                                p.save()
                        elif params['bulk_action'] == 'available':
                            for p in profiles:
                                p.active_not_available = False
                                p.save()
                        elif params['bulk_action'] == 'unavailable':
                            for p in profiles:
                                p.active_not_available = True
                                p.save()
                        else:
                            for p in profiles:
                                if p.trouble_code_type is None:
                                    if params['bulk_action'] == 'Other':
                                        tcd = 'Light Service'
                                    else:
                                        tcd = params['bulk_action']
                                    p.trouble_code_type = tcd
                                    p.save()
                                elif params['bulk_action'] not in p.trouble_code_type or (params['bulk_action'] == 'Other' and 'Light Service' not in p.trouble_code_type):
                                    if params['bulk_action'] == 'Other':
                                        tcd = 'Light Service'
                                    else:
                                        tcd = params['bulk_action']
                                    if 'Battery' in p.trouble_code_type or 'Tow' in p.trouble_code_type or 'Light Service' in p.trouble_code_type:
                                        p.trouble_code_type += ', {0}'.format(tcd)
                                    else:
                                        p.trouble_code_type = tcd
                                    p.save()
                        return Response(True)
                    data = ShortEmployeeSerializer(queryset, many=True).data
                    return Response(data)

                elif 'org_slug' in request.data:
                    organization = Organization.objects.get(slug=request.data["org_slug"])
                    print(organization)
                    queryset = Employee.objects.filter(organization=organization).exclude(active=0)
                    data = ShortEmployeeSerializer(queryset, many=True).data
                    return Response(data)

                elif 'fleet-supervisor' in request.data:
                    queryset = Employee.objects.filter(position_type='Fleet-Supervisor')
                    data = ShortEmployeeSerializer(queryset, many=True).data
                    return Response(data)
                else:
                    return Response("You need to submit an org_slug or org_id post key", status=500)



            def get_driver_profile_data(self, queryset):
                queryset = queryset.filter(position_type='Driver')
                driver_list = queryset.values_list('id', flat=True)
                data = queryset.values('id', 'first_name', 'last_name', 'user', 'position_type',
                                       'active', 'employee_profile__id', 'employee_profile__employee',
                                       'employee_profile__trouble_code_type', 'employee_profile__active',
                                       'employee_profile__active_not_available',
                                       'employee_profile__employee_profile_entries__id',
                                       'employee_profile__employee_profile_entries__day_of_week',
                                       'employee_profile__employee_profile_entries__start_time',
                                       'employee_profile__employee_profile_entries__end_time',
                                       'employee_profile__employee_profile_entries__type',
                                       'employee_profile__employee_profile_entries__pto_start',
                                       'employee_profile__employee_profile_entries__pto_end')
                from itertools import groupby
                drivers = []
                for driver, driver_data in groupby(data, lambda x: x['id']):
                    driver_data = list(driver_data)
                    global_data = driver_data[0]
                    d = {}

                    for dd in ['id', 'first_name', 'last_name', 'user', 'position_type', 'active']:
                        d[dd] = global_data[dd]
                    d['employee_profile'] = [{}, ]
                    for dd in ['employee_profile__id', 'employee_profile__trouble_code_type', 'employee_profile__active',
                               'employee_profile__active_not_available']:
                        d['employee_profile'][0][dd.replace('employee_profile__', '')] = global_data[dd]

                    d['employee_profile'][0]['employee_profile_entries'] = []
                    for entry in driver_data:
                        e = {}
                        for dd in ['employee_profile__employee_profile_entries__id',
                                   'employee_profile__employee_profile_entries__day_of_week',
                                   'employee_profile__employee_profile_entries__start_time',
                                   'employee_profile__employee_profile_entries__end_time',
                                   'employee_profile__employee_profile_entries__type',
                                   'employee_profile__employee_profile_entries__pto_start',
                                   'employee_profile__employee_profile_entries__pto_end']:
                            e[dd.replace('employee_profile__employee_profile_entries__', '')] = entry[dd]
                        d['employee_profile'][0]['employee_profile_entries'].append(e)
                    drivers.append(d)
                pto_requests = ApprovalRequestEmployeeTimeOff.objects.filter(request_data__requester__id__in=driver_list, request_data__status='Pending_Review').count()
                av_request = ApprovalRequestEmployeeAvailability.objects.filter(request_data__requester__id__in=driver_list, request_data__status='Pending_Review').count()
                total_requests = pto_requests + av_request
                return {'drivers': drivers, 'total_requests': total_requests}

        class Detail(generics.RetrieveUpdateDestroyAPIView):

            def post(self, request):
                data = request.data

                user_employee = Employee.objects.get(user=request.user)
                permissions = list(user_employee.permission.all().values_list('name', flat=True))
                user_org = user_employee.organization

                self.user = request.user


                if 'recent_actions' in data:
                    queryset = UserActions.objects.filter(user=self.user)

                    if 'from_date' in data:
                        queryset = queryset.filter(date__gte=data['from_date'])

                    if 'end_date' in data:
                        queryset = queryset.filter(date__gte=data['end_date'])

                    if 'selectedActionType' in data:
                        queryset = queryset.filter(type__in=data['selectedActionType'])


                    queryset = queryset.order_by('-date')
                    if 'last_n' in data:
                        queryset = queryset[:int(data['last_n'])]

                    serializer = RecentActionsSerializer(queryset, many=True)
                    return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

                if 'request_pto' in data:
                    new_data = {
                        'org_id': data['org_id'],
                        'employee': data['employee'],
                        'pto_start': data['pto_start'],
                        'pto_end': data['pto_end'],
                        'type': data['type']

                    }

                    serializer = EmployeeTimeOffSerializer(data=new_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
                    else:
                        return Response(serializer.errors, status=status.HTTP_406_NOT_ACCEPTABLE)

                if 'request_availability' in data:
                    new_data = {
                        'org_id': data['org_id'],
                        'employee': data['employee'],
                        'day_of_week': data['day_of_week'],
                        'start_time': data['start_time'],
                        'end_time': data['end_time']
                    }


                    serializer = EmployeeRequestedAvailabilitySerializer(data=new_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
                    else:
                        return Response(serializer.errors, status=status.HTTP_406_NOT_ACCEPTABLE)

                if 'edit_info' in data:
                    queryset = Employee.objects.get(id=data['employee_id'])
                    update_data = {'first_name': data['first_name'], 'last_name': data['last_name']}
                    serializer = ShortEmployeeSerializer(queryset, data=update_data)
                    if serializer.is_valid():
                        serializer.save()
                        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
                    else:
                        return Response(serializer.errors, status=status.HTTP_406_NOT_ACCEPTABLE)
                elif 'scheduler_info' in data:
                    employee = Employee.objects.get(id=data['employee_id'])
                    params = data['parameters']
                    if 'trouble_code' in params:
                        em_profile = EmployeeProfile.objects.get(id=data['employee_profile'])
                        em_profile.trouble_code_type = params['trouble_code']
                        em_profile.save()
                        output = EmployeeProfileAllSerializer(employee).data
                        return Response(output)
                    if 'profile_entry' in params:
                        entry = EmployeeProfileEntries.objects.get(id=params['profile_entry'])
                        if params['type'] == True or params['type'] == 'is not available':
                            entry.type = 'is not available'
                            entry.start_time = None
                            entry.end_time = None
                        else:
                            print(params['start_time'], params['end_time'])
                            entry.start_time = params['start_time']
                            entry.end_time = params['end_time']
                            entry.type = 'is available'
                            print(entry.start_time, entry.end_time)
                        entry.save()
                        output = EmployeeProfileAllSerializer(employee).data
                        return Response(output)
                    if 'new_pto' in params:
                        em_profile = EmployeeProfile.objects.get(id=data['employee_profile'])
                        reason = 'pto - {0}'.format(params['reason'])
                        entry = EmployeeProfileEntries.objects.create(
                            driver_profile=em_profile,
                            pto_start=params['pto_start'],
                            pto_end=params['pto_end'],
                            type=reason
                        )
                        entry.save()
                        output = EmployeeProfileEntriesSerializer(entry).data
                        return Response(output)
                    if 'edit_pto' in params:
                        entry = EmployeeProfileEntries.objects.get(id=params['pto_id'])
                        entry.pto_start = params['pto_start']
                        entry.pto_end = params['pto_end']
                        entry.type = params['type']
                        entry.save()
                        output = EmployeeProfileEntriesSerializer(entry).data
                        return Response(output)

                    if 'delete_pto' in params:
                        entry = EmployeeProfileEntries.objects.get(id=params['pto_id'])
                        entry.delete()
                        output = EmployeeProfileAllSerializer(employee).data
                        return Response(output)



                    if 'driver_active_not_available' in params:
                        em_profile = EmployeeProfile.objects.get(id=data['employee_profile'])
                        em_profile.active_not_available = params['active_na']
                        em_profile.save()
                        output = EmployeeProfileAllSerializer(employee).data
                        return Response(output)



                if 'my_org_users' in data:
                    queryset = Employee.objects.filter(organization_id=user_org.id, user_id__isnull=False)
                    data = ShortEmployeeSerializer(queryset, many=True).data
                    print(data)
                    return Response(data)

                # for emp in range(len(data)):
                #     if 'org_slug' in data[emp]:
                #         data[emp]['organization'] = Organization.objects.get(slug=emp['org_slug']).id

                print(permissions)
                print(user_org.id)

                if 'create-employee' in permissions:
                    proceed=True
                elif 'create-child-employees' in permissions:
                    eligible_orgs = list(user_org.org_children().values_list('id', flat=True))
                    eligible_orgs.append(user_org.id)
                    proceed=True
                    for emp in data:
                        if emp['organization'] not in eligible_orgs:
                            proceed=False
                            break
                else:
                    proceed=False

                # api healthcheck
                necessary_params = ['organization', 'first_name', 'last_name', 'position_type', "permission"]

                if proceed:
                    employee_types = list(Employee.objects.order_by().values_list('position_type', flat=True).distinct())
                    for emp in data:
                        if not all(param in necessary_params for param in emp):
                            return Response("Missing parameters. Please pass at least" + str(necessary_params), status=status.HTTP_406_NOT_ACCEPTABLE)
                    for emp in data:
                        if emp['position_type'] not in employee_types:
                            if user_employee.position_type != 'Admin':
                                return Response("This position type is new! If this is intentional please post as an Admin employee otherwise please select from the following choices:" + str(employee_types), status=status.HTTP_406_NOT_ACCEPTABLE)



                if proceed:
                    succesful = []
                    for emp in data:
                        emp['latest_activity_on'] = dt.date.today()
                        emp['registered_by'] = request.user.id
                        print(emp)

                        necessary_params = ['organization', 'first_name', 'last_name', 'position_type', "permission"]

                        serializer = AddEmployeeSerializer(data=emp)
                        if serializer.is_valid():
                            serializer.save()
                            print(serializer.data)
                            print("SUCCESS!")
                            succesful.append(serializer.data)
                        else:
                            return Response(emp, status=status.HTTP_406_NOT_ACCEPTABLE)
                    return Response(succesful, status=status.HTTP_201_CREATED)
                else:
                    return Response("ACCESS DENIED", status=status.HTTP_406_NOT_ACCEPTABLE)

            queryset = Employee.objects.all()
            serializer_class = EmployeeSerializer

    class Organization:
        class List(generics.ListCreateAPIView):

            permission_classes = ()
            authentication_classes = ()

            def eligible_types(self, vertical):
                if not vertical:
                    return ['Market', 'Territory', 'Station-Business', 'Station', 'Driver', 'Call-Center', 'Call-Center-Group']
                if vertical == 'roadside':
                    return ['Market', 'Territory', 'Station-Business', 'Station', 'Driver']
                elif vertical == 'call-center':
                    return ['Call-Center', 'Call-Center-Group']

            def get(self, request, format=None):

                if request.GET.get('type'):
                    searched_type = request.GET.get('type')
                    orgs = Organization.objects.filter(type=searched_type)
                    if searched_type == 'Station-State':
                        orgs = Organization.objects.filter(type=searched_type, latest_activity_on__gte='2021-01-01')
                    serializer = ShortOrganizationSerializer(orgs, many=True)
                    return Response(serializer.data)


                org = Organization.objects.get(slug=request.GET.get('slug'))

                if request.GET.get('vertical'):
                    vertical = request.GET.get('vertical')
                else:
                    vertical = False

                if request.GET.get('relation') == 'children':
                    serializer = ShortOrganizationSerializer(org.children().filter(type__in=self.eligible_types(vertical)), many=True)
                    if serializer.data[0]['name'] is None:
                        serializer = EmployeeSerializer(org.children().filter(type__in=self.eligible_types(vertical)), many=True)
                    return Response(serializer.data)
                elif request.GET.get('relation') == 'siblings':
                    serializer = ShortOrganizationSerializer(org.siblings().filter(type__in=self.eligible_types(vertical)), many=True)
                    return Response(serializer.data)
                elif request.GET.get('relation') == 'employees':
                    serializer = EmployeeSerializer(org.employees(), many=True)
                    return Response(serializer.data)
                else:
                    serializer = ShortOrganizationSerializer(org)
                    return Response(serializer.data)

            def post(self, request):
                data = request.data
                if 'slug' in data:
                    try:
                        org = Organization.objects.get(slug=data['slug'])
                    except ObjectDoesNotExist:
                        employee = Employee.objects.get(slug=data['slug'])
                        duplicates = employee.cross_territory_duplicates()
                        data = EmployeeSerializer(employee).data

                        if duplicates:
                            data['duplicates'] = duplicates

                        return Response(data, status=status.HTTP_202_ACCEPTED)
                elif 'org_id' in data:
                    if data['org_id'] is None:
                        try:
                            org = Organization.objects.get(parent_id__isnull=True)
                        except MultipleObjectsReturned:
                            org = Organization.objects.get(id=7) # Note this only works with ACA!
                    else:
                        org = Organization.objects.get(id=data['org_id'])


                if 'vertical' in data:
                    vertical = data['vertical']
                else:
                    vertical = False

                if 'relation' not in data:
                    data['relation'] = False
                if data['relation'] == 'children':
                    if org.type == 'Club':
                        serializer = OrganizationSerializer(Organization.objects.filter(type='Station-State').order_by('name'), many=True)
                        return Response(serializer.data)
                    else:
                        children = org.children().filter(type__in=self.eligible_types(vertical)).exclude(latest_activity_on='2010-01-01').order_by('name')
                        print(children)
                    if data.get('only_active_sb_days'):
                        if children[0].type != 'Station':
                            children = org.lineage('Station')
                            children = Organization.objects.filter(id__in=children)
                        print('Just getting active stations within specified days')
                        cutoff = dt.datetime.today() - dt.timedelta(days=data.get('only_active_sb_days'))
                        print('cutoff is', cutoff)
                        recent_stations = StationDriver.objects.filter(last_sc_dt__gt=cutoff).values_list('station_id', flat=True).distinct().order_by()
                        children = children.filter(id__in=recent_stations).order_by('name')
                        print('got children')
                        if data.get('quick'):
                            return Response(list(children.values('slug', 'name')))
                    serializer = OrganizationSerializer(children, many=True)
                    if serializer.data[0]['name'] is None:
                        serializer = EmployeeSerializer(org.children().filter(type__in=self.eligible_types(vertical)), many=True)
                    return Response(serializer.data)
                if data['relation'] == 'siblings':
                    serializer = OrganizationSerializer(org.siblings().filter(type__in=self.eligible_types(vertical)), many=True)
                    return Response(serializer.data)
                if data['relation'] == 'employees':
                    emps = org.employees()
                    if data.get('last_thirty'):
                        emps = org.employees()
                        today = dt.datetime.now()
                        thirty_days = today - dt.timedelta(days=60)
                        employee_list = emps.exclude(active=False).values_list('id', flat=True)
                        active_employees = StationDriver.objects.filter(driver_id__in=employee_list,
                                                                        last_sc_dt__gte=thirty_days)\
                            .values_list('driver_id', flat=True)
                        print('ACTIVE EMPLOYEES', active_employees)

                        emps = emps.filter(id__in=active_employees)
                        print('EMPS', emps)
                    print(emps)
                    if data.get('shorter'):

                        emps = org.employees().annotate(
                            email=F('user__email'),
                            username=F('user__username'),
                            organization_name=F('organization__name')
                        )
                        print(emps)
                        if data.get('last_thirty'):
                            emps = emps.filter(id__in=active_employees)
                        emps = emps.order_by('last_name').values('id', 'email', 'slug', 'username', 'organization', 'first_name', 'last_name', 'full_name', 'active')
                        out = []
                        names = []
                        for e in emps:
                            if e['full_name'] in names and e['email'] is None:
                                # print(e)
                                continue
                            elif e['full_name'] in names and e['email'] is not None:
                                idx = next(i for (i, n) in enumerate(out) if n['full_name'] == e['full_name'])
                                print(idx, e, out[idx])
                                out[idx] = e
                            else:
                                out.append(e)
                                names.append(e['full_name'])
                        # print(names)
                        return Response(out)

                        # serializer = SimpleEmployeeSerializer(emps, many=True)
                    else:
                        # emps = org.employees()
                        serializer = EmployeeSerializer(emps.order_by('last_name'), many=True)
                        serialized_data = serializer.data
                        return Response(serialized_data)
                else:
                    serializer = OrganizationSerializer(org)
                    return Response(serializer.data)
            queryset = Organization.objects.all()
            serializer_class = AddOrganizationSerializer

        class Detail(generics.RetrieveUpdateDestroyAPIView):
            queryset = Organization.objects.all()
            serializer_class = OrganizationSerializer

    class Profile:

        permission_classes = (IsAuthenticated,)

        class List(generics.ListCreateAPIView):

            queryset = Profile.objects.all()
            serializer_class = ProfileSerializer

        class Detail(generics.RetrieveUpdateDestroyAPIView):

            def post(self, request):
                try:
                    queryset = Profile.objects.get(user=request.user)

                except ObjectDoesNotExist:
                    Profile(user=request.user, slug=request.user.username, employee=request.user.employee()).save()
                    queryset = Profile.objects.get(user=request.user)

                serializer = ProfileSerializer(queryset, data=request.data, partial=True)
                print(request.data)

                if 'email' in request.data:
                    try:
                        request.user.email = request.data['email']
                        request.user.save()
                        try:
                            cu = CampaignUser.objects.get(user=request.user)
                            if cu:
                                cu.email = request.data['email']
                                cu.save()
                        except Exception as e:
                            print(e)
                    except Exception as e:
                        print(e)

                if serializer.is_valid():

                    serializer.save()
                    print(serializer.data)
                else:
                    print(request.data)
                    raise Exception("serializer invalid")

                return Response(serializer.data)

            queryset = Profile.objects.all()
            serializer_class = ProfileSerializer

    class Appeals:

        permission_classes = (IsAuthenticated,)

        class List(generics.ListCreateAPIView):

            queryset = ApprovalRequestAppeals.objects.all()
            serializer_class = ApprovalRequestAppealsSerializer

            def post(self, request):
                data = request.data
                if data['purpose'] == 'survey_appeals':
                    employee = Employee.objects.get(user=request.user)
                    org = Organization.objects.get(slug=data['geography_slug'])
                    stations = org.lineage('Station-Business')
                    # if org.type != 'Station-Business' or org.type != 'Station':
                    #
                    # elif org.type == 'Station':
                    #     stations = [org.parent]
                    # else:
                    #     stations = org.lineage('S')

                    surveys = Std12EReduced.objects.filter(org_business_id__in=stations, appeals_request__isnull=False)\
                        .annotate(requester_name=F('appeals_request__request_data__requester__display_name'),
                                  request_date=F('appeals_request__request_data__submission_date'),
                                  request_reason=F('appeals_request__appeals_reason'),
                                  status=F('appeals_request__request_data__status'),
                                  org_id=F('sp_fac_id'),
                                  org_name=F('org_business_id__name'),
                                  territory_name=F('org_territory_id__name'),
                                  verbatim=F('q30'),
                                  overall_sat_true=F('outc1'),
                                  driver_sat=F('driver10'),
                                  decision_note=F('appeals_request__request_data__approver_notes'),
                                  decision_date=F('appeals_request__request_data__review_date'),
                                  requester_notes=F('appeals_request__request_data__requester_notes'),
                                  exception_granted=F('appeals_request__exception_granted'),
                                  reviewer_appeals_reason=F('appeals_request__reviewer_appeals_reason'))\
                        .values('id',
                                'sc_id_surveys',
                                'sc_dt_surveys',
                                'org_id',
                                'org_name',
                                'territory_name',
                                'overall_sat_true',
                                'driver_sat',
                                'verbatim',
                                'requester_name',
                                'request_reason',
                                'request_date',
                                'requester_notes',
                                'status',
                                'reviewer_appeals_reason',
                                'decision_note',
                                'decision_date',
                                'exception_granted').order_by('-request_date')
                    return Response(surveys, status=status.HTTP_200_OK)
                return Response({'message': 'Something went wrong'}, status=status.HTTP_400_BAD_REQUEST)

        class Detail(generics.RetrieveUpdateDestroyAPIView):

            def post(self, request):
                data = request.data
                if data.get('purpose') == 'new_appeal':
                    survey = Std12EReduced.objects.get(id=data.get('survey_id'))
                    del request.data['survey_id']
                    del request.data['purpose']
                    comment = data.get('additional_comment', None)
                    del request.data['additional_comment']
                    approval_request_obj = ApprovalRequests.objects.create(
                        requester=Employee.objects.get(user=request.user),
                        requester_notes=comment
                    )
                    data['request_data_id'] = approval_request_obj.id
                    print(data)
                    print(survey)
                    appeals_request = ApprovalRequestAppeals.objects.create(
                        **data
                    )
                    appeals_request.reviewer_appeals_reason = appeals_request.appeals_reason
                    appeals_request.save()
                    survey.appeals_request = appeals_request
                    survey.save()
                    out = ApprovalRequestAppealsSerializer(appeals_request).data
                    out.update(model_to_dict(survey, fields=['outc1', 'sc_dt_surveys', 'sc_id_surveys']))


                    return Response(out, status=status.HTTP_200_OK)
                elif data.get('purpose') == 'update_appeal':
                    survey = Std12EReduced.objects.get(id=data.get('survey_id'))
                    approve_req = ApprovalRequestAppeals.objects.get(id=survey.appeals_request.id)
                    request_data = approve_req.request_data
                    request_data.review_date = dt.datetime.now()
                    print(data['decision'])
                    if approve_req.appeals_reason == 'different_driver':
                        if data['decision'] == 'Approved' or data['decision'] == 'Exception_Granted':
                            request_data.status = 'Approved-Remove'
                        else:
                            request_data.status = data['decision']
                    else:
                        if data['decision'] == 'Approved' or data['decision'] == 'Exception_Granted':
                            request_data.status = 'Approved-Reroute'
                        else:
                            request_data.status = data['decision']
                    if data['decision'] == 'Exception_Granted':
                        approve_req.exception_granted = True
                        approve_req.save()
                    else:
                        if approve_req.exception_granted is True:
                            approve_req.exception_granted = False
                            approve_req.save()

                    approve_req.reviewer_appeals_reason = data['reviewer_appeal']
                    approve_req.save()
                    # request_data.status = data['decision']
                    request_data.approver_notes = data['decision_note']
                    request_data.approver = Employee.objects.get(user=request.user)
                    request_data.save()
                    out = ApprovalRequestAppealsSerializer(approve_req).data
                    return Response(out, status=status.HTTP_200_OK)
                else:
                    return Response({'error': True}, status=status.HTTP_400_BAD_REQUEST)


            queryset = ApprovalRequestAppeals.objects.all()
            serializer_class = ApprovalRequestAppealsSerializer

    class SchedulerDriver:

        permission_classes = (IsAuthenticated,)

        class List(generics.ListCreateAPIView):
            queryset = ApprovalRequests.objects.all()
            serializer_class = ApprovalRequestAppealsSerializer

            def post(self, request):
                """ this is meant for the website where the manager or the person making the schedules to get all the
                 requests from the drivers, it will show the for both PTO request or Availability changes """
                data = request.data
                org = Organization.objects.get(slug=data.get('slug'))
                print('getting all the requests')
                employees = Employee.objects.filter(organization=org.employees_under).exclude(
                    Q(active=0) | Q(employee_profile__active=0))
                emp_list = employees.values_list('id', flat=True)
                pto_req = ApprovalRequestEmployeeTimeOff.objects.filter(request_data__requester_id__in=emp_list)
                av_req = ApprovalRequestEmployeeAvailability.objects.filter(request_data__requester_id__in=emp_list)
                current_availability = {
                    'Sunday': 'employee_id__'
                }
                pending_pto = pto_req.filter(request_data__status='Pending_Review').count()
                pending_av = av_req.filter(request_data__status='Pending_Review').count()
                pto_req = pto_req.annotate(employee_id=F('request_data__requester_id'),
                                           employee_name=F('request_data__requester__full_name'),
                                           status=F('request_data__status'),
                                           requester_reason=F('request_data__requester_notes'),
                                           approver_reason=F('request_data__approver_notes')) \
                    .values('id', 'employee_id', 'employee_name', 'pto_start', 'pto_end', 'status', 'requester_reason', 'approver_reason')
                av_req = av_req.annotate(employee_id=F('request_data__requester_id'),
                                         employee_name=F('request_data__requester__full_name'),
                                         status=F('request_data__status'),
                                         requester_reason=F('request_data__requester_notes'),
                                         approver_reason=F('request_data__approver_notes')) \
                    .values('id', 'employee_id', 'employee_name', 'day_of_week', 'start_time', 'end_time', 'status', 'prev_start', 'prev_end', 'requester_reason', 'approver_reason')
                fill_req = []
                fill_open = ScheduleOpenAvailability.objects.filter(organization=org, open=True)
                fill_close = ScheduleOpenAvailability.objects.filter(organization=org, open=False).order_by('-date_schedule')[0:5]
                # fill_req_yes = fill_req.aggregate()
                for f in fill_open:
                    fill_req.append(f)
                print(fill_req)
                for f in fill_close:
                    fill_req.append(f)
                print(fill_req)
                fill_req = ScheduleOpenAvailabilitySerializer(fill_req, many=True).data

                output = {'pto_requests': pto_req, 'availability_requests': av_req, 'schedule_fill_requests': fill_req, 'pending_av': pending_av, 'pending_pto': pending_pto}
                print(output)
                return Response(output, status=status.HTTP_200_OK)

        class Detail(generics.RetrieveUpdateDestroyAPIView):
            def get_requested_availabilities(self, params):
                print('IS IT GETTING TO THE FUNCTIIIOOOOOOONNNNN')
                availabilities = ApprovalRequestEmployeeAvailability.objects.filter(request_data__requester_id=params.get('employee_id'))
                availabilities_output = ApprovalRequestEmployeeAvailabilitySerializer(availabilities, many=True).data
                return {'availabilities': availabilities_output}

            def get_requested_pto(self, params):
                pto = ApprovalRequestEmployeeTimeOff.objects.filter(request_data__requester=params.get('employee_id'))
                pto_output = ApprovalRequestEmployeeTimeOffSerializer(pto, many=True).data
                return {'output': pto_output}

            def approve_reject_pto(self, params):
                """ Manger approves or rejects Driver's request for PTO

                {
                    "purpose": "approve_reject_pto",
                    "parameters": {
                        "multiple": boolean,
                        "request_id": if multiple: array of int else: int,
                        "decision": string (approve or reject),
                        "reason": string
                    }
                }

                """
                decision = params.get('decision')
                multiple = params.get('multiple')
                if decision == 'Rejected':
                    if multiple:
                        all_requests = ApprovalRequestEmployeeTimeOff.objects.filter(id__in=params.get('request_id'))
                        for a in all_requests:
                            a.request_data.status = 'Rejected'
                            a.request_data.approver_notes = params.get('reason', None)
                            a.request_data.save()
                            a.save()
                        # output = ApprovalRequestEmployeeTimeOffSerializer(all_requests, many=True).data
                    else:
                        request = ApprovalRequestEmployeeTimeOff.objects.get(id=params.get('request_id'))
                        request.request_data.status = 'Rejected'
                        request.request_data.approver_notes = params.get('reason', None)
                        request.request_data.save()
                        request.save()
                        # output = ApprovalRequestEmployeeTimeOffSerializer(request).data
                else:
                    if multiple:
                        all_requests = ApprovalRequestEmployeeTimeOff.objects.filter(id__in=params.get('request_id'))
                        new_pto = []
                        for a in all_requests:
                            a.request_data.status = 'Approved'
                            a.request_data.approver_notes = params.get('reason', None)
                            a.request_data.save()
                            a.save()
                            profile = EmployeeProfile.objects.get(employee=a.request_data.requester)
                            pto = EmployeeProfileEntries.objects.create(
                                driver_profile=profile,
                                pto_start=a.pto_start,
                                pto_end=a.pto_end,
                                type=a.request_data.requester_notes
                            )
                            new_pto.append(pto)
                        # output = EmployeeProfileEntriesSerializer(new_pto, many=True).data
                    else:
                        request = ApprovalRequestEmployeeTimeOff.objects.get(id=params.get('request_id'))
                        request.request_data.status = 'Approved'
                        request.request_data.approver_notes = params.get('reason', None)
                        request.request_data.save()
                        request.save()
                        profile = EmployeeProfile.objects.get(employee=request.request_data.requester)
                        pto = EmployeeProfileEntries.objects.create(
                            driver_profile=profile,
                            pto_start=request.pto_start,
                            pto_end=request.pto_end,
                            type=request.request_data.requester_notes
                        )
                        # output = EmployeeProfileEntriesSerializer(pto).data
                print('pre response')
                return {'completed': 'True'}

            def approve_reject_av(self, params):
                """ Manager approves or rejects Driver's request for change of availability

                {
                    "purpose": "approve_reject_av",
                    "parameters": {
                        "multiple": boolean,
                        "request_id": if multiple: array of int else: int,
                        "decision": string (approve or reject),
                        "reason": string
                    }
                }

                """
                decision = params.get('decision')
                multiple = params.get('multiple')
                print(decision)
                if decision == 'Rejected':
                    if multiple:
                        all_requests = ApprovalRequestEmployeeAvailability.objects.filter(id__in=params.get('request_id'))
                        for a in all_requests:
                            a.request_data.status = 'Rejected'
                            a.request_data.approver_notes = params.get('reason', None)
                            a.request_data.save()
                            a.save()
                        output = ApprovalRequestEmployeeAvailabilitySerializer(all_requests, many=True).data
                    else:
                        request = ApprovalRequestEmployeeAvailability.objects.get(id=params.get('request_id'))
                        request.request_data.status = 'Rejected'
                        request.request_data.approver_notes = params.get('reason', None)
                        request.request_data.save()
                        request.save()
                        output = ApprovalRequestEmployeeAvailabilitySerializer(request).data
                else:
                    if multiple:
                        all_requests = ApprovalRequestEmployeeAvailability.objects.filter(id__in=params.get('request_id'))
                        for a in all_requests:
                            a.request_data.status = 'Approved'
                            a.request_data.approver_notes = params.get('reason', None)
                            a.request_data.save()
                            a.save()
                            availability = EmployeeProfileEntries.objects.get(driver_profile__employee=a.request_data.requester,
                                                                              day_of_week=a.day_of_week)
                            availability.start_time = a.start_time
                            availability.end_time = a.end_time
                            availability.save()
                        output = ApprovalRequestEmployeeAvailabilitySerializer(all_requests, many=True).data
                    else:
                        request = ApprovalRequestEmployeeAvailability.objects.get(id=params.get('request_id'))
                        request.request_data.status = 'Approved'
                        request.request_data.approver_notes = params.get('reason', None)
                        request.request_data.save()
                        request.save()
                        availability = EmployeeProfileEntries.objects.get(driver_profile__employee=request.request_data.requester,
                                                                              day_of_week=request.day_of_week)
                        availability.start_time = request.start_time
                        availability.end_time = request.end_time
                        availability.save()
                        output = ApprovalRequestEmployeeAvailabilitySerializer(request).data

                return output

            def req_pto(self, params):
                """ Driver requests for PTO

                {
                    "purpose": "req_pto",
                    "parameters": {
                        "start_date": string, (YYYY-MM-DD)
                        "end_date": string, (YYYY-MM-DD)
                        "reason": string,
                        "employee_id": int
                    }
                }

                """
                start = params.get('start_date')
                end = params.get('end_date')
                reason = params.get('reason', None)
                emp = Employee.objects.get(id=params.get('employee_id'))
                request = ApprovalRequests.objects.create(
                    requester=emp,
                    status='Pending_Review',
                    requester_notes=reason
                )
                pto_request = ApprovalRequestEmployeeTimeOff.objects.create(
                    pto_start=start,
                    pto_end=end,
                    request_data=request
                )
                return ApprovalRequestEmployeeTimeOffSerializer(pto_request).data

            def availability_date_request(self, day, start_time, end_time, req_data):
                try:
                    entry = EmployeeProfileEntries.objects.filter(driver_profile__employee_id=req_data.requester.id, day_of_week=day)[0]
                    prev_start = entry.start_time
                    prev_end = entry.end_time
                except:
                    prev_start = None
                    prev_end = None
                req_av = ApprovalRequestEmployeeAvailability.objects.create(
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    request_data=req_data,
                    prev_start=prev_start,
                    prev_end=prev_end
                )
                req_av.save()
                return req_av

            def req_av(self, params):
                """ Driver requests for change of availability
                {
                    "purpose": "req_av",
                    "parameters": {
                        "multiple": boolean,
                        "day": if multiple: array of strings else string, (Sunday-Saturday)
                        "start_time": string, (hh:mm:ss)
                        "end_time": string, (hh:mm:ss)
                        "employee_id": int,
                        "reason": string
                    }
                }
                """
                multiple = params.get('multiple', False)
                emp = Employee.objects.get(id=params.get('employee_id'))
                start = params.get('start_time')
                end = params.get('end_time')
                reason = params.get('reason', '')
                if multiple:
                    days = params.get('day')
                    new_requests = []
                    for d in days:
                        request = ApprovalRequests.objects.create(
                            requester=emp,
                            status='Pending_Review',
                            requester_notes=reason
                        )
                        new_req = self.availability_date_request(d, start, end, request)
                        new_requests.append(new_req)
                    output = ApprovalRequestEmployeeAvailabilitySerializer(new_requests, many=True).data

                else:
                    day = params.get('day')
                    request = ApprovalRequests.objects.create(
                        requester=emp,
                        status='Pending_Review',
                        requester_notes=reason
                    )
                    new_req = self.availability_date_request(day, start, end, request)
                    output = ApprovalRequestEmployeeAvailabilitySerializer(new_req).data

                return output

            def req_driver_fill(self, params):
                """ This is where the manager can create a date and time that drivers can fill in a schedule

                {
                    "purpose": "req_driver_fill",
                    "parameters": {
                        "slug": string, (organization slug)
                        "date": string, (YYYY-MM-DD)
                        "start_time": string, (HH:mm:ss),
                        "end_time": string, (HH:mm:ss),
                        "service_type": string, (Tow, Battery, or Other)
                    }
                }

                """
                org = Organization.objects.get(slug=params.get('slug'))
                date = params.get('date')
                start_time = params.get('start_time')
                end_time = params.get('end_time')
                type = params.get('service_type')
                schedule = TimeseriesSchedule.objects.get_or_create(date=date, organization_id=org.id)[0]
                scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).values_list('employee_id', flat=True)
                employee_list = Employee.objects.filter(organization_id=org.employees_under.id, position_type='Driver')\
                    .exclude(Q(active=0) | Q(employee_profile__active=0), id__in=scheduled_drivers)
                employee_list = employee_list.values_list('id', flat=True)
                schedule_fill = ScheduleOpenAvailability.objects.create(
                    date_schedule=date,
                    start_time=start_time,
                    end_time=end_time,
                    organization=org,
                    service_type=type
                )
                schedule_fill.potential_drivers.add(*employee_list)
                schedule_fill.save()
                print('schedule fill created', schedule_fill)
                output = ScheduleOpenAvailabilitySerializer(schedule_fill).data
                return output

            def approve_reject_fill(self, params):
                """ Driver's decision if they can work on date that was available to fill

                {
                    "purpose": "approve_reject_fill",
                    "parameters": {
                        "schedule_fill_id": int, (id of the schedule fill)
                        "employee_id": int,
                        "decision": string, (Available or Not-Available)
                    }
                }

                """
                schedule_fill = ScheduleOpenAvailability.objects.get(id=params.get('schedule_fill_id'))
                employee = Employee.objects.get(id=params.get('employee_id'))
                decision = params.get('decision')
                if decision == 'Available':
                    schedule_fill.drivers_available.add(employee)
                    output = 'You have been added to the list of potential drivers to fill this spot for the schedule.  A Manager will review and decide if you will fill this spot.'
                else:
                    schedule_fill.drivers_rejected.add(employee)
                    output = 'You will not be chosen to fill this spot of the schedule.'
                schedule_fill.potential_drivers.remove(employee)
                schedule_fill.save()
                return {'message': output}

            def close_fill(self, params):
                """ Manager decide to close the fill no other driver can respond and the slots have been filled for the schedule
                {
                    "purpose": "close_fill",
                    "parameters": {
                        "schedule_fill_id": int, (id of the schedule fill)
                        "close": bool
                    }
                }
                """
                schedule_fill = ScheduleOpenAvailability.objects.get(id=params.get('schedule_fill_id'))
                schedule_fill.open = params.get('close')
                schedule_fill.save()
                return {'completed': True}

            def respond_and_fill(self, params):
                """ Managers decide who gets scheduled optional: close the fill
                 {
                    "purpose": 'respond_and_fill',
                    "parameters": {
                        "multiple": boolean, (if manager is scheduling multiple drivers in the same fill space)
                        "schedule_fill": int, (id of the fill: ScheduleOpenAvailability)
                        "organization_id": int,
                        "driver_id": if multiple: Array of int else: int (id of employee that will fill the schedule)
                        "keep_open": boolean, (keep this fill open in order for more drivers to respond)
                    }
                 }

                 """
                fill_details = ScheduleOpenAvailability.objects.get(id=params.get('schedule_fill'))
                org = Organization.objects.get(id=params.get('organization_id'))
                schedule = TimeseriesSchedule.objects.get(date=fill_details.date_schedule, organization_id=org.id)
                multiple = params.get('multiple', False)
                print(fill_details.date_schedule.year, fill_details.date_schedule.month, fill_details.date_schedule.day)
                date = dt.datetime(fill_details.date_schedule.year, fill_details.date_schedule.month, fill_details.date_schedule.day, 0, 0, 0)

                def get_duration(start, end):
                    # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
                    d_start = (start.hour + (start.minute / 60))
                    d_end = (end.hour + (end.minute / 60))
                    if d_start > d_end:
                        duration = ((d_end + 24) - d_start)
                    else:
                        duration = (d_end - d_start)
                    print('duration', duration)
                    return duration

                def get_end_date(start, end, s_date):
                    if start.hour > end.hour:
                        schedule_date = s_date + dt.timedelta(days=1)
                    else:
                        schedule_date = s_date
                    schedule_date = schedule_date.replace(hour=end.hour, minute=end.minute)
                    print(end.hour, end.minute, schedule_date)
                    return schedule_date

                if multiple:
                    drivers = Employee.objects.filter(id__in=params.get('driver_id'))
                    scheduled_drivers = []
                    for d in drivers:
                        s_driver = TimeseriesScheduledDrivers.objects.create(
                            employee=d,
                            start_date=date.replace(hour=fill_details.start_time.hour, minute=fill_details.start_time.minute),
                            end_date=get_end_date(fill_details.start_time, fill_details.end_time, date),
                            duration=get_duration(fill_details.start_time, fill_details.end_time),
                            schedule_type=fill_details.service_type,
                            schedule=schedule
                        )
                        scheduled_drivers.append(s_driver)
                        fill_details.drivers_accepted.add(d)
                        fill_details.drivers_available.remove(d)
                    # output = TimeseriesSchedule
                else:
                    s_driver = TimeseriesScheduledDrivers.objects.create(
                        employee=Employee.objects.get(id=params.get('driver_id')),
                        start_date=date.replace(hour=fill_details.start_time.hour, minute=fill_details.start_time.minute),
                        end_date=get_end_date(fill_details.start_time, fill_details.end_time, date),
                        duration=get_duration(fill_details.start_time, fill_details.end_time),
                        schedule_type=fill_details.service_type,
                        schedule=schedule
                    )
                all_scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
                self.save_daily_schedule(schedule.date, all_scheduled_drivers, org.id)

                fill_details.open = params.get('keep_open')
                fill_details.save()
                return {'message': 'schedule saved!'}

            def get_employee_list(self, org_id):
                org = Organization.objects.get(id=org_id)
                if org.type == 'Territory':
                    org_set = org.children()
                    employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
                else:
                    employees = Employee.objects.filter(organization=org.employees_under).exclude(
                        active=0).values_list('id', flat=True)

                employees = EmployeeProfile.objects.filter(
                    employee_id__in=employees.values_list('id', flat=True)).exclude(
                    active=0)
                employees_list = employees.values_list('employee_id', flat=True)
                return employees_list

            def save_daily_schedule(self, date, drivers, org_id):
                employees_list = self.get_employee_list(org_id)
                ghost_list = PlaceholderDriver.objects.filter(organization_id=org_id).values_list('id', flat=True)
                print(date)
                SchedulerReviewByDriver.objects.filter(
                    Q(date=date) & (Q(employee_id__in=employees_list) | Q(placeholder_id__in=ghost_list))).delete()
                scheduled_drivers_review = SchedulerReviewByDriver.objects.bulk_create(
                    [SchedulerReviewByDriver(
                        employee=d.employee,
                        date=d.start_date.date(),
                        starting_time=d.start_date,
                        ending_time=d.end_date,
                        duration=d.duration,
                        tcd=d.schedule_type,
                        off=False,
                        placeholder=d.placeholder
                    ) for d in drivers]
                )
                print('saved Daily Schedule', scheduled_drivers_review)

            def post(self, request):
                data = request.data
                print('inside the post for driver-request')
                purpose = {
                    'get_requested_availabilities': self.get_requested_availabilities,
                    'get_requested_pto': self.get_requested_pto,
                    'approve_reject_pto': self.approve_reject_pto,
                    'approve_reject_av': self.approve_reject_av,
                    'req_pto': self.req_pto,
                    'req_av': self.req_av,
                    'req_driver_fill': self.req_driver_fill,
                    'approve_reject_fill': self.approve_reject_fill,
                    'respond_and_fill': self.respond_and_fill,
                    'close_fill': self.close_fill
                }

                output = purpose[data.get('purpose')](data.get('parameters'))

                return Response(output, status=status.HTTP_200_OK)



    class Bookmark:

        permission_classes = (IsAuthenticated,)

        class Detail(generics.RetrieveUpdateDestroyAPIView):

            def post(self, request):

                if 'delete' in request.data:
                    Bookmarks.objects.get(id=request.data['id']).delete()
                    return Response(BookmarkSerializer(Bookmarks.objects.filter(user=request.user), many=True).data)


                bookmark = Bookmarks(user=request.user, display=request.data['display'], link=request.data['link'])
                bookmark.save()
                serializer = BookmarkSerializer(bookmark, data=request.data, partial=True)

                if serializer.is_valid():
                    serializer.save()

                return Response(serializer.data)

            queryset = Bookmarks.objects.all()
            serializer_class = BookmarkSerializer

    class Permission:
        class List(generics.ListCreateAPIView):

            queryset = Permissions.objects.all()
            serializer_class = PermissionSerializer

        class Detail(generics.RetrieveUpdateDestroyAPIView):
            queryset = Permissions.objects.all()
            serializer_class = PermissionSerializer

    class Invite:

        class List(generics.ListCreateAPIView):

            # permission_classes = ()
            # authentication_classes = ()

            print("WORKED")

            queryset = Invite.objects.all()
            serializer_class = InviteSerializer

        class Detail(generics.RetrieveUpdateDestroyAPIView):

            permission_classes = (IsAuthenticated, )

            serializer_class = None

            www_authenticate_realm = 'api'

            def get_authenticate_header(self, request):
                return '{0} realm="{1}"'.format(
                    AUTH_HEADER_TYPES[0],
                    self.www_authenticate_realm, )

            def find_eligible_employees(self, request):

                employee = Employee.objects.get(user=request.user)
                print(employee.id)
                permissions = employee.permission.all().values_list('name', flat=True)
                print(permissions)

                if 'invite-anyone' in permissions:
                    return "ALL"


            def allowed_to_invite(self, request):

                eligible_employees = self.find_eligible_employees(request)

                if eligible_employees == 'ALL':
                    return True
                for invited in request.data:
                    if invited['employee'] in eligible_employees:
                        continue
                    else:
                        print("CANT INVITE", invited['employee'])
                        return False
                return True


            def get(self, request):
                """
                This view gets called when creating a user, so we have
                most of the form already filled out, and we just need the username
                and password. It gets created by a manager


                :param request: id
                :return: return invite serialized object
                """
                print(request.method)

                if 'invite_code' in request.GET:
                    try:
                        invite = force_text(urlsafe_base64_decode(request.GET.get('invite_code')))
                        print(invite)
                        invite = Invite.objects.get(pk=invite)
                    except ObjectDoesNotExist:
                        return HttpResponse("This id does not exist or doesnt match the info we got.")
                else:
                    return HttpResponse("Invite ID not passed.")

                if invite.already_used:
                    print(invite.id)
                    return HttpResponse("This invite has already been used or is stale.")

                today = dt.date.today()
                if invite.expiration < today:
                    invite.already_used = True
                    invite.save()
                    return HttpResponse("This invite is too old")

                if invite.employee.user is not None:
                    return HttpResponse("This Employee already has a user assigned. Bad Invite")

                invite_data = InviteSerializer(invite).data
                return Response(invite_data)

            def post(self, request):
                """
                This if for creating an invite we need an employee id first.
                So, if we want to create a user: first we need an employee (Which requires an organization),
                then we create an invite for that employee

                :param request:
                email
                created_by -- user id who created invite
                employee -- id corresponding to employee

                :return:
                """

                if 'eligible_employees' in request.data:
                    eligible_employees = self.find_eligible_employees(request)
                    if eligible_employees != 'ALL':
                        employee_data = Employee.objects.filter(id__in=eligible_employees)
                    else:
                        employee_data = Employee.objects.filter(position_type=request.data['position_type'])
                        employee_data = employee_data.filter(organization_id__isnull=False)

                    if 'only_non_users' in request.data:
                        employee_data = employee_data.filter(user_id__isnull=True)

                    return Response(list(employee_data.values()), status=status.HTTP_201_CREATED)


                proceed = self.allowed_to_invite(request)

                if proceed:
                    successful = []
                    for invited in request.data:
                        invited['created_by'] = request.user.id
                        invited['sent_on'] = dt.datetime.utcnow()
                        serializer = CreateInviteSerializer(data=invited)
                        if serializer.is_valid():
                            serializer.save()
                            print(serializer.data)
                            invite = Invite.objects.get(id=serializer.data['id'])
                            invite.email_invite()
                            invite.sent_on = dt.datetime.utcnow()
                            invite.save()
                            employee = Employee.objects.get(id=invited['employee'])
                            employee.invited_on = dt.datetime.utcnow()
                            employee.save()
                            successful.append(serializer.data)
                            print("SUCCESS!")
                        else:
                            return Response(serializer.errors, status=status.HTTP_406_NOT_ACCEPTABLE)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response("ACCESS DENIED", status=status.HTTP_201_CREATED)


            queryset = Invite.objects.all()
            serializer_class = InviteSerializer

        class Detail_GET(generics.RetrieveUpdateDestroyAPIView):

            permission_classes = ()
            authentication_classes = ()

            serializer_class = None

            www_authenticate_realm = 'api'

            def get_authenticate_header(self, request):
                return '{0} realm="{1}"'.format(
                    AUTH_HEADER_TYPES[0],
                    self.www_authenticate_realm, )

            def find_eligible_employees(self, request):

                employee = Employee.objects.get(user=request.user)
                print(employee.id)
                permissions = employee.permission.all().values_list('name', flat=True)
                print(permissions)

                if 'invite-anyone' in permissions:
                    return "ALL"


            def allowed_to_invite(self, request):

                eligible_employees = self.find_eligible_employees(request)

                if eligible_employees == 'ALL':
                    return True
                for invited in request.data:
                    if invited['employee'] in eligible_employees:
                        continue
                    else:
                        print("CANT INVITE", invited['employee'])
                        return False
                return True


            def get(self, request):
                """
                This view gets called when creating a user, so we have
                most of the form already filled out, and we just need the username
                and password. It gets created by a manager


                :param request: id
                :return: return invite serialized object
                """
                print(request.method)

                if 'invite_code' in request.GET:
                    try:
                        invite = force_str(urlsafe_base64_decode(request.GET.get('invite_code')))
                        print(invite)
                        invite = Invite.objects.get(pk=invite)
                    except ObjectDoesNotExist:
                        return HttpResponse("This id does not exist or doesnt match the info we got.")
                else:
                    return HttpResponse("Invite ID not passed.")

                if invite.already_used:
                    print(invite.id)
                    return HttpResponse("This invite has already been used or is stale.")

                today = dt.date.today()
                if invite.expiration < today:
                    invite.already_used = True
                    invite.save()
                    return HttpResponse("This invite is too old")

                if invite.employee.user is not None:
                    return HttpResponse("This Employee already has a user assigned. Bad Invite")

                invite_data = InviteSerializer(invite).data
                return Response(invite_data)

            def post(self, request):
                """
                This if for creating an invite we need an employee id first.
                So, if we want to create a user: first we need an employee (Which requires an organization),
                then we create an invite for that employee

                :param request:
                email
                created_by -- user id who created invite
                employee -- id corresponding to employee

                :return:
                """

                if 'eligible_employees' in request.data:
                    eligible_employees = self.find_eligible_employees(request)
                    if eligible_employees != 'ALL':
                        employee_data = Employee.objects.filter(id__in=eligible_employees)
                    else:
                        employee_data = Employee.objects.filter(position_type=request.data['position_type'])
                        employee_data = employee_data.filter(organization_id__isnull=False)

                    if 'only_non_users' in request.data:
                        employee_data = employee_data.filter(user_id__isnull=True)

                    return Response(list(employee_data.values()), status=status.HTTP_201_CREATED)


                proceed = self.allowed_to_invite(request)

                if proceed:
                    successful = []
                    for invited in request.data:
                        invited['created_by'] = request.user.id
                        invited['sent_on'] = dt.datetime.utcnow()
                        serializer = CreateInviteSerializer(data=invited)
                        if serializer.is_valid():
                            serializer.save()
                            print(serializer.data)
                            invite = Invite.objects.get(id=serializer.data['id'])
                            invite.email_invite()
                            invite.sent_on = dt.datetime.utcnow()
                            invite.save()
                            employee = Employee.objects.get(id=invited['employee'])
                            employee.invited_on = dt.datetime.utcnow()
                            employee.save()
                            successful.append(serializer.data)
                            print("SUCCESS!")
                        else:
                            return Response(serializer.errors, status=status.HTTP_406_NOT_ACCEPTABLE)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response("ACCESS DENIED", status=status.HTTP_201_CREATED)


            queryset = Invite.objects.all()
            serializer_class = InviteSerializer

class HealthCheck(APIView):


    def get(self, request):
        user = request.user.username
        content = 'Congrats! It worked for: ' + str(user)
        return Response(content, status=status.HTTP_200_OK)

    def post(self, request):
        permission_classes = (IsAuthenticated,)
        content = {'message': 'POST, World!'}
        return Response(content)


from django.apps import apps



class ActionsMgmt(APIView):
    permission_classes = (IsAuthenticated,)

    serializer_class = None

    www_authenticate_realm = 'api'

    def get_eligible_models(self):
        allowed_models = ['EmployeeDashboard', 'EmployeeDashboardElement', 'Employee', 'Organization',
                          'EmployeeProfile', 'EmployeeProfileEntries', 'Profile']
        allowed_apps = ['accounts', 'dashboard']
        for app in allowed_apps:
            app_models = apps.get_app_config(app).get_models()
            eligible_models = []
            for model in app_models:
                if model.__name__ in allowed_models:
                    eligible_models.append(model)

        return eligible_models

    def deleteDetail(self):

        if len(UserActionDetails.objects.filter(parent_action=self.detail.parent_action)) < 2:
            self.detail.parent_action.delete()
            self.detail.delete()
        else:
            self.detail.delete()

    def undo(self):
        if self.detail.db_action_type == 'add':
            self.object.delete()
            self.deleteDetail()
        elif self.detail.db_action_type in ['remove_m2m', 'clear_m2m']:
            print(self.detail.field)
            getattr(self.object, str(self.detail.field)).add(self.detail.from_value) #TODO: work on this...
            self.object.save()
            self.deleteDetail()
        if self.detail.db_action_type in ['update']:
            print(self.detail.field)
            try:
                setattr(self.object, str(self.detail.field), self.detail.from_value) #TODO: work on this...
            except ValueError:
                setattr(self.object, str(self.detail.field) + '_id', self.detail.from_value) #TODO: work on this...

            self.object.save()
            self.deleteDetail()
        return "Success"

    def editObject(self):
        return self.object_values


    def post(self, request):
        data = request.data

        detail = UserActionDetails.objects.get(id=data['id'])
        self.detail = detail
        print(detail.db_model)
        eligible_models = self.get_eligible_models()

        for model in eligible_models:
            print(model.__name__, detail.db_model)
            if model.__name__ == detail.db_model:
                try:
                    self.object = model.objects.get(id = detail.db_model_id)
                    self.object_values = model.objects.filter(id = detail.db_model_id).values()[0]
                except ObjectDoesNotExist:
                    if data['change_type'] == 'undo' and self.detail.db_action_type == 'add':
                        self.deleteDetail()
                        return Response('Object doesnt exist', status=status.HTTP_200_OK)

        updateActions = {
            'undo': self.undo,
            'edit': self.editObject,
        }

        return Response(updateActions[data['change_type']](), status=status.HTTP_200_OK)

class EmployeeUpdate(APIView):
    queryset = Employee.objects.all()
    serializer_class = ShortEmployeeSerializer

    def get_object(self, id):
        emp = Employee.objects.get(id=id)
        return emp

    def update_email(self):
        employee = Employee.objects.get(user=self.request.user)
        tech_id_matches = self.request.data.get('tech_id').lower() == employee.login_id.lower()
        print(employee.login_id.lower(), self.request.data.get('tech_id').lower())

        our_name = re.sub(r'\W+', '', employee.last_name.lower())

        if self.request.data.get('last_name').lower()  in ['sr', 'jr', 'ii', 'iii']:
            return HttpResponse("You need to include the rest of the name. ")

        last_name_matches = self.request.data.get('last_name').lower() in our_name

        if last_name_matches and tech_id_matches:
            self.request.user.email = self.request.data.get('email')
            self.request.user.save()
            return HttpResponse(f"Success Email is now set to {self.request.data.get('email')}", status=status.HTTP_200_OK)
        else:
            if not last_name_matches:
                return HttpResponse(f"Last name provided doesnt match", status=status.HTTP_200_OK)
            elif not tech_id_matches:
                return HttpResponse(f"Tech ID doesnt match", status=status.HTTP_200_OK)
            else:
                return HttpResponse(f"something went wrong...", status=status.HTTP_400_BAD_REQUEST)


    def post(self, request):
        self.request = request
        if request.data.get('update_email'):
            return self.update_email()
        id = request.data.get('id')
        if not id:
            return Response("Need an employee id to update.")
        object = self.get_object(id)
        if 'active' in request.data:
            if request.data['active'] == False:
                if object.login_id is not None:
                    set_inactive=object.login_id+' - inactive'
                    object.login_id=set_inactive

        serializer = ShortEmployeeSerializer(object, data=request.data, partial=True)
        if serializer.is_valid():
            if 'unverified_email' in request.data:
                user = User.objects.get(id=object.user.id)
                user.email = request.data['unverified_email']
                user.save()

            if 'active' in request.data:
                if request.data['active']==False:

                    user = User.objects.get(id=object.user.id)
                    user.is_active = False
                    user.save()

            serializer.save()
            return Response(serializer.data)
        return Response("wrong parameters")

class ProfilePictureUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    www_authenticate_realm = 'api'


    def post(self, request, *args, **kwargs):
        print(request.data)

        queryset = Profile.objects.get(user=request.user)
        print(queryset)

        file_serializer = ProfilePictureSerializer(queryset, data=request.data, partial=True)

        if file_serializer.is_valid():
            file_serializer.save()

            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileBannerUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    www_authenticate_realm = 'api'


    def post(self, request, *args, **kwargs):
        print(request.data)

        queryset = Profile.objects.get(user=request.user)
        print(queryset)

        file_serializer = ProfileBannerSerializer(queryset, data=request.data, partial=True)

        if file_serializer.is_valid():
            file_serializer.save()

            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
