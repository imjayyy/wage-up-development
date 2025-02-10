from django.shortcuts import render
import sys

sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from .serializers import *
from accounts.models import *
from .models import *
from django.template.loader import render_to_string
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from django.core import serializers as django_serializers

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Q
from root.utilities import make_dynamodb_query, pprint
import requests
# from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import os
from django.conf import settings
from django.http import HttpResponse, Http404
from payments.models import WingSpanUserEmployee
from performance_points.models import PPCampaign
from django.core import files
from io import BytesIO
from dashboard.models import *
import itertools
from operator import itemgetter
from email.mime.image import MIMEImage
import base64
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.http import JsonResponse
from django.forms.models import model_to_dict
import requests
from fcm_django.models import FCMDevice
import json
from root.utilities import combine_dicts

from rest_framework.test import APIClient

from root.utilities import clean_val


LAMBDA_MESSAGING_ENDPOINT = "https://ve1mc0qia6.execute-api.us-east-1.amazonaws.com/dev/"
# LAMBDA_EXCEL_ENDPOINT = "https://1u95s2sc29.execute-api.us-east-1.amazonaws.com/dev/"
LAMBDA_PDF_ENDPOINT = "https://5iplynvm4e.execute-api.us-east-1.amazonaws.com/dev"
LAMBDA_EXCEL_ENDPOINT = "https://wy9j62tj9h.execute-api.us-east-1.amazonaws.com/dev/"
LAMBDA_EXCEL_FROM_REQUEST_ENDPOINT = "https://t7gxv0pkl5.execute-api.us-east-1.amazonaws.com/default/django_to_excel"
LAMBDA_EMAILS_ENDPOINT = "https://k8wspgj9xe.execute-api.us-east-1.amazonaws.com/default/wageupEmails-dev-emails"
LAMBDA_BOT_ENDPOINT = "https://wnts41svtf.execute-api.us-east-1.amazonaws.com/default/wageup_gpt3"

from django.template.defaultfilters import slugify

TESTING = False

# from performance_points.models import *
import requests
import boto3

from .serializers import *
from io import StringIO
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def upload_to_s3(url, key, base64File=None):
    if url is None and base64File is None:
        print("Please specify URL")
        return None
    if key is None:
        print("please specify key")
        return None
    session = boto3.Session()
    s3 = session.resource('s3')
    key = slugify(key.split('.')[0]) + '.' + key.split('.')[1]
    # print(key)
    bucket_name = 'wageup-media'
    bucket = s3.Bucket(bucket_name)

    if url:
        r = requests.get(url, stream=True)
        bucket.upload_fileobj(r.raw, key)
    elif base64File:
        obj = s3.Object(bucket_name, key)
        obj.put(Body=base64.b64decode(base64File.replace('data:image/png;base64,', '')))
        object_acl = s3.ObjectAcl(bucket_name, key)
        response = object_acl.put(ACL='public-read')

    objURL = f"https://wageup-media.s3.us-east-1.amazonaws.com/{key}"

    # print(objURL)

    return objURL


def send_push_notification(message):
    print('push notification')
    target_users = message.get('target_user_id')
    if type(target_users) != list:
        target_users = [int(i) for i in str(message.get('target_user_id')).split(',')]
    print(target_users)
    fcm_devices = FCMDevice.objects.filter(user__in=target_users)
    message = {
        'title': message.get('title', 'Notification'),
        'body': strip_tags(message.get('body', 'Notification Body')),
        'time_to_live': 604800,
        'click_action': message.get('click_url', 'https://aca-mtk.wageup.com'),
        # 'data': {
        #     'body': strip_tags(message.get('body', 'Notification Body')),
        #     'msg_type': message.get('message_type'),
        #     'from_user': 'WageUp Bot',
        # },
        'icon': 'https://wageup-media.s3.us-east-1.amazonaws.com/wageupLogo850.png',
    }
    fcm_devices.send_message(**message)


def send_email(email):
    '''

    :param email --> subject, from, to, attachmentLink, filename, filetype, message, image
    :return:
    '''
    lambda_request = {
        "header": email.get('subject'),
        "from": email.get('from', "messaging@wageup.com"),
        "to": email.get('to'),
        "goTo": email.get('goTo', None),
        "customGoTo": email.get('customGoTo', None),
        "getInTouch": email.get('getInTouch', None),
        "subject": email.get('subject'),
        "replyTo": email.get('replyTo'),

        "imageHighlights": [],
        "filesURL": [],
        "articles": [
            {
                "image": email.get('image', 'data.png'),
                "header": email.get('subject'),
                "text": email.get('message')
            }
        ]
    }

    if email.get('attachmentLink'):
        if email.get('filename'):
            lambda_request['imageHighlights'].append({
                "image": email.get('filename'),
                "header": email.get('subject')
            })
        lambda_request["filesURL"] = [
            {
                "url": email.get('attachmentLink'),
                "name": email.get('filename'),
                "type": email.get('filetype')
            }
        ]

    print('Email lambda request', lambda_request)

    resp = requests.post(LAMBDA_EMAILS_ENDPOINT, json=lambda_request)
    print(resp.json())


