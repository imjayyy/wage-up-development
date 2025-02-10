from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response
from fcm_django.models import FCMDevice
import datetime as dt
from datetime import timezone
from .models import *
from django.db.models.functions import Concat
from django.db.models import F, Value as V
import requests
from django.core import serializers
from .serializers import *
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.decorators import authentication_classes, permission_classes
import json
from rest_framework.renderers import JSONRenderer
from accounts.models import Profile, Employee
from fcm_django.models import *
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Max
from django.conf import settings
from email.mime.image import MIMEImage
import os

import json

# Initiate session
from boto3.session import Session

# from ics import Calendar, Event
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
import requests
from django.utils.html import strip_tags
import io
from django.http import HttpResponse, Http404
from accounts.jwt_serializers import TokenVerifySerializer, TokenRefreshSerializer
from django.utils import timezone

LAMBDA_MESSAGING_ENDPOINT = "https://ve1mc0qia6.execute-api.us-east-1.amazonaws.com/dev/"


@renderer_classes((JSONRenderer,))
@csrf_exempt
@api_view(('POST',))
@authentication_classes([])
@permission_classes([])

def alert_data_processing(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data)

    wageup_staff_user_ids = [2, 4, 55] # devin, chrissy, cody
    if data.get('send_to'):
        wageup_staff_user_ids = data.get('send_to')

    if data['p'] != "sWZHd5gmM9gupRK9uN33yfCLkQfm5Quc5meqEtgv":
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    else:
        msg = {
            "data": {
                "msg_type": "airflowError",
                "title": data.get('title', "Wageup ETL Error"),
                "body": data['message'],
                "url": "https://cloud.prefect.io/wageup/",
                "time": dt.datetime.strftime(dt.datetime.now().astimezone(timezone.utc), "%Y-%m-%d %H:%M"),
            }
        }
        audience = FCMDevice.objects.filter(user_id__in=wageup_staff_user_ids)
        audience.send_message(**msg)


        # send email
        def email_alert(employee, content, mail_subject, template='etl_problem.html'):
            message = render_to_string('qa/' + template, {
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'content': content,
            })
            print("SENT ERROR EMAIL TO: ", employee.user.email)
            to_email = employee.user.email
            email = EmailMessage(mail_subject, message, 'wageup-etl-alert@wageup.com', to=[to_email])
            email.send()

        wageup_employees = Employee.objects.filter(user_id__in=wageup_staff_user_ids)

        for employee in wageup_employees:
            email_alert(employee, data['message'], data.get('title', "Wageup ETL Error"))

    return Response("Sent", status=status.HTTP_200_OK)

def generateS3File(filename, file):
    session = Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    s3 = session.resource('s3')
    client = session.client('s3')
    bucket = 'wageup-chat-temp-files'

    if filename == file:
        s3.Bucket(bucket).upload_file(filename, filename)
    else:
        s3.Bucket(bucket).put_object(Key=filename, Body=file)

    url = client.generate_presigned_url('get_object',
                                        Params={'Bucket': bucket,
                                                'Key': filename},
                                        ExpiresIn=86400)
    return url


def send_ics_email(mail_subject, html_message, to_email, icsFileURL, filename):
    mail_subject = mail_subject
    plain_message = strip_tags(html_message)
    mail = EmailMultiAlternatives(mail_subject, plain_message, 'events@wageup.com', to_email)
    mail.mixed_subtype = 'related'
    mail.attach_alternative(html_message, "text/html")
    r = requests.get(icsFileURL)
    attachment = io.BytesIO(r.content)
    print(r, icsFileURL, attachment)
    with open(settings.BASE_DIR + '/media/logo.png', 'rb') as logo:
        img = MIMEImage(logo.read(), 'png')
        img.add_header('Content-Id', '<logo.png>')
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        mail.attach(img)
    mail.attach(filename, attachment.getvalue(), 'text/calendar')
    mail.send()

@renderer_classes((JSONRenderer,))
@csrf_exempt
@api_view(('POST',))
@authentication_classes([])
@permission_classes([])
def verify_token(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data)
    try:
        is_authenticated = TokenVerifySerializer(
            data={'token': data['access_token']}).is_valid()  # try to confirm that this is a valid instance
    except:
        return Response("BAD ACCESS TOKEN", status=status.HTTP_401_UNAUTHORIZED)
    if is_authenticated:
        return Response("OK", status=status.HTTP_200_OK)
    else:
        return Response("BAD ACCESS TOKEN", status=status.HTTP_401_UNAUTHORIZED)


