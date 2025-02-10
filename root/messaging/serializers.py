from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *
from django.conf import settings
import datetime as dt
from accounts.models import Employee, Profile
from accounts.serializers import UserSerializer
from accounts.serializers import *

class TriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerMessages
        fields = ('__all__')

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledMessages
        fields = ('__all__')

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcements
        fields = ('__all__')

class EmailDataSerializer(serializers.ModelSerializer):
    trigger_email_data = TriggerSerializer(read_only=True, many=True)
    schedule_email_data = ScheduleSerializer(read_only=True, many=True)
    recipients = UserSerializer(read_only=True, many=True)
    author = UserSerializer(read_only=True)
    class Meta:
        model = EmailData
        fields = ('__all__')


class MTKMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MTKMessage
        fields = [
            'id',
            'pp_campaign',
            'inbox_message_title',
            'inbox_message_text',
            'banner_text',
            'button_text',
            'registered_only',
            'active',
            'hierarchy',
            'type',
            'external_link',
            'internal_link',
        ]

class InvitedUserEmployeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields = ('full_name', 'position_type', 'display_name')

class PhotoAvatarSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = ('photo_avatar',)

class ChatMessageUserSerializer(serializers.ModelSerializer):
    employee = InvitedUserEmployeeSerializer(read_only=True)
    # profile = PhotoAvatarSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('username', 'id', 'employee', 'profile')

class ChatMessageSerializer(serializers.ModelSerializer):
    from_user = ChatMessageUserSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = ('__all__')

class ChatGroupSerializer(serializers.ModelSerializer):
    invited_users = ChatMessageUserSerializer(read_only=True, many=True)

    class Meta:
        model = ChatGroup
        fields = ('__all__')