class PushNotificationView(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def get_push_notification_subscription(self):
        print(self.parameters.get('user'))
        out = list(PushNotificationSubscription.objects.filter(user=self.parameters.get('user')).values())
        # print(out)
        [o.update({'geography':
                       list(Organization.objects.filter(id=o['target_org_id']).values())[0]}) for o in out]
        return Response(out, status=status.HTTP_200_OK)

    def create_push_notification_subscription(self):
        obj = self.parameters
        # obj.update({'user': self.request.user})
        obj = PushNotificationSubscription.objects.create(**obj)

        return Response(PushNotificationSubscipritonSerializer(obj).data, status=status.HTTP_200_OK)

    def update_push_notification_subscription(self):
        message = PushNotificationSubscription.objects.get(id=self.parameters.get('originalAlertID'))
        for k, v in self.parameters.items():
            if k != 'originalAlertID':
                message.__setattr__(k, v)
        message.save()

        return Response("Success", status=status.HTTP_200_OK)

    def delete_push_notification_subscription(self):
        message = PushNotificationSubscription.objects.get(id=self.parameters.get('originalAlertID'))
        message.delete()
        return Response("Success", status=status.HTTP_200_OK)

    def send_pending_push_notifications(self):
        assert self.request.META.get(
            'HTTP_AUTHORIZATION') == 'D5kqmUmWHpEXb4zr', "Must include password in Authorization Header"
        self.new_messages = PushNotification.objects.filter(sent=False)

        for message in self.new_messages.values():
            params = json.loads(message['data'])
            message.update(params)
            send_push_notification(message)

        self.new_messages.update(sent=True)

        return Response("Success", status=status.HTTP_200_OK)

    def send_test_push_notification(self):
        assert self.request.META.get(
            'HTTP_AUTHORIZATION') == 'D5kqmUmWHpEXb4zr', "Must include password in Authorization Header"

        send_push_notification(self.parameters)
        return Response("Success", status=status.HTTP_200_OK)

    def post(self, request):
        self.request = request

        self.parameters = request.data.get('parameters')

        purpose = self.request.data.get('purpose', 'send_pending_push_notifications')

        self.purpose_router = {
            'send_pending_push_notifications': self.send_pending_push_notifications,
            'create_push_notification_subscription': self.create_push_notification_subscription,
            'update_push_notification_subscription': self.update_push_notification_subscription,
            'get_push_notification_subscription': self.get_push_notification_subscription,
            'delete_push_notification_subscription': self.delete_push_notification_subscription,
            'send_test_push_notification': self.send_test_push_notification,

        }

        return self.purpose_router[purpose]()


class Mail(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def send_mail(self):

        print('parameters', self.parameters)

        message = {
            'message': self.parameters.get('message'),
            'author': self.user.employee(),
            'subject': self.parameters.get('subject'),
            'priority': self.parameters.get('priority', 'Normal')
        }
        if self.parameters.get('parent'):
            message['parent'] = MailMessage.objects.get(id=self.parameters.get('parent'))
            print('parent', message['parent'])

        msg = MailMessage.objects.create(**message)

        # print(self.parameters.get('recipients'))
        recipients = [Employee.objects.get(id=int(r)) for r in self.parameters.get('recipients', [])]
        users = []
        for e in recipients:
            print(e)
            if e.user: users.append(e.user)

        if self.parameters.get('email', True):
            for user in users:
                print('emailing to', user, user.email)

                email = {
                    'to': user.email,
                    'subject': self.parameters.get('subject'),
                    'from': f'{self.user.first_name} {self.user.last_name}',
                    'replyTo': self.parameters.get('replyTo'),
                    'message': self.parameters.get('pureText', self.parameters.get('message')),
                    'image': 'message.png'
                }
                link = None
                if self.parameters.get('base64Img'):
                    link = upload_to_s3(self.parameters.get('imageURL'), 'chartimage.png',
                                        self.parameters.get('base64Img'))
                if link:
                    email['attachmentLink'] = link
                    email['filename'] = "chartimage.png"
                    email['filetype'] = "image"
                    email['image'] = "chartimage.png"
                print('sending email', email)
                send_email(email)

        if self.parameters.get('priority') == 'Urgent':
            push = {
                'title': self.parameters.get('subject'),
                'target_user_id': [u.id for u in users],
                'body': self.parameters.get('message'),
                'from_user': self.user
            }
            send_push_notification(push)

        msg.recipient.add(*recipients)

        msg.save()
        return True

    def get_inbox(self):
        emp = self.user.employee()
        vals = ['id', "message", "subject", "priority", "sent_on",
                "author_id", "author__display_name",
                "parent_id",
                "parent__message",
                "parent__author__display_name",
                "parent__sent_on",
                "recipient__display_name"
                ]

        inbox = MailMessage.objects.filter(recipient__in=[emp]).order_by('-sent_on').values(*vals)[:3]
        sent = MailMessage.objects.filter(author=emp).order_by('-sent_on').values(*vals)[:3]

        inbox = combine_dicts(inbox, 'id', concat_same_key="recipient__display_name", strict=False)
        sent = combine_dicts(sent, 'id', concat_same_key="recipient__display_name", strict=False)

        return {
            'inbox': inbox,
            'sent': sent
        }

    def post(self, request):
        self.user = request.user
        self.data = request.data
        self.purpose = self.data.get('purpose', 'get_inbox')
        self.parameters = self.data.get('parameters', {})

        make_dynamodb_query('createUserAction', {
            'input': {
                'user_id': request.user.id,
                'action': 'mail'
            }

        })

        purpose_router = {
            'send_mail': self.send_mail,
            'get_inbox': self.get_inbox,
        }

        output = purpose_router[self.purpose]()
        return Response(output, status=status.HTTP_200_OK)

    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'



class Chat(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def get_recent_logins(self):

        make_dynamodb_query('createUserAction', {
            'input': {
                'user_id': self.request.user.id,
                'action': 'chat'
            }

        })

        recent = dt.datetime.utcnow() - dt.timedelta(minutes=15)
        return Profile.objects.filter(last_activity__gte=recent).annotate(
            username=F('user__username'), last_login=F('user__last_login'), pic=F('photo_avatar'),
            name=F('employee__full_name'), organization=F('employee__organization__name'), emp_slug=F('employee__slug')
        ).values('username', 'last_login', 'last_activity', 'pic', 'organization', 'display_name', 'slug',
                 'employee_id').order_by('-last_activity')

    def send_test_notification(self):
        print('is send test notification being fired too?')
        parameters = self.parameters
        fcm_devices = FCMDevice.objects.filter(user__in=self.parameters.get('user_list'),
                                               name=self.parameters.get('device_group'))
        profile = Profile.objects.get(user_id=self.user.id)
        message = {
            'title': parameters.get('title', 'Notification'),
            'body': parameters.get('body', 'Notification Body'),
            'time_to_live': 604800,
            'click_action': parameters.get('click_url', 'https://rdb2.wageup.com'),
            'data': {
                'body': parameters.get('body', 'Notification Body'),
                'photo_avatar': profile.photo_avatar.url,
                'msg_type': 'huddle',
                'from_user': self.user.employee().full_name,
                'team': parameters.get('team_slug'),
                'viewable': parameters.get('viewable', 'private')
            },
            'icon': 'https://wageup-media.s3.us-east-1.amazonaws.com/wageupLogo850.png',
        }

        fcm_devices.send_message(**message)

    def send_notification(self):
        print('is send notification being fired?')
        parameters = self.parameters
        team_contest = PPTeamContest.objects.get(team__slug=parameters.get('team_slug'),
                                                 contest=parameters.get('contest', 1))
        huddle_recipients = TeamAssignments.objects.filter(team=team_contest).values_list('player__user', flat=True)
        print(huddle_recipients)
        huddle_subscriptions = Huddle.objects.get(team=team_contest).fans.all().values_list('user_id', flat=True)
        print(huddle_subscriptions)
        fcm_devices = FCMDevice.objects.filter(
            user__in=list(huddle_recipients) + list(huddle_subscriptions) + [self.user.id], name='rdb2')
        print('sending message', fcm_devices)
        profile = Profile.objects.get(user_id=self.user.id)
        message = {
            'title': parameters.get('title', 'Notification'),
            'body': parameters.get('body', 'Notification Body'),
            'time_to_live': 604800,
            'click_action': parameters.get('click_url', 'https://rdb2.wageup.com'),
            'data': {
                'body': parameters.get('body', 'Notification Body'),
                'photo_avatar': profile.photo_avatar.url,
                'msg_type': 'huddle',
                'from_user': self.user.employee().full_name,
                'team': parameters.get('team_slug'),
                'viewable': parameters.get('viewable', 'private')
            },
            'icon': 'https://wageup-media.s3.us-east-1.amazonaws.com/wageupLogo850.png',
        }
        fcm_devices.send_message(**message)

        team = PPTeamContest.objects.get(team__slug=self.parameters.get('team_slug', 'mountain-marvelers'),
                                         contest=self.parameters.get('contest', 1))
        huddle = Huddle.objects.get(team=team)
        message = HuddleMessages.objects.create(
            huddle=huddle,
            message=parameters.get('body', 'Notification Body'),
            from_user=self.user,
            time=parameters.get('time'),
            private=parameters.get('viewable', 'private') == 'private'
        )

        return {'message_id': message.id}

    def chat_subscribe(self):
        if self.parameters.get('type') == 'fandom':
            ppTeamContest = PPTeamContest.objects.get(contest=self.parameters.get('contest', 1),
                                                      team__slug=self.parameters.get('team_slug'))
            huddle = Huddle.objects.get(team=ppTeamContest)
            huddle.fans.add(self.user.employee())
            huddle.save()

        return 'Successfully Subscribed'

    def get_huddle_messages(self):

        team = PPTeamContest.objects.get(team__slug=self.parameters.get('team_slug'),
                                         contest=self.parameters.get('contest', 1))
        huddle = Huddle.objects.get(team=team)
        # print(huddle)
        user_in_team = TeamAssignments.objects.filter(team=team, player=self.user.employee()).exists()
        messages = HuddleMessages.objects.filter(huddle=huddle)
        if not user_in_team:
            messages = messages.filter(private=False)
        return messages.annotate(from_user_name=F('from_user__employee__full_name'),
                                 timestamp=F('time'),
                                 photo_avatar=F('from_user__profile__photo_avatar')) \
            .values('from_user_name', 'message', 'timestamp', 'photo_avatar', 'private')

    def notify_new_chat(self):
        testing = False
        message = self.parameters.get('message')
        recipient = message.get('chatMessageRecipientId')
        recipient = Employee.objects.get(id=recipient)
        fcm_devices = FCMDevice.objects.filter(user=recipient.user).filter(name__isnull=False)
        me = self.user.employee()
        profile_pic = Profile.objects.get(user=self.user).photo_avatar

        rdb2_click_url = f"http://localhost:8081?openChat={me.id}" if testing else f'https://rdb2.wageup.com?openChat={me.id}'
        mtk_click_url = f"http://localhost:8080?openChat={me.id}" if testing else f'https://aca-mtk.wageup.com/?openChat={me.id}'

        rdb2_message = {
            'data': {
                'title': f'{me.display_name} wants to talk to you.',
                'body': message.get('message'),
                'msg_type': 'chat',
                'redirect': rdb2_click_url,
                'icon': f'https://wageup-media.s3.us-east-1.amazonaws.com/{profile_pic}' if profile_pic is not None else 'https://wageup-media.s3.us-east-1.amazonaws.com/wageupLogo850.png',
            },

        }

        mtk_message = {
            'data': {
                'title': f'{me.display_name} wants to talk to you.',
                'body': message.get('message'),
                'msg_type': 'chat',
                'redirect': mtk_click_url,
                'icon': f'https://wageup-media.s3.us-east-1.amazonaws.com/{profile_pic}' if profile_pic is not None else 'https://wageup-media.s3.us-east-1.amazonaws.com/wageupLogo850.png',
            },

        }

        fcm_devices.filter(name='rdb2').send_message(**rdb2_message)
        fcm_devices.filter(name='mtk').send_message(**mtk_message)
        return {}

    def post(self, request):
        self.request = request
        self.user = request.user
        self.data = request.data
        self.purpose = self.data.get('purpose', 'default')
        self.parameters = self.data.get('parameters', {})

        purpose_router = {
            'send_notification': self.send_notification,
            'get_huddle_messages': self.get_huddle_messages,
            'chat_subscribe': self.chat_subscribe,
            'send_test_notification': self.send_test_notification,
            'get_recent_logins': self.get_recent_logins,
            'notify_new_chat': self.notify_new_chat,
        }

        output = purpose_router[self.purpose]()
        return Response(output, status=status.HTTP_200_OK)


@csrf_exempt
def unsubscribe(request):
    print(request.GET)
    if request.GET.get('emailSubscriptionID'):
        try:
            if not request.GET.get('userID'):
                return HttpResponse("<h1>We Couldnt find the email. Please contact support at help@wageup.com</h1>")
            emailObject = SubscriptionEmail.objects.get(id=request.GET.get('emailSubscriptionID'))
            emailObject.recipients.remove(User.objects.get(request.GET.get('userID')))
            emailObject.save()
        except ObjectDoesNotExist:
            return HttpResponse("<h1>We Couldnt find the email. Please contact support at help@wageup.com</h1>")
        return HttpResponse("<h1>Successfully removed subscription!</h1>")
    else:
        try:
            emailObject = SimpleEmailSubscriptions.objects.get(id=request.GET.get('id'))
        except ObjectDoesNotExist:
            return HttpResponse("<h1>Successfully removed subscription!</h1>")

        emailObject.delete()
        return HttpResponse("<h1>Successfully removed subscription!</h1>")


class Messaging(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def pretty(self, d, indent=0):
        for key, value in d.items():
            print('\t' * indent + str(key))
            if isinstance(value, dict):
                self.pretty(value, indent + 1)
            else:
                print('\t' * (indent + 1) + str(value))

    def subscribe_to_table(self, parameters):
        print(parameters)
        save = parameters.get('save', True)
        request = parameters.get('request')
        request['password'] = "C4QwE4hvemtmhLXS"
        user = User.objects.get(id=parameters.get('to'))
        obj_id = parameters.get('id')
        if save:
            if parameters.get('period') == 'add_to':
                obj = SimpleEmailSubscriptions.objects.filter(subject=parameters.get('subject'), to=user).last()
                current_request = json.loads(obj.request)
                current_request['sheets'] = current_request['sheets'] + request['sheets']
                obj.request = json.dumps(current_request)
                request = current_request
                obj.save()
            else:
                obj, created = SimpleEmailSubscriptions.objects.get_or_create(
                    interval=parameters.get('period'),
                    subject=parameters.get('subject'),
                    to=user,
                    message=parameters.get('message'),
                    request=json.dumps(request),
                    filename=parameters.get('filename')
                )
            obj_id = obj.id
        return self.send_simple_email(parameters.get('subject'),
                                      user.email,
                                      parameters.get('message'),
                                      request,
                                      parameters.get('filename'),
                                      obj_id
                                      )



    def send_number_highlights_email(self, subject, to, message, data, emailID=None, conditionalFormatting={}):
        lambda_request = {
            "header": subject,
            "from": "subscriptions@wageup.com",
            "to": to.get('email'),
            "userID": to.get('userID'),
            "emailSubscriptionID": emailID,
            "subject": subject,
            "filesURL": [],
            "articles": [
                {
                    "image": "data.png",
                    "header": subject,
                    "text": message
                }
            ]
        }
        thresholds = {}
        skip = False
        for d in data:
            reverse = False
            val = d.get('series')[0]
            d_name = d.get('name').lower().replace('_', ' ')
            # print(d_name, val)

            if conditionalFormatting.get('type') == 'manual':
                thresholds = next((x for x in conditionalFormatting.get('metrics',[])
                                   if x.get('info').get('element').lower() == d_name
                                   or x.get('info').get('formatted_name').lower() == d_name), {})

                skip = thresholds is None or thresholds.get('range') is None
                if not skip:
                    thresholds['top'] = thresholds.get('range').get('max') \
                        if not reverse else thresholds.get('range').get('min')
                    thresholds['bottom'] = thresholds.get('range').get('min') \
                        if not reverse else thresholds.get('range').get('max')

                    if thresholds.get('info').get('number_type') == 'percentage':
                        thresholds['top'] = thresholds['top'] / 100
                        thresholds['bottom'] = thresholds['bottom'] / 100
                # print('reverse', reverse, 'thresholds', thresholds, thresholds.get('info').get('number_type'))
            if not reverse:
                if val >= thresholds.get('top', d.get('avg')):
                    level = {"img": 'good.png', 'color': 'green'}
                elif val >= thresholds.get('bottom',d.get('avg')) - d.get('std') :
                    level = {"img": 'okay.png', 'color': 'orange'}
                else:
                    level = {"img": 'bad.png', 'color': 'red'}
            else:
                if val <= thresholds.get('top', d.get('avg')):
                    level = {"img": 'good.png', 'color': 'green'}
                elif val <= thresholds.get('bottom',d.get('avg')) - d.get('std') :
                    level = {"img": 'okay.png', 'color': 'orange'}
                else:
                    level = {"img": 'bad.png', 'color': 'red'}

            if skip:
                level = {"img": 'data.png', 'color': 'black'}

            lambda_request['articles'].append(
                {
                    "image": level['img'],
                    "header": clean_val(d.get('name'), 'string'),
                    "text": clean_val(val, 'evaluate', d.get('name')),
                    "fontColor": level['color'],
                    "fontSize": "40px"
                }
            )

        print(lambda_request)

        resp = requests.post(LAMBDA_EMAILS_ENDPOINT, json=lambda_request)
        print(resp.json())
        return resp




    def send_excel_email(self, subject, to, message, dataURL, emailID=None):

        lambda_request = {
            "header": subject,
            "from": "subscriptions@wageup.com",
            "emailSubscriptionID": emailID,
            "to": to.get('email'),
            "userID": to.get('userID'),
            "subject": subject,
            "filesURL": [{
                "url": dataURL,
                "name": f"subscription_data_{dt.date.today().strftime('%Y-%m-%d')}.xlsx",
                "type": "excel"
                }],
            "articles": [
                {
                    "image": "data.png",
                    "header": subject,
                    "text": message
                }
            ]
        }

        resp = requests.post(LAMBDA_EMAILS_ENDPOINT, json=lambda_request)
        print(resp.json())
        return resp

    def send_simple_email(self, subject, to, message, subscription_data, filename, id):

        s3_link = requests.post(LAMBDA_EXCEL_FROM_REQUEST_ENDPOINT, json=subscription_data)
        attachmentLink = s3_link.json()['link']
        print(attachmentLink)

        lambda_request = {
            "header": subject,
            "from": "subscriptions@wageup.com",
            "to": to,
            "id": id,
            "subject": subject,
            "filesURL": [
                {
                    "url": attachmentLink,
                    "name": filename,
                    "type": "excel"
                }
            ],

            "articles": [
                {
                    "image": "data.png",
                    "header": "Your Data is Attached",
                    "text": message
                }
            ]
        }

        print(lambda_request)

        resp = requests.post(LAMBDA_EMAILS_ENDPOINT, json=lambda_request)
        print(resp)
        return {"Success": True}

        # html_content = requests.post(LAMBDA_MESSAGING_ENDPOINT, json={"data": [{'intro_text': message},
        #                                                                        {'text': "To Unsubscribe from this email, click the Unsubscribe Button",
        #                                                                         'button' : {"link": f"https://aca-dashboard-api.wageup.com/messaging/unsubscribe?id={id}",
        #                                                                                     "text": "Unsubscribe"}}]})
        # # print(html_content.json())
        # html_content = html_content.json()['body']['html'].replace('/\\"/g', '"')
        # mail = EmailMultiAlternatives(subject, strip_tags(html_content), 'subscription@wageup.com', [to,])
        # mail.mixed_subtype = 'related'
        # mail.attach_alternative(html_content, "text/html")
        #
        # with open(settings.BASE_DIR + '/media/logo.png', 'rb') as logo:
        #     img = MIMEImage(logo.read(), 'png')
        #     img.add_header('Content-Id', '<logo.png>')
        #     img.add_header("Content-Disposition", "inline", filename="logo.png")
        #     mail.attach(img)
        #

        # attachment = BytesIO(resp.content)
        # mail.attach(filename, attachment.getvalue(), 'application/ms-excel')
        # mail.send()
        # print("sending to", to)
        return {"Success": True}

    def send_email(self, html_message):
        mail_subject = self.mail_subject
        plain_message = strip_tags(html_message)
        mail = EmailMultiAlternatives(mail_subject, plain_message, self.from_email, self.email, cc=self.email)
        mail.mixed_subtype = 'related'
        mail.attach_alternative(html_message, "text/html")
        for x in self.xls_attachments:
            mail.attach(x['title'] + ".xlsx", x['attachment'].getvalue(), 'application/ms-excel')
        for p in self.pdf_attachments:
            mail.attach(p['title'] + ".pdf", p['attachment'].getvalue(), 'application/pdf')
        # logo
        with open(settings.BASE_DIR + '/media/logo.png', 'rb') as logo:
            img = MIMEImage(logo.read(), 'png')
            img.add_header('Content-Id', '<logo.png>')
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            mail.attach(img)
        for fname, i in self.img.items():
            img = MIMEImage(base64.b64decode(i[i.find(",") + 1:].encode('ascii')), 'png')
            img.add_header('Content-Id', '<' + fname + '>')
            img.add_header("Content-Disposition", "inline", filename=fname)
            mail.attach(img)
        mail.send()
        log = EmailLogs(date_delivered=dt.datetime.now(), sent_to=self.email, parameters=str(self.parameters),
                        generated_by=self.user)
        if 'newSurveys' in self.parameters or 'lastEmailSurveys' in self.parameters:
            log.type = 'newSurveys'
        log.save()

    def sentEmailHistory(self, parameters):
        return EmailLogs.objects.filter(generated_by=self.user).values('sent_to', 'date_delivered')

    def generate_email(self, parameters):
        # print(parameters['lambda_data'])
        self.parameters = parameters
        bad_data = []
        for el in range(len(parameters['lambda_data']['data'])):
            # print(parameters['lambda_data']['data'][el])
            if parameters['lambda_data']['data'][el] is None:
                bad_data.append(el)
                continue
            if 'svg' in parameters['lambda_data']['data'][el]:
                parameters['lambda_data']['data'][el]['svg'] = parameters['lambda_data']['data'][el]['svg'].replace('"',
                                                                                                                    "'")
                parameters['lambda_data']['data'][el]['legend'] = [x.replace('"', "'") for x in
                                                                   parameters['lambda_data']['data'][el]['legend']]
                # print(parameters['lambda_data']['data'][el]['legend'], "LEGEND")
        if len(bad_data) > 0:
            for el in bad_data:
                # print(el)
                # print(parameters['lambda_data']['data'][el])
                del parameters['lambda_data']['data'][el]

        # insert into all emails this text:
        db_updated = DashboardUpdateHistory.objects.latest('date_updated').date_updated.strftime("%b %d")
        intro_text = """
        <p>This email was created by you or someone you know to update you on performance for ACA Roadside events. 
        If you wish to unsubscribe from this email please go to your profile on the Wageup site. </p><p>The data was updated on <b>%s</b></p>
        """ % db_updated

        print(intro_text)
        parameters['lambda_data']['data'].insert(0, {'intro_text': intro_text})
        print(parameters['lambda_data'])

        if TESTING:
            with open('templates/mjml_html_output.json') as f:
                lambda_response = json.load(f)
        else:
            lambda_response = requests.post(LAMBDA_MESSAGING_ENDPOINT, json=parameters['lambda_data'])
            # print(lambda_response.json())
            lambda_response = lambda_response.json()
        print(lambda_response, "RESPONSE FROM LAMBDA")
        html = lambda_response['body']['html'].replace('/\\"/g', '"')
        self.img = lambda_response['body']['imgs']
        # print(self.img)
        self.mail_subject = parameters['mail_subject']
        self.table_data = []
        self.xls_attachments = []
        self.pdf_attachments = []

        for elem in parameters['lambda_data']['data']:
            # print(type(elem))
            if type(elem) is str:
                print(elem, "converting to json")
                elem = json.loads(elem)
            if 'table' in elem:
                self.table_data.append(elem['table'])

        if 'attachments' in parameters:
            for table in self.table_data:
                filters = table['filters']
                filter_text = ""
                for k, v in filters.items():
                    filter_text += v + '_'
                print(filters, "FILTERS")
                if 'excel' in parameters['attachments']:
                    excel_rows = []
                    for i, row in enumerate(table['displayed_data']):
                        if i == 0 and 'djangoLabel' in row['data'][0]:
                            continue
                        # print(row)
                        excel_row = {}
                        for cell in row['data']:
                            if 'djangoLabel' in cell:
                                excel_row[cell['djangoLabel'].upper()] = cell['value']
                            elif 'clean_time_label' in cell:
                                excel_row[cell['clean_time_label'].upper()] = cell['value']
                            else:
                                excel_row[cell['label'].upper()] = cell['value']
                        excel_rows.append(excel_row)

                    print(excel_rows, "EXCEL ROWS")
                    req = {'name': 'email_doc.xlsx', 'data': excel_rows}
                    excel_response = requests.post(LAMBDA_EXCEL_ENDPOINT, json=req)
                    print(excel_response.content)
                    xls_link = json.loads(excel_response.content)['body']
                    # print("EXCEL RESPONSE: ", xls_link)
                    resp = requests.get(xls_link)
                    xls_attachment = BytesIO()
                    xls_attachment.write(resp.content)
                    self.xls_attachments.append(
                        {
                            "attachment": xls_attachment,
                            "title": table['title'] + " " + filter_text[:-1]
                        }

                    )
            if 'pdf' in parameters['attachments']:
                req = self.format_pdf_request()
                # print(req)fself.
                for r in req:
                    pdf_response = requests.post(LAMBDA_PDF_ENDPOINT, json=r['request'])
                    # print(pdf_response)
                    pdf_link = pdf_response.json()['body']
                    resp = requests.get(pdf_link)
                    pdf = BytesIO(resp.content)
                    self.pdf_attachments.append({'attachment': pdf, 'title': r['title']})

        if 'pdfRequest' in parameters:
            pdf_response = requests.post(LAMBDA_PDF_ENDPOINT, json=parameters['pdfRequest'])
            pdf_link = pdf_response.json()['body']
            resp = requests.get(pdf_link)
            pdf = BytesIO(resp.content)
            self.pdf_attachments.append({'attachment': pdf, 'title': parameters['mail_subject']})

        self.send_email(html)
        return html

    def post(self, request):

        self.data = request.data
        self.parameters = self.data['parameters']
        print("PARAMETERS", self.parameters)
        if request.user:
            self.user = request.user
            self.user_id = self.user.id
            # print(self.user)

        if 'send_to' in self.parameters:
            self.email = list(set([self.user.email] + [d['value'] for d in self.parameters['send_to']]))
        else:
            self.email = self.user.email

        try:
            from_user = User.objects.get(id=self.parameters['send_from'])
            self.from_email = from_user.username + '@wageup.com'
        except Exception as e:
            self.from_email = "messaging@wageup.com"
            print("something went wrong: ", e)

        print(self.email)

        self.purpose_router = {
            'updateEmailText': self.updateEmailText,
            'subscribe_to_table': self.subscribe_to_table,
            'sentEmailHistory': self.sentEmailHistory,
            'pause_email': self.pause_email,
            'restart_email': self.restart_email,
            'generate_email': self.generate_email,
            'create_trigger_email': self.create_trigger_email,
            'create_schedule_email': self.create_schedule_email,
            'get_user_emails': self.get_user_emails,
            'identify_trigger_emails': self.identify_trigger_emails,
            'update_email_data': self.update_email_data,
            'delete_schedule_trigger_email': self.delete_schedule_trigger_email,
            'get_announcements': self.get_announcements,
            'get_loading_data': self.get_loading_data,
            'remove_recipient': self.remove_recipient,
            'add_recipients': self.add_recipients,
            'read_announcement': self.read_announcement,
            'send_dashboard_data_element_email' : self.send_dashboard_data_element_email,
            'create_subscription_email': self.create_subscription_email,
            'get_subscription_emails': self.get_subscription_emails,
            'send_subscription_email': self.send_subscription_email,
            'update_enabled_subscription_email': self.update_enabled_subscription_email,
            'delete_subscription_email': self.delete_subscription_email,
            'get_mtk_messages': self.get_mtk_messages
        }

        output = self.purpose_router[self.data['purpose']](self.data['parameters'])

        return Response(output, status=status.HTTP_200_OK)

    def get_mtk_messages(self, parameters):
        """
        Fetch active MTK messages that fall within the start and end dates.
        Include 'w9' messages if the employee needs a W9.
        Include 'registration' messages only if the employee is eligible for the campaign.
        Show messages with the 'registered_only' flag only if the employee is registered to the associated campaign.
        """
        employee = self.user.employee()
        today = dt.datetime.today()

        # Check if the employee needs a W9
        wingspan_user_employee = WingSpanUserEmployee.objects.filter(employee=employee).first()
        employee_needs_w9 = wingspan_user_employee.need_w9() if wingspan_user_employee else False

        # Filter campaigns the employee is registered for
        registered_campaigns = PPCampaign.objects.filter(
            ppcampaignregistration__employee=employee
        )

        # Base message filter (active messages within date range)
        messages = MTKMessage.objects.filter(
            active=True,
            start_date__lte=today,
            end_date__gte=today,
        )

        # Step 1: Handle 'registration' messages for campaigns

        registration_messages = messages.filter(
            type='registration',
            pp_campaign__isnull=False,  # Only messages tied to campaigns
            pp_campaign__geography_eligiblity=employee.organization
        ).exclude(
            pp_campaign__ppcampaignregistration__employee=employee
        )

        print("REGISTRATION MESSAGES", registration_messages)


        # Step 2: Handle all other messages
        other_messages = messages.exclude(type='registration')
        print("OTHER MESSAGES", other_messages)
        # Step 3: Combine the two sets of messages
        messages = registration_messages | other_messages

        # Step 4: Apply 'registered_only' filter
        messages = messages.filter(
            Q(registered_only=False) | Q(pp_campaign__in=registered_campaigns)
        )

        # Step 5: Include or exclude 'w9' messages based on W9 need
        if not employee_needs_w9:
            messages = messages.exclude(type='w9')

        # Order messages by hierarchy and serialize
        messages = messages.order_by('hierarchy')
        serializer = MTKMessageSerializer(messages, many=True)
        return serializer.data

    def get_loading_data(self, parameters):
        bearerToken = "AAAAAAAAAAAAAAAAAAAAABUElAEAAAAAIb9%2BaeetverG%2Bb2Gqh2JbdSM9Fk%3D8xdwYM8HVC6E2RGaFuwPFaQZtBqvQdo95F1bsm3YnBFyred8aY"
        allTweets = []
        following = ['15690243']
        # following = ['15690243', '18622756', '2891202783', '454313925', '222107569', '172440908', '97036677',
        #              '1067797863042818049']
        for f in following:
            url = f"https://api.twitter.com/2/users/{f}/tweets?tweet.fields=text,created_at&exclude=replies&user.fields=username&expansions=author_id,attachments.media_keys&media.fields=url,height,type"

            resp = requests.get(url, headers={
                "Authorization": f"Bearer {bearerToken}"
            }).json()
            print(resp)
            try:
                author = resp['includes']['users'][0]['name']
            except:
                author = " - "
            media = resp['includes'].get('media', [])
            # print('media', media)
            media = {m['media_key']: m for m in media}
            # print('media', media)

            tweets = [{"text": t['text'], "created_at": t['created_at'], "author": author,
                       "media": media.get(t.get('attachments', {}).get('media_keys', ['NONE'])[0])} for t in
                      resp['data']]
            allTweets = allTweets + tweets

        return allTweets

    def updateEmailText(self, parameters):
        email = EmailData.objects.get(id=parameters['id'])
        if parameters['type'] == 'subject':
            email.subject = parameters['value']
        elif parameters['type'] == 'body':
            lambda_data = json.loads(email.lambdaData)
            for i in range(len(lambda_data)):
                if 'text' in lambda_data[i]:
                    text = lambda_data[i]
                    print(text)
                    try:
                        text_id = lambda_data[i + 1]['id']
                    except:
                        print('couldnt find next element to assign id')
                        text_id = None
                    parameters['value'] = parameters['value'].replace('\u2022', '<br>\u2022')
                    lambda_data[i] = {'text': parameters['value'], 'id': text_id}
                    print(lambda_data[i])
                    break
            email.lambdaData = json.dumps(lambda_data)
        email.save()
        return EmailDataSerializer(email).data

    def format_pdf_request(self):
        pdf_requests = []
        for table in self.table_data:
            filters = table['filters']
            filter_text = ""
            for k, v in filters.items():
                filter_text += v + '_'
            print(filters, "FILTERS")

            col_count = len(table['displayed_data'][0]['data'])

            request = {}
            request['header'] = {
                "margin": 10,
                "columns": [
                    {
                        "margin": [
                            10,
                            0,
                            0,
                            0
                        ],
                        "text": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "margin": [
                            10,
                            0,
                            0,
                            0
                        ],
                        "text": table['title'] + '_' + filter_text[:-1]
                    }
                ]
            }
            request["pageOrientation"] = "landscape"
            request['content'] = []
            docDefinition = {}
            docDefinition["layout"] = "lightHorizontalLines"
            docDefinition['table'] = {}
            docDefinition['table']['headerRows'] = 1
            docDefinition['table']['widths'] = []
            docDefinition['table']['body'] = []
            for col in range(col_count):
                docDefinition['table']['widths'].append(str(100 / col_count) + "%")
            r = 0
            for row in table['displayed_data']:
                row_data = []
                r += 1
                for cell in row['data']:
                    if r == 1:
                        row_data.append(cell['label'])
                    else:
                        row_data.append(cell['value'])
                docDefinition['table']['body'].append(row_data)
            request['content'].append(docDefinition)
            print(self.pretty(request))
            pdf_requests.append({'request': request, 'title': table['title'] + '_' + filter_text[:-1]})
        return pdf_requests

    #deprecated
    def create_email(self, parameters):
        pdf_attachment = 'pdf' in parameters.get('email_data').get('attachments', [])
        xls_attachment = 'excel' in parameters.get('email_data').get('attachments', [])
        emailObject = EmailData.objects.create(requestData=parameters['email_data']['request'],
                                               subject=parameters['email_data']['subject'],
                                               xls_attachment=xls_attachment,
                                               pdf_attachment=pdf_attachment,
                                               # lambdaSVGData=parameters['email_data']['lambdaSVGData'],
                                               # lambdaTableData=parameters['email_data']['lambdaTableData'],
                                               lambdaData=parameters['email_data']['lambdaData'])
        emailObject.recipients.add(self.user)
        emailObject.author = self.user
        emailObject.save()
        return EmailDataSerializer(emailObject).data

    def get_subscription_emails(self, parameters):
        myEmails = SubscriptionEmail.objects.filter(author=self.user)
        data = EmailSubscriptionSerializer(myEmails, many=True).data
        return data

    def create_subscription_email(self, parameters):
        triggers = []
        schedules = []
        for t in parameters.get('triggers', []):
            triggers.append(TriggerMessages.objects.create(**t))
        for s in parameters.get('schedule', []):
            schedules.append(ScheduledMessages.objects.create(**s))
        emailData = parameters.get('email', {})
        if parameters.get('conditionalFormatting'):
            emailData.update({"conditional_formatting": parameters.get('conditionalFormatting', {})})

        email = SubscriptionEmail.objects.create(**emailData)

        email.recipients.add(self.user.id)
        for r in parameters.get('recipients'):
            email.recipients.add(r.get('id'))

        for t in triggers:
            email.triggers.add(t)
        for s in schedules:
            email.schedules.add(s)

        email.save()

    def update_enabled_subscription_email(self, parameters):
        email = SubscriptionEmail.objects.get(id=parameters.get('id'))
        email.disabled = not parameters.get('enabled')
        email.save()
        return {"enabled": not email.disabled}

    def delete_subscription_email(self, parameters):
        email = SubscriptionEmail.objects.get(id=parameters.get('id'))
        email.delete()

    def send_subscription_email(self, parameters):
        email = SubscriptionEmail.objects.get(id=parameters.get('email_id'))

        params = {
            "endpoint": email.endpoint,
            "request": email.request,
            "email": {
                "subject": email.subject,
                "body": email.body,
            },
            "emailID": email.id,
            "recipients": [{"email": x.get('fields').get('email'), "userID": x.get('pk')} for x in json.loads(django_serializers.serialize('json', email.recipients.all()))],
            "conditionalFormatting": email.conditional_formatting

        }
        print(json.loads(django_serializers.serialize('json', email.recipients.all()))[0])
        print("PARAMS")
        print(params.get('recipients'))

        self.send_dashboard_data_element_email(params)

    def remove_recipient(self, parameters):
        email = EmailData.objects.get(id=parameters['email_id'])
        recipient = User.objects.get(id=parameters['recipient_id'])
        email.recipients.remove(recipient)
        email.save()
        return EmailDataSerializer(email).data

    def pause_email(self, parameters):
        email = EmailData.objects.get(id=parameters['email_id'])
        email.disabled = True
        email.save()
        return EmailDataSerializer(email).data

    def restart_email(self, parameters):
        email = EmailData.objects.get(id=parameters['email_id'])
        email.disabled = False
        email.save()
        return EmailDataSerializer(email).data

    def add_recipients(self, parameters):
        email = EmailData.objects.get(id=parameters['email_id'])
        for recipient in parameters['new_recipients']:
            recipient = Employee.objects.get(id=recipient).user
            email.recipients.add(recipient)
            email.save()
        return EmailDataSerializer(email).data

    def update_email_data(self, parameters):
        print("UPDATING EMAIL DATA", parameters['email_data']['subject'])
        emailObject = EmailData.objects.get(id=parameters['email_fk'])
        pdf_attachment = 'pdf' in parameters['email_data']['attachments']
        xls_attachment = 'excel' in parameters['email_data']['attachments']
        emailObject.requestData = parameters['email_data']['request'],
        emailObject.subject = parameters['email_data']['subject'],
        emailObject.subject = emailObject.subject[0]
        emailObject.requestData = emailObject.requestData[0]
        print(emailObject.requestData)
        emailObject.xls_attachment = xls_attachment
        emailObject.pdf_attachment = pdf_attachment
        if 'lambdaData' in parameters['email_data']:
            emailObject.lambdaData = parameters['email_data']['lambdaData']
        if 'lambdaSVGData' in parameters['email_data']:
            emailObject.lambdaSVGData = parameters['email_data']['lambdaSVGData']
        if 'lambdaTableData' in parameters['email_data']:
            emailObject.lambdaTableData = parameters['email_data']['lambdaTableData']
        emailObject.save()
        return EmailDataSerializer(emailObject).data

    def create_trigger_email(self, parameters):
        print("CREATING TRIGGER EMAIL")
        print(parameters)
        if 'email_fk' in parameters:
            emailObject = EmailData.objects.get(id=parameters['email_fk']).id
        else:
            emailObject = self.create_email(parameters)['id']

        print(emailObject)

        for req_criteria in parameters['criteria']:
            if type(req_criteria) == list:
                logical_operator = 'conjunction'
            else:
                req_criteria = [req_criteria]
                logical_operator = 'disjunction'
            print(req_criteria)
            for i in range(len(req_criteria)):
                criteria = req_criteria[i]
                print(criteria)
                if i == 0:
                    prev_key = None

                for v in ['employee_id', 'organization_id', 'sc_dt', 'time_relation']:
                    if v not in criteria:
                        criteria[v] = None

                new_obj = TriggerMessages.objects.create(metric=criteria['metric'],
                                                         comparison_type=criteria["comparison_type"],
                                                         value=criteria['value'],
                                                         email_data_id=emailObject,
                                                         logical_operator=logical_operator,
                                                         employee_id=criteria['employee_id'],
                                                         organization_id=criteria['organization_id'],
                                                         sc_dt=criteria['sc_dt'],
                                                         time_relation=criteria['time_relation'],
                                                         time_type=criteria['time_relation'],
                                                         conjoined_trigger_id=prev_key)
                prev_key = new_obj.id

        out = TriggerMessages.objects.filter(email_data=emailObject).values()

        return out

    def create_schedule_email(self, parameters):
        print(parameters)
        if 'email_fk' in parameters:
            emailObject = EmailData.objects.get(id=parameters['email_fk']).id
        else:
            emailObject = self.create_email(parameters)['id']

        for criteria in parameters['schedule']:
            ScheduledMessages.objects.create(interval=criteria['interval'],
                                             starting=criteria['starting'],
                                             ending=criteria['ending'],
                                             email_data_id=emailObject,
                                             )

        out = ScheduledMessages.objects.filter(email_data=emailObject).values()

        return out

    def delete_schedule_trigger_email(self, parameters):
        print(parameters)
        if parameters['type'] == 'schedule':
            s = ScheduledMessages.objects.get(id=parameters['id'])
            email_fk = int(s.email_data.id)
            s.delete()
            updatedScheduledMessages = ScheduledMessages.objects.filter(email_data_id=email_fk)
            data = ScheduleSerializer(updatedScheduledMessages, many=True).data
        if parameters['type'] == 'trigger':
            t = TriggerMessages.objects.get(id=parameters['id'])
            email_fk = int(t.email_data.id)
            t.delete()
            updatedTriggerMessages = TriggerMessages.objects.filter(email_data_id=email_fk)
            data = TriggerSerializer(updatedTriggerMessages, many=True).data

        return data

    def get_user_emails(self, parameters):
        print(parameters)
        if 'author_only' in parameters:
            email_obj = EmailData.objects.filter(author=self.user)
        elif 'recipient_only' in parameters:
            email_obj = EmailData.objects.filter(recipients__in=[self.user]).exclude(author=self.user)
        else:
            email_obj = EmailData.objects.filter(recipients__in=[self.user])
        print(email_obj)
        return EmailDataSerializer(email_obj, many=True).data

    def identify_trigger_emails(self, parameters):
        trigger_objects = list(TriggerMessages.objects.all().values())
        time_relation_dict = {
            "yesterday": dt.date.today() - dt.timedelta(days=1)
        }
        for email, criteria in itertools.groupby(trigger_objects, key=itemgetter('email_data_id')):
            print(email)
            for c in criteria:
                print(c)

    def get_announcements(self, parameters):
        print("GETTING ANNOUNCEMENTS...")
        now = dt.datetime.now()
        # TODO: position type filter
        new_announcement = Announcements.objects.filter(starts__lte=now, ends__gte=now,
                                                        position_types__in=[self.user.employee().position_type,
                                                                            'everyone']).exclude(
            read__in=[self.user.id])
        new_announcement = new_announcement.exclude(platform='App')
        print(new_announcement)
        if new_announcement:
            new_announcement = new_announcement[0]
        else:
            return False
        new_announcement.read.add(self.user)
        new_announcement.save()
        return AnnouncementSerializer(new_announcement).data

    def read_announcement(self, parameters):
        try:
            announcement = Announcements.objects.get(id=parameters['announcement_id'])
            announcement.read.add(self.user)
            announcement.save()
        except:
            return {'announcement', 'no announcement'}
        return {'announcement': 'viewed'}

        # q = DashboardAggregations.objects

    def send_dashboard_data_element_email(self, parameters):
        print(parameters)
        endpoint = parameters.get('endpoint', "/dashboard/dashboard-data/")
        request = parameters.get('request', {})
        excluded = ['line_chart', 'bar_chart']
        to = parameters.get('recipients', [{"email": self.user.email, "userID": self.user.id}, ])
        if not len(to):
            to = [{"email": self.user.email, "userID": self.user.id}, ]
        if request.get('chart_type') == 'numberHighlights':
            client = APIClient()
            refresh = RefreshToken.for_user(self.user)
            client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))
            response = client.post(endpoint, request, format='json')
            data = response.json()
            print("DATA LENGTH", len(data))
            resp = "Nothing Happened"
            for t in to:
               resp = self.send_number_highlights_email(
                    subject=parameters.get('email').get('subject'),
                    to=t,
                    message=parameters.get('email').get('body'),
                    data=data,
                    emailID=parameters.get('emailID'),
                    conditionalFormatting=parameters.get('conditionalFormatting', {}),
                )
            return resp
        elif request.get('chart_type') not in excluded:

            lambda_request = {"sheets": [{
                "request": request,
                "endpoint": endpoint,
                "conditionalFormatting": parameters.get('conditionalFormatting', {}),
                "name": "subscription_data",
            }], 'password': "C4QwE4hvemtmhLXS", }
            print(lambda_request)

            s3_link = requests.post(LAMBDA_EXCEL_FROM_REQUEST_ENDPOINT, json=lambda_request)
            resp = s3_link.json()
            print(resp)
            attachmentLink = s3_link.json()['link']
            for t in to:
                self.send_excel_email(
                    subject=parameters.get('email').get('subject'),
                    to=t,
                    emailID=parameters.get('emailID'),
                    message=parameters.get('email').get('body'),
                    dataURL=attachmentLink,

                )
            return "Success"

        else:
            return "Not Available."



@csrf_exempt
def update_email_table_lambda_data(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data, "THIS IS THE REQUEST")
    id = data['id']
    lambda_data = data['lambdaData']
    emailObject = EmailData.objects.get(id=id)
    emailObject.lambdaTableData = lambda_data
    emailObject.save()
    return "Success!"


@csrf_exempt
def update_email_data(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data, "THIS IS THE REQUEST")
    id = data['id']
    lambda_data = data['lambdaData']
    emailObject = EmailData.objects.get(id=id)
    emailObject.lambdaSVGData = lambda_data
    emailObject.save()
    return "Success!"


import json
from rest_framework.renderers import JSONRenderer


@csrf_exempt
@api_view(('POST',))
@renderer_classes((JSONRenderer,))
def get_email(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data, "THIS IS THE REQUEST")
    id = data['id']
    print("PARAMETERS", id)
    emailObject = EmailData.objects.get(id=id)
    emailObject = EmailDataSerializer(emailObject).data
    # sendTo = UserEmails.objects.get(email_data=emailObject)
    # emailObject = model_to_dict(emailObject)
    # sendTo = [{'value': sendTo.user.email}]
    # print(emailObject)
    # print(sendTo)
    return Response(emailObject, status=status.HTTP_200_OK)


@csrf_exempt
def trigger_emails(request):
    data = json.loads(request.body.decode('utf-8'))
    r = requests.get('http://localhost:8080/email-generator/?id=31')
    print(r)
    print(data)
    return HttpResponse(r)