@renderer_classes((JSONRenderer,))
@csrf_exempt
@api_view(('POST',))
@authentication_classes([])
@permission_classes([])
def record_notification_response(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data)
    metaData = json.loads(data['payload']['data'])
    device = FCMDevice.objects.filter(registration_id=data['user_token'])[0]
    if data['action'] == 'silence-login':
        profile = device.user.profile.get()
        profile.silence_login_notifications = True
        profile.save()

    if 'broadcast' in data['action']:
        response = data['action'].split('-')[-1]

        intro_text = """
        <p>You have been invited to a meeting. Be sure to open the attached invite file to add it to your calendar and view details.!</p>
        """
        meeting_qs=Meeting.objects.filter(id=int(data['meeting_id']))
        meeting = meeting_qs.values()[0]
        time = meeting['meeting_time'] + dt.timedelta(hours=-4)
        lambda_data = {'data': [{'intro_text': intro_text}]}
        if metaData.get('broadcastMessage', False):
            lambda_data['data'].append({
                "text": "Event Details: " + metaData.get('broadcastMessage'),
                "button": {"link": data['meeting_link'], "text": "Go to the Meeting Now"}
            })
            lambda_data['data'].append({
                "text": "Event Starts: " +
                        meeting['meeting_time'].strftime("%A %b %d, %Y") +
                        " at " +
                        meeting['meeting_time'].strftime("%I:%m %p") + " EST"
            })
            lambda_data['data'].append({
                "text": "Participants Invited: " + ", ".join(meeting_qs.last().participants.all().values_list('employee__display_name', flat=True))
            })
        lambda_response = requests.post(LAMBDA_MESSAGING_ENDPOINT, json=lambda_data)
        html = lambda_response.json()['body']['html'].replace('/\\"/g', '"')



        send_ics_email(metaData.get('broadcastEventName', "New Meeting") + '-- (Meeting Invite Attached)', html, [device.user.email], data['icsURL'], metaData['filename'])

        obj = {
            'message_id':data['message_id'],
            'user': device.user,
            'responseChar': data['action']
        }
        if response in ['yes', 'no']:
            obj['responseBool'] = response == 'yes'
        broadcast_resp = BroadcastResponse.objects.create(**obj)

        print('broadcast response', broadcast_resp)

    return Response("OK", status=status.HTTP_200_OK)



