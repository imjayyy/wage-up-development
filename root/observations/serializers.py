from rest_framework import serializers
# from rest_framework_recursive.fields import RecursiveField
from django.contrib.auth.models import User
from .models import *
from django.conf import settings
import datetime as dt
from accounts.serializers import UserSerializer
from accounts.models import EmployeeGroup
from accounts.serializers import *

class RecursiveReplies(serializers.Serializer):
    def to_representation(self, value):
        serialize = self.parent.parent.__class__(value, context=self.context)
        return serialize.data

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topics
        fields = ('__all__')

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeGroup
        fields = ('__all__')

class ReplyCommentsSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='user_full_name', read_only=True)
    organization_name = serializers.CharField(source='get_org_name', read_only=True)
    total_likes = serializers.IntegerField(source='comment_likes_count', read_only=True)
    # comment_replies = RecursiveReplies()

    class Meta:
        model = Comments
        fields = ('__all__')


class CommentsDataSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='user_full_name', read_only=True)
    organization_name = serializers.CharField(source='get_org_name', read_only=True)
    total_likes = serializers.IntegerField(source='comment_likes_count', read_only=True)
    comment_replies = RecursiveReplies(many=True, read_only=True, source='comment_parent')
    mentions = ShortEmployeeSerializer(many=True, read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    groups = GroupSerializer(many=True, read_only=True)
    avatar = serializers.FileField(source='employee_avatar', read_only=True)
    class Meta:
        model = Comments
        fields = ('__all__')

# CommentsDataSerializer.base_fields['comment_replies'] = CommentsDataSerializer()
    # def get_fields(self):
    #     fields = super(CommentsDataSerializer, self).get_fields()
    #     fields['comment_replies'] = CommentsDataSerializer(many=True)
    #     return fields
    #
    # @staticmethod
    # def get_replies(self, obj):
    #     comment_replies = Comments.objects.filter(reply_to=obj.id)
    #     serializer = CommentsDataSerializer(comment_replies, many=True)
    #     return serializer.data

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriptions
        fields = ('__all__')
        depth = 1
