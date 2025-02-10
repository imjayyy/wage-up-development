from channels.generic.websocket import WebsocketConsumer
from channels.consumer import SyncConsumer
from asgiref.sync import async_to_sync
import json, time
# from accounts.models import SocketConnections, User
from accounts.jwt_serializers import TokenVerifySerializer, TokenRefreshSerializer
# from messaging.models import ChatGroup, ChatMessage
from django.db.models.functions import Concat
from django.db.models import F, Value as V
import datetime as dt
from datetime import timezone, datetime, timedelta
from rest_framework_simplejwt.state import token_backend
from fcm_django.models import FCMDevice
# from messaging.views import sendFirebaseNotification


class chatConsumer(WebsocketConsumer):

    def getAvatar(self, image):
        defaultImg = "https://wageup-media.s3.amazonaws.com/anonymous-user.png"

        if image is None:
            return defaultImg
        elif image == 'https://wageup-media.s3.amazonaws.com/':
            return defaultImg
        elif 'https://' not in image:
            return 'https://wageup-media.s3.amazonaws.com/' + image
        else:
            return image

    def sendFirebaseNotification(self, event):
        userList = event['chatGroupName'].split('-')
        fcm_devices = FCMDevice.objects.filter(user__in=userList)
        print('sending message', fcm_devices, event)
        if 'photo_avatar' not in event['user']:
            event['user']['photo_avatar'] = None

        message = {
            'title': "New Chat",
            'body': event['message'],
            'data': {
                'msg_type': 'chat',
                'group': event['group'],
                'chatMessage': {
                    'photo_avatar': self.getAvatar(event['user']['photo_avatar']),
                    'from': event['user']['user']['id'],
                    'message': event['message']
                }
            },

            'icon': self.getAvatar(event['user']['photo_avatar']),
        }
        fcm_devices.send_message(**message)
        group = ChatGroup.objects.get(id=event['group'])
        msg, created = ChatMessage.objects.get_or_create(from_user_id=event['user']['user']['id'], message=event['message'])
        if created:
            group.messages.add(msg)
            group.save()

    http_user = True

    def connect(self):
        self.room_name = 'all'
        self.room_group_name = 'chat_%s' % self.room_name
        print(self.scope['headers'])

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def authenticate(self, event):
        access_token = event['user']['access']
        refresh_token = event['user']['refresh']
        print("access token is", access_token, 'refresh_token is', refresh_token)
        refresh_acceptable = {}
        try:
            is_authenticated = TokenVerifySerializer(data={'token': access_token}).is_valid() # try to confirm that this is a valid instance
        except:
            is_authenticated = False
        if not is_authenticated:
            try:
                refresh_acceptable = TokenRefreshSerializer().validate(attrs={'refresh': refresh_token})
                if 'access' in refresh_acceptable:
                    print('acceptable')
                else:
                    self.disconnect()
            except Exception as e:
                print(e)
                self.disconnect()
        token_data = token_backend.decode(token=access_token)
        self.user_id = token_data['user_id']
        print('access', is_authenticated, 'refresh', 'access' in refresh_acceptable, 'authenticated')

    def disconnect(self, close_code=None):
        # Leave room group
        #TODO: BETTER WAY OF GETTING SELF.USER

        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
        print('disconnecting...')
        try:
            print('deleting user', self.user)
            SocketConnections.objects.get(user_id=self.user_id).delete()
        except Exception as e:
            print(e)

    def receive(self, text_data):
        event = json.loads(text_data)
        print("event is ", event)
        self.authenticate(event)
        print("Incoming request", event["type"], " from ", event['group'])
        if event['type'] == 'chatMessage':
            self.sendFirebaseNotification(event)
            # print('using room', event['chatGroupName'])
            # self.room_name = event['chatGroupName']
            # self.room_group_name = 'chat_%s' % self.room_name
            # async_to_sync(self.channel_layer.group_send)(self.room_group_name, event)
        else:
            self.room_name = 'all'
            self.room_group_name = 'chat_%s' % self.room_name
            async_to_sync(self.channel_layer.group_send)(self.room_group_name, event)

    def start_chat_group(self, event):
        users = [event['user']['user']['id'],] + event['invitedUsers']
        print(event, users, 'chat create')
        users.sort()
        chatGroupName = "-".join([str(u) for u in users])

        group, created = ChatGroup.objects.get_or_create(name=chatGroupName)

        self.send(text_data=json.dumps(
            {"infoType": "group_chat_created", "type": "push", "data": {'users': users, 'group': group.id, 'invited_by': event['user']}}
        ))

        group_users = list(User.objects.filter(id__in=users))
        for u in group_users:
            group.invited_users.add(u)
        group.save()

        # async_to_sync(self.channel_layer.group_add)(
        #     chatGroupName,
        #     self.channel_name
        # )



    def join_chat_group(self, event):
        print(event)
        group = ChatGroup.objects.get(id=event['group_id'])
        this_user = User.objects.get(id=event['user']['user']['id'])
        print(group, this_user)
        if group.invited_users.filter(id=this_user.id).exists():
            onlineUsers = group.online_users.all().values('first_name', 'last_name', 'profile__photo_avatar', 'id')
            group.online_users.add(this_user)
            group.save()
            print('Online users: ', onlineUsers)
            onlineUserNameList = []
            avatars = []
            for user in onlineUsers:
                if this_user.id == user['id']:
                    onlineUserNameList.append('Me')
                else:
                    onlineUserNameList.append(user['first_name'] + ' ' + user['last_name'][0] + '.')
                avatars.append(user['profile__photo_avatar'])
            if len(onlineUserNameList) == 0:
                displayName = 'Waiting for others...'
            else:
                displayName = ', '.join(onlineUserNameList)
            self.room_name = group.name
            self.room_group_name = 'chat_%s' % self.room_name

            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )

            send_this = {
                "infoType": 'user_joined_chat_group',
                "type": 'push',
                'data': {
                    'chatGroupName': group.name,
                    'chatDisplayName': displayName,
                    'avatar': avatars,
                    'users': list(group.online_users.all().values_list('id', flat=True)),
                    'group_id': group.id,
                    'messageHistory': list(group.messages.all().annotate(photo_avatar=F('from_user__profile__photo_avatar')).values('message', 'photo_avatar', 'from_user_id')),
                }
            }

            print(send_this)

            self.send(text_data=json.dumps(send_this))
        else:
            self.send(text_data=json.dumps({
                "infoType": 'user_denied_access',
                "type": 'push',
                'data': {
                    'message': 'You werent invited'
                    }
                }))

    def registerChat(self, event):
        if 'photo_avatar' not in event['user']:
            event['user']['photo_avatar'] = None
        self.send(text_data=json.dumps(
            {"infoType": "chat_registration", "type": "push", "data": {'message': " logged into chat", 'user': event['user'], 'type': 'login', 'avatar': event['user']['photo_avatar']}}
        ))
        print(event['user']['id'])
        user = User.objects.get(id=event['user']['user']['id'])
        try:
            SocketConnections.objects.get_or_create(
                room_group_name=self.room_group_name,
                user=user
            )
        except Exception as e:
            print(e)
        registeredUsers = list(SocketConnections.objects.filter(room_group_name='chat_all')
                               .order_by('-time')
                               .annotate(username=F('user__username'),
                                         name=F('user__employee__full_name'),
                                         position_type=F('user__employee__position_type'),
                                         organization = F('user__employee__organization__name'),
                                         avatar=Concat(V('https://wageup-media.s3.amazonaws.com/'), F('user__profile__photo_avatar')))
                               .values('username', 'name', 'position_type', 'organization', 'time', 'room_group_name', 'avatar', 'user_id'))
        print(dt.datetime.now())
        for u in range(len(registeredUsers)):
            registeredUsers[u]['time'] = dt.datetime.strftime(registeredUsers[u]['time'].astimezone(timezone.utc), '%Y-%m-%d %H:%M')
        print(registeredUsers, 'registered users')
        self.send(text_data=json.dumps(
            {"infoType": "user_registration_list", "type": "push", "data": {'userList': registeredUsers, 'type': 'userList'}}
        ))


    def chatMessage(self, event):
        print('got chat message')


class generalConsumer(WebsocketConsumer):

    http_user = True
    def connect(self, message, **kwargs):
        self.user = message.user
        self.accept()


    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, message):
        event = json.loads(message)
        print("event is ", event)
        print("Incoming request", event["type"], " from ", event['group'])
        self.group_name = event['group']
        async_to_sync(self.channel_layer.send)(self.channel_name, event)


    def push(self, response):
        self.send(json.dumps(response))


    def canChat(self, event):
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        print("RECEIVED AVAILBILITY SIGNAL from child of ", self.group_name)
        print("Sending Pong")



    def ping(self, event):
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        print("RECEIVED PING from child of ", self.group_name)
        print("Sending Pong")
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {"infoType": "ping_pong", "type": "push", "data": {'message': "pong"}}
        )



class DBWriteConsumer(SyncConsumer):

    def update(self, event):
        print("UPDATE SOMETHING...", event)