class Chat(generics.GenericAPIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def add_s3_file(self, filename):
        print(self.request.data)

        url = generateS3File(filename, self.request.data['uploadedFile'])

        print(url)
        users_name=self.user.first_name + ' ' + self.user.last_name
        msg = {
            "data": {
                "msg_type": "fileUpload",
                "title": users_name + " wants to send you a file.",
                "body": "The file is: " + filename,
                "icon": self.getAvatar("self"),
                "badge": self.logo,
                "tag": "fileUpload",
                "group": self.request.data["group"],
                "filename": filename,
                "data": {
                    "type": "fileUpload",
                    "filename": filename,
                    "url": url,
                },
                "url": url,
                "time": dt.datetime.strftime(dt.datetime.now().astimezone(timezone.utc), "%Y-%m-%d %H:%M"),
                "sent_by": {
                    "id": self.user.id,
                    "photo_avatar": self.getAvatar("self"),
                    "display_name": self.user.first_name + " " + self.user.last_name
                    }
            }
        }
        group = ChatGroup.objects.get(id=self.request.data['group'])
        audience = self.get_audience(group.invited_users.all())
        audience.send_message(**msg)

        message = ChatMessage.objects.create(from_user_id=self.user.id,
                                             data=json.dumps(msg['data'].get('data', None)),
                                             group_id=self.request.data['group'])
        group.lastMessageId = message.id
        group.lastMessageTime = message.time
        group.save()

        return {'filename': filename, "url": url}

    def generate_ics_file(self, event):
        """
        :param event: {'begin':'2014-01-01 00:00:00', 'name' 'my meeting', 'description', 'my meeting is about pandas', 'end' '2014-01-01 01:00:00'}
        :return: s3 url for event ics file
        """
        c = Calendar()
        e = Event()
        e.name = event['name']  # "My cool event"
        c.method = 'REQUEST'
        e.location = event.get('meetingLink', 'https://demo.wageup.com/chat/')
        e.summary = event['description']
        e.description = event['description']
        e.status = 'confirmed'
        e.organizer = self.user.email
        e.begin = event.get('begin')  # '2014-01-01 00:00:00'
        e.end = event.get('end')
        e.attendees = event.get('attendees')


        c.events.add(e)
        filename = event['name'].replace(' ', '_') + '.ics'
        with open(filename, 'w+') as f:
            f.writelines(c)
        url = generateS3File(filename, filename)
        os.remove(filename)

        return url, filename

    def messageSerializer(self, messages):
        return list(messages.annotate(photo_avatar=F('from_user__profile__photo_avatar'), from_user_name=F('from_user__profile__user__employee__full_name'),
                  message_id=F('id')).order_by('time').values('message', 'photo_avatar', 'from_user_id', 'group_id',
                                                              'data', 'time', 'id', 'from_user_name'))

    def updateNotificationLog(self, users, notification_type, message):
        bulk = []
        for user in users:
            bulk.append(
                NotificationLog(user=user, notification=json.dumps(message), type=notification_type)
            )
        NotificationLog.objects.bulk_create(bulk)

    def post(self, request):
        self.request = request
        self.logo = "https://wageup-media.s3.us-east-1.amazonaws.com/wageupLogo850.png"
        self.clientLogo = "https://wageup-media.s3.us-east-1.amazonaws.com/aaaLogo.png"

        self.user = request.user
        self.avatar = False
        if 'parameters' in request.data:
            self.parameters = request.data['parameters']
        else:
            self.parameters = {}

        purpose_router = {
            'loginChat': self.loginChat, #let everyone know you joined
            'createChat': self.createChat, #create a new chat; let invited users know you created it
            'joinChat': self.joinChat, # accept chat invite
            'submitChatMessage': self.submitChatMessage, # send a message
            'refreshOnlineUsers': self.refreshOnlineUsers, # get a full user list
            'logoutChat': self.logoutChat ,# leave chat --- will probably be ammended to various status messages
            'new_meeting': self.new_meeting,
            'join_meeting': self.join_meeting,
            'add_user_to_chat': self.add_user_to_chat,
            'get_closed_groups': self.get_closed_groups,
            'add_s3_file': self.add_s3_file,
            'leave_meeting': self.leave_meeting,
            'switch_privacy': self.switch_privacy
        }

        out = purpose_router[request.data['purpose']](self.parameters)

        return Response(out, status=status.HTTP_200_OK)

    def switch_privacy(self, parameters):
        group = ChatGroup.objects.get(id = parameters['chatGroup'])
        newPrivacy = not group.private
        newGroup = ChatGroup.objects.get_or_create(name=group.name, private=newPrivacy)

        invited_users_data = list(newGroup.invited_users.annotate(
                                         name=F('employee__full_name'),
                                         position_type=F('employee__position_type'),
                                         organization = F('employee__organization__name'),
                                         avatar=Concat(V('https://wageup-media.s3.amazonaws.com/'),
                                                       F('profile__photo_avatar'))).values('username', 'name', 'position_type', 'organization','avatar', 'id'))

        msg = {
            'data': {
                'msg_type': 'chatInvite',
                'title': 'The chat was set to private',
                'icon': self.getAvatar('self'),
                'badge': self.logo,
                'private': newPrivacy,
                'private_switch': True,
                'old_group': group.id,
                'tag': 'chatInvite',
                'group': newGroup.id,
                'redirect': 'https://demo.wageup.com?chatgroup=' + str(newGroup.id),
                'users': invited_users_data,
                'invited_by': {
                    'id': self.user.id,
                    'photo_avatar': self.getAvatar('self'),
                    'display_name': self.user.first_name + ' ' + self.user.last_name
                    }
            },
        }

        audience = self.get_audience(newGroup.invited_users.all())
        audience.send_message(msg)

    def add_user_to_chat(self, parameters):
        #TODO: dont do private just create a new chat with all the users
        print(parameters)
        invited_user_qs = User.objects.filter(id=parameters['user'])
        original_group = ChatGroup.objects.get(id=parameters['chatGroup'])
        original_users = original_group.invited_users.all()
        new_name = list(original_users.values_list('id', flat=True)) + [parameters['user'],]
        new_name = [str(u) for u in new_name]
        new_name.sort()
        new_name = "-".join(new_name)
        group, created = ChatGroup.objects.get_or_create(name=new_name, private=False)
        group.invited_users.add(invited_user_qs[0])
        for user in original_users:
            group.invited_users.add(user)
        group.save()

        invited_users_data = list(group.invited_users.annotate(
                                         name=F('employee__full_name'),
                                         position_type=F('employee__position_type'),
                                         organization = F('employee__organization__name'),
                                         avatar=Concat(V('https://wageup-media.s3.amazonaws.com/'),
                                                       F('profile__photo_avatar'))).values('username', 'name', 'position_type', 'organization','avatar', 'id'))
        invite_body = parameters.get('invite_body', "Hey can you hop on WageUp to chat for a bit?")

        msg = {
            'data': {
                'msg_type': 'chatInvite',
                'title': self.user.first_name + ' ' + self.user.last_name+ ' wants to talk to you.',
                'body': invite_body,
                'icon': self.getAvatar('self'),
                'badge': self.logo,
                'private': False,
                'tag': 'chatInvite',
                'redirect': 'https://demo.wageup.com?chatgroup=' + str(group.id),
                'group': group.id,
                'users': invited_users_data,
                'invited_by': {
                    'id': self.user.id,
                    'photo_avatar': self.getAvatar('self'),
                    'display_name': self.user.first_name + ' ' + self.user.last_name
                    }
            },
        }

        new_user_audience = self.get_audience(invited_user_qs)
        original_user_audience = self.get_audience(original_users)
        new_user_audience.send_message(**msg)
        msg['data']['switch_chat'] = True
        msg['data']['silent'] = True
        msg['data']['old_group'] = original_group.id
        original_user_audience.send_message(**msg)
        self.updateNotificationLog(original_users, 'chatInvite', msg)
        self.updateNotificationLog(invited_user_qs, 'chatInvite', msg)

    def get_closed_groups(self, parameters):
        print(parameters)
        group_q = ChatGroup.objects\
            .filter(invited_users__id=self.user.id)\
            .order_by('-lastMessageTime')
        groups = ChatGroupSerializer(group_q, many=True).data
        messages = self.messageSerializer(ChatMessage.objects.filter(group_id__in=group_q.values_list('id', flat=True)))
        missed_notifications = NotificationLog.objects.filter(user=self.user).order_by('-id')
        missed_notifications_v = list(missed_notifications.annotate(from_name=F('user__employee__full_name')).values())
        # missed_notifications.delete()
        return {'groups': groups, 'messages': messages, 'missed_notifications': missed_notifications_v}

    def get_audience(self, userList=False, type=False):

        userSettingsFilter = {'profile__chat_status' : 'Available', 'profile__silence_all_notifications': False}
        if type == 'login':
            userSettingsFilter['profile__silence_watched_login_notifications'] = False
            userSettingsFilter['profile__silence_all_notifications'] = False
        elif type == 'chatMessage':
            userSettingsFilter['profile__silence_message_notifications'] = False
        if not userList:
            userList = User.objects.filter(**userSettingsFilter)
        else:
            userList = userList.filter(**userSettingsFilter)
        return FCMDevice.objects.filter(user__in=userList)

    def getAvatar(self, image):
        defaultImg = "https://wageup-media.s3.amazonaws.com/anonymous-user.png"
        if image == 'self':
            if not self.avatar:
                self.avatar = User.objects.filter(id=self.user.id).values('profile__photo_avatar')[0]['profile__photo_avatar']
            print('avatar is', self.avatar)
            if len(self.avatar) < 2:
                return defaultImg
            return 'https://wageup-media.s3.amazonaws.com/' + self.avatar


        if image is None:
            return defaultImg
        elif image == 'https://wageup-media.s3.amazonaws.com/':
            return defaultImg
        elif 'https://' not in image:
            return 'https://wageup-media.s3.amazonaws.com/' + image
        else:
            return image

    def logoutChat(self, parameters):
        audience = self.get_audience()
        print('audience is: ', audience)
        if 'photo_avatar' not in parameters['user']:
            parameters['user']['photo_avatar'] = None
        msg = {
            # 'title': self.user.first_name + ' ' + self.user.last_name + 'Left',
            # 'body': self.user.first_name + ' ' + self.user.last_name + " logged out.",
            'data': {
                'msg_type': 'chatLogout',
                'title': 'Logout',
                'body': parameters['user']['display_name'] + ' just logged out.',
                'icon': parameters['user']['photo_avatar'],
                'badge': self.logo,
                'tag': 'chatLogout',
                'name': parameters['user']['display_name'],
                'avatar': parameters['user']['photo_avatar'],
                'username': parameters['user']['user']['username'],
                'time': dt.datetime.strftime(dt.datetime.now().astimezone(timezone.utc), '%Y-%m-%d %H:%M'),
            },
        }
        print(msg)
        audience.send_message(**msg)
        profile = self.user.profile.get()
        profile.chat_status = "Offline"
        # me = OnlineUsers.objects.get(user=self.user)
        # me.delete()

    def loginChat(self, parameters):
        profile = self.user.profile.get()
        profile.chat_status='Available'
        profile.save()
        audience = self.get_audience(type='login')
        print('audience is: ', audience)
        if 'photo_avatar' not in parameters['user']:
            parameters['user']['photo_avatar'] = None
        msg = {
            # 'title': 'New Login',
            # 'body': self.user.first_name + ' ' +  self.user.last_name + " logged in.",
            'data': {
                'msg_type': 'chatLogin',

                'title': 'ACA Roadside Dashboard Login',
                'body':  parameters['user']['display_name'] + ' just logged in.',
                'icon': parameters['user']['photo_avatar'],
                'badge': self.logo,
                'tag': 'chatLogin',
                'name': parameters['user']['display_name'],
                'avatar': parameters['user']['photo_avatar'],
                'username': parameters['user']['user']['username'],
                'user': self.user.id,
                'actions': [
                    {
                        'action': 'silence-login',
                        'icon': 'https://wageup-medFia.s3.us-east-1.amazonaws.com/silent.png',
                        'title': 'Silence Login Messages'
                    }
                ],
                'time': dt.datetime.strftime(dt.datetime.now().astimezone(timezone.utc), '%Y-%m-%d %H:%M'),
            },
        }
        print(msg)
        audience.send_message(**msg)
        return 'OK'

    def refreshOnlineUsers(self, parameters):
        allUsers = Profile.objects.annotate(time=F('user__last_login'))\
            .filter(chat_status='Available')\
            .order_by('-user__last_login')\
            .annotate(username=F('user__username'),
                                         name=F('user__employee__full_name'),
                                         position_type=F('user__employee__position_type'),
                                         organization = F('user__employee__organization__name'),
                                         avatar=Concat(V('https://wageup-media.s3.amazonaws.com/'),
                                                       F('user__profile__photo_avatar'))).values('username', 'name', 'position_type', 'organization', 'time', 'avatar', 'user_id')
        return list(allUsers)

    def createChat(self, parameters):
        print('create chat', parameters)
        if 'invitedEmployees' in parameters:
            parameters['invitedUsers'] = list(Employee.objects.filter(id__in=parameters['invitedEmployees']).values_list('user_id', flat=True))

        private = False
        print(parameters['invitedUsers'])
        if len(parameters['invitedUsers']) < 3:
            private = True

        users = parameters['invitedUsers']
        if self.user.id not in parameters['invitedUsers']:
            users = [self.user.id,] + parameters['invitedUsers']
        users.sort()
        chatGroupName = "-".join([str(u) for u in users])

        #update models
        group, created = ChatGroup.objects.get_or_create(name=chatGroupName, private=private)
        print(users)
        invited_users = User.objects.filter(id__in=users)
        print(invited_users)
        print(group, created)
        group.invited_users.add(*invited_users)
        group.online_users.add(self.user)
        group.save()

        invited_users_data = list(invited_users.annotate(
                                         name=F('employee__full_name'),
                                         position_type=F('employee__position_type'),
                                         organization = F('employee__organization__name'),
                                         avatar=Concat(V('https://wageup-media.s3.amazonaws.com/'),
                                                       F('profile__photo_avatar'))).values('username', 'name', 'position_type', 'organization','avatar', 'id'))


        invite_body = parameters.get('invite_body', "Hey can you hop on WageUp to chat for a bit? Click this to go.")

        msg = {
            'data': {
                'msg_type': 'chatInvite',
                'title': self.user.first_name + ' ' + self.user.last_name + ' wants to talk to you.',
                'body': invite_body,
                'icon': self.getAvatar('self'),
                'badge': self.logo,
                'private': private,
                'tag': 'chatInvite',
                'redirect': 'https://demo.wageup.com?chatgroup=' + str(group.id),
                'group': group.id,
                'users': invited_users_data,
                'invited_by': {
                    'id': self.user.id,
                    'photo_avatar': self.getAvatar('self'),
                    'display_name': self.user.first_name + ' ' + self.user.last_name
                    }
            },
        }

        if parameters.get('type', False):
            msg_data = parameters.get('data', {})
            # broadcast ...
            msg = {
                'data': {
                    'msg_type': parameters.get('type'),
                    'title': parameters.get('title', 'ACA ANNOUNCEMENT'),
                    'body': parameters.get('body', 'Click to go the site.'),
                    'icon': self.logo,
                    'badge': self.logo,
                    'tag': parameters.get('type'),
                    'redirect': 'https://demo.wageup.com?chatgroup=' + str(group.id),
                    'actions': parameters.get('actions', []),
                    'data': msg_data
                },
            }



            if msg_data.get('addCalendarInvite', False):

                begin_time = msg_data.get('broadcastEventStartDate', dt.datetime.now())
                if type(begin_time) != str:
                    begin_time = begin_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    begin_time = begin_time[:19].replace('T', ' ')
                    print(begin_time)

                msg['data']['body'] += " Event scheduled for " + begin_time
                event = {
                    'begin': begin_time,
                    'name': msg_data.get('broadcastEventName', "New Meeting"),
                    'description': msg_data.get('broadcastMessage', 'You were invited to an event'),
                    'end': msg_data.get('broadcastEventEndDate', (
                            dt.datetime.strptime(begin_time, "%Y-%m-%d %H:%M:%S") + dt.timedelta(
                        hours=1)).strftime('%Y-%m-%d %H:%M:%S'))
                }

                if parameters['data'].get('addConferenceCall', False):
                    meeting_name = (msg_data.get('broadcastEventName', "NewMeeting") + begin_time).replace(' ', '_').replace(':', '-')
                    new_meeting = Meeting.objects.create(
                        meeting_creator=self.user,
                        meeting_name=meeting_name,
                        meeting_time=begin_time,
                    )
                    new_meeting.save()
                    for user in group.invited_users.all():
                        new_meeting.participants.add(user)
                    new_meeting.save()
                    msg['data']['meeting_name'] = meeting_name
                    msg['data']['meeting_id'] = new_meeting.id
                    event['meetingLink'] = 'https://demo.wageup.com?chatgroup=' + str(group.id) + '&meeting=' + meeting_name + '&meetingid=' + str(new_meeting.id)

                event['attendees'] = []
                for user in group.invited_users.all():
                    event['attendees'].append(user.email)

                msg['data']['icsURL'], msg['data']['data']['filename'] = self.generate_ics_file(event)
                msg['data']['meeting_link'] = event['meetingLink']





            message = ChatMessage.objects.create(
                data= msg,
                from_user= self.user,
                type= parameters.get('type')
            )

            msg['data']['message_id'] = message.id

            audience = self.get_audience(invited_users)
            print(audience, msg)
            audience.send_message(**msg)

            self.updateNotificationLog(invited_users, 'chatInvite', msg)

        else:
            audience = self.get_audience(invited_users.exclude(id=self.user.id))
            print("Starting new chat", audience, msg)
            audience.send_message(**msg)
            self.joinChat({'group_id': group.id})
            self.updateNotificationLog(invited_users.exclude(id=self.user.id), 'chatInvite', msg)
            return {'messages': self.messageSerializer(ChatMessage.objects.filter(group_id=group.id)), 'group': group.id}


    def joinChat(self, parameters):
        print("join chat", parameters)
        group = ChatGroup.objects.get(id=parameters['group_id'])
        private = False
        if group.invited_users.filter(id=self.user.id).exists():
            group.online_users.add(self.user)
            group.save()
            onlineUserNameList = []
            avatars = []
            users = []
            for user in group.online_users.all().values('first_name', 'last_name', 'profile__photo_avatar', 'id'):
                print('user', user)
                if self.user.id == user['id']:
                    onlineUserNameList.append('Me')
                else:
                    onlineUserNameList.append(user['first_name'] + ' ' + user['last_name'][0] + '.')
                avatars.append(user['profile__photo_avatar'])
                users.append(user['id'])
            invitedUserList = []
            for user in group.invited_users.all().values('first_name', 'last_name', 'profile__photo_avatar', 'id'):
                if self.user.id == user['id']:
                    invitedUserList.append('Me')
                else:
                    invitedUserList.append(user['first_name'] + ' ' + user['last_name'][0] + '.')
            if len(onlineUserNameList) == 1:
                displayName = 'Waiting for others...'
            else:
                displayName = ', '.join(onlineUserNameList)

            invitedDisplay = ", ".join(invitedUserList)

            msg = {
                'data': {
                    'msg_type': 'joinedChat',
                    'title': self.user.first_name + ' ' + self.user.last_name + ' (' + self.user.username + ") joined the chat.",
                    'body': "This user is now logged into chat.",
                    'icon': self.getAvatar('self'),
                    'badge': self.logo,
                    'tag': 'joinedChat',
                    'private': private,
                    'invitedDisplay': invitedDisplay,
                    'group': group.id,
                    'users': users,
                    'avatars': avatars,
                    'joiningUser': self.user.id,
                    'chatGroupName': group.name,
                    'chatDisplayName': displayName,
                },
            }

            if 'switch_chat' in parameters:
                msg['data']['switch_chat'] = True

            audience_users = group.online_users.all()
            audience = self.get_audience(audience_users)
            print(audience, msg)
            audience.send_message(**msg)
            # self.updateNotificationLog(audience_users, 'chatInvite', msg)

            if 'last_message_id' in parameters:
                messages = False
                if parameters['last_message_id'] is not None:
                    messages = ChatMessage.objects.filter(group_id=group.id, id__gt=parameters.get('last_message_id', 0))
                if messages:
                    new_messages = self.messageSerializer(messages)
                else:
                    new_messages = []
                return {'messages': new_messages, 'group': group.id}

    def submitChatMessage(self, parameters):
        group = ChatGroup.objects.get(id=parameters['group_id'])
        print(parameters)
        data = json.loads(parameters.get('data', '{"data": "empty"}'))

        print(parameters)

        msg = {
            'data': {
                'title': self.user.first_name + ' ' + self.user.last_name + " sent you a message.",
                'body': parameters['message'],
                'icon': self.getAvatar('self'),
                'badge': self.logo,
                'tag': 'chatMessage',
                'msg_type': 'chatMessage',
                'group': parameters['group_id'],
                'redirect': 'https://demo.wageup.com?chatgroup=' + str(group.id),
                'from_user': self.user.id,
                'from_user_name': self.user.first_name + ' ' + self.user.last_name,
                'photo_avatar': self.getAvatar('self'),
                'time': dt.datetime.strftime(dt.datetime.now().astimezone(timezone.utc), '%Y-%m-%d %H:%M'),
            },
        }

        if 'data' in parameters:
            msg['data']['msg_type'] = data['type']
            msg['data']['data'] = data['info']
        else:
            msg['data']['message'] = parameters['message']

        unicode_message = parameters['message'].encode('unicode-escape').decode('ASCII')

        print(msg)
        message_audience = group.online_users.all()
        audience = self.get_audience(message_audience)
        audience.send_message(**msg)

        # convert to utf8
        saved_msg = ChatMessage(from_user_id=self.user.id,
                                             message=unicode_message,
                                             data=parameters.get('data', None),
                                             group=group)
        saved_msg.save()
        print(saved_msg.id)
        group.lastMessageID = saved_msg.id
        group.lastMessageTime = saved_msg.time
        group.save()
        self.updateNotificationLog(message_audience, 'chatMessage', msg)

    def new_meeting(self, parameters):
        """
        {
             "purpose": "new_meeting",

                "parameters": {
                    "user":"2736"
                    "chatGroup: "2",
                    "meeting_name":"mymeeting",
                    "meeting_time":"20200828100000"
                }
             }
        create new meeting:
        POST
        https://aca-conferencing.wageup.com/v2/join?title=6542&name=asdf&region=us-east-1
        http://127.0.0.1:8080/?m=asdf&attendeeName=matt&t={token}
        """
        print(parameters)
        if parameters.get('meeting_time', False):
            date_string=parameters['meeting_time'].replace(':','-')
        else:
            now = datetime.now()
            date_string=now.strftime("%Y%m%d%H%M%S")

        if parameters.get('meeting_name', False):
            meeting_name=parameters['meeting_name']
        else:
            meeting_name=''

        meeting_name+=date_string
        datetime_object = datetime.strptime(date_string, '%Y%m%d%H%M%S')

        try:
            user_object=User.objects.filter(id=parameters['user'])[0]#.values('username')[0]['username']
            username = User.objects.filter(id=parameters['user']).values('username')[0]['username']
        except:
            raise Exception("Need username")

        new_entry = Meeting.objects.create(
            meeting_creator=user_object,
            meeting_name=meeting_name,
            meeting_time=datetime_object,
        )
        new_entry.save()

        for user in ChatGroup.objects.get(id=parameters['chatGroup']).invited_users.all():
            new_entry.participants.add(user)

        new_entry.save()

        return {
            'meeting_creator':username,
            'meeting_name' :meeting_name,
            'meeting_time' : date_string,
            'meeting_id': new_entry.id,
        }



    def leave_meeting(self, parameters):
        print('leaving meeting', parameters)



    def join_meeting(self, parameters):
        """
        {
         "purpose": "join_meeting",

            "parameters": {
                "user":"2736",
                "meeting_name":"meetingname"
            }
        }

        Join meeting if exists:
        GET
        https://aca-conferencing.wageup.com/v2/?m=654 then
        POST
        http://127.0.0.1:8080/?m=asdf&attendeeName=matt&t={token}
        """
        print(parameters)
        meeting = Meeting.objects.get(id=int(parameters['meeting_id']))

        if not meeting:
            return "Meeting doesnt exist"
        if meeting.meeting_time > (timezone.now() + dt.timedelta(minutes=15)):
            print("meeting hasnt started yet")
            return "Meeting hasnt started yet"

        user = User.objects.get(id=parameters['user'])  # .values('username')[0]['username']
        if user:
            username = user.username
        else:
            return "This is not a user"

        meeting_params = {
            "meeting_name": parameters['meeting_name'],
            "attendeeName": username,
            "access": parameters['access']
        }

        meeting_link='https://aca-conferencing.wageup.com/v2/?m={meeting_name}&attendeeName={attendeeName}&t={access}'.format(**meeting_params)
        # meeting_link="https://8x9bh6usrg.execute-api.us-east-1.amazonaws.com/Prod/v2/?m={0}".format(parameters['meeting_name'])


        # join_url = "https://aca-conferencing.wageup.com/join?"
        # join_url = "https://8x9bh6usrg.execute-api.us-east-1.amazonaws.com/Prod/v2/join?"
        # payload = "&title={0}&name={1}&region=us-east-1&t={2}".format(parameters['meeting_name'],username,parameters['access'] )
        # meeting_link+=payload

        output = {}
        output['join_url'] = meeting_link
        print(meeting_link)
        return output

        # try:
        #     response = requests.request("GET", meeting_link)
        #     print(response)
        #     if response.status_code==200:
        #         # response = requests.request("POST", join_url)
        #         # print(response)
        #         # if response.status_code==200:
        #         output=response.json()
        #         output['join_url']=meeting_link
        #             # output['join_url']=join_url
        #         return output
        #     else:
        #         raise Exception("Request to aca-conferencing failed.  Please contact developer.")
        # except:
        #     raise Exception("Request to aca-conferencing failed.  Please contact developer.")