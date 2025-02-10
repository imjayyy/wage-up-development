from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *
from django.conf import settings
import datetime as dt

class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.__class__(value, context=self.context)

        return serializer.data

class ParallelRecursiveField(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class SurveySerializer(serializers.Serializer):
    mtk_satisfaction = serializers.CharField(allow_null=True)
    mtk_recommendation_likelihood = serializers.IntegerField(allow_null=True)
    mtk_job_improvements = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    mtk_usage_frequency = serializers.CharField(allow_null=True)
    mtk_ease_of_use = serializers.CharField(allow_null=True)
    mtk_importance = serializers.CharField(allow_null=True)
    mtk_inspiration = serializers.CharField(allow_null=True)
    mtk_improvement_response = serializers.CharField(allow_blank=True)
    mtk_testimonial = serializers.CharField(allow_blank=True)


class OrganizationSerializer(serializers.ModelSerializer):
    parent = RecursiveField()
    parallel_parents = ParallelRecursiveField(many=True)

    class Meta:
        model = Organization
        fields = '__all__'


class AddOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('name', 'type', 'real_name', 'parent_name',)

class ShortOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id','name', 'type', 'real_name', 'parent', 'parent_name', 'slug')

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmarks
        fields = '__all__'

class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'last_login', 'date_joined',)

class UserSerializer(serializers.ModelSerializer):

    # completedTraining = serializers.PrimaryKeyRelatedField(queryset=UserProgress.objects.all())
    bookmarks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'last_login',
                  'is_superuser', 'date_joined', 'bookmarks')

    def get_bookmarks(self, obj):
        return obj.bookmarks().values('display', 'link', 'id')


class CreateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'is_staff', 'is_active', 'date_joined', 'first_name', 'last_name')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permissions
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'




class ProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('photo_avatar',)


class ProfileBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('banner_pic',)


class AddEmployeeSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    permission = serializers.PrimaryKeyRelatedField(queryset=Permissions.objects.all(), many=True)
    registered_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'organization', 'org_name_help', 'position_type', 'permission', 'slug', 'latest_activity_on', 'registered_by', 'no_match')

class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    permission = PermissionSerializer(read_only=True, many=True)
    parallel_organizations = ShortOrganizationSerializer(read_only=True, many=True)

    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'user', 'organization', 'position_type', 'permission', 'slug', 'data_name', 'parallel_organizations', 'login_id', 'no_match', 'unverified_email',  'active', 'group')

class EmployeeProfileEntriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfileEntries
        exclude = ['driver_profile']

class EmployeeProfileSerializer(serializers.ModelSerializer):
    employee_profile_entries = EmployeeProfileEntriesSerializer(many=True)
    class Meta:
        model = EmployeeProfile
        fields = ['id', 'employee', 'trouble_code_type', 'active', 'employee_profile_entries', 'active_not_available']

    def create(self, validated_data):
        entries = validated_data.pop('employee_profile_entries')
        profile = EmployeeProfile.objects.create(**validated_data)
        for entry in entries:
            EmployeeProfileEntries.objects.create(driver_profile=profile, **entry)
        return profile


class EmployeeProfileAllSerializer(serializers.ModelSerializer):
    employee_profile = EmployeeProfileSerializer(many=True, read_only=True)
    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'user', 'position_type', 'active', 'employee_profile')

class EmployeeProfileEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'user', 'position_type', 'active')

class ApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRequests
        fields = '__all__'

class ApprovalRequestEmployeeTimeOffSerializer(serializers.ModelSerializer):
    request_data = ApprovalRequestSerializer()
    class Meta:
        model = ApprovalRequestEmployeeTimeOff
        fields = '__all__'

class ApprovalRequestEmployeeAvailabilitySerializer(serializers.ModelSerializer):
    request_data = ApprovalRequestSerializer()
    class Meta:
        model = ApprovalRequestEmployeeAvailability
        fields = '__all__'

class ApprovalRequestAppealsSerializer(serializers.ModelSerializer):
    request_data = ApprovalRequestSerializer()
    class Meta:
        model = ApprovalRequestAppeals
        fields = '__all__'


class EmployeeProfileOptimizedSerializer(serializers.ModelSerializer):
    employee = EmployeeProfileEmployeeSerializer()
    employee_profile_entries = EmployeeProfileEntriesSerializer(many=True)
    class Meta:
        model = EmployeeProfile
        fields = ['id', 'employee', 'trouble_code_type', 'active', 'employee_profile_entries']

    def create(self, validated_data):
        entries = validated_data.pop('employee_profile_entries')
        profile = EmployeeProfile.objects.create(**validated_data)
        for entry in entries:
            EmployeeProfileEntries.objects.create(driver_profile=profile, **entry)
        return profile

class TinyEmployeeSerializer(serializers.ModelSerializer):
    organization = ShortOrganizationSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name',
                  'user', 'position_type',
                  'active', 'full_name', 'display_name', 'organization')


class ShortEmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'user', 'position_type', 'permission', 'login_id', 'unverified_email', 'active', 'full_name')

class SimpleEmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    organization = ShortOrganizationSerializer(read_only=True)
    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name','position_type', 'permission', 'login_id', 'unverified_email', 'full_name', 'user', 'organization')


class CommentEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ('id', 'full_name')

class InviteSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Invite
        fields = '__all__'


class CreateInviteSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Invite
        fields = '__all__'


class ActionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActionDetails
        fields = '__all__'


class RecentActionsSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer(read_only=True)
    details = ActionDetailSerializer(read_only=True, many=True)

    class Meta:
        model = UserActions
        fields = '__all__'

class ScheduleOpenAvailabilitySerializer(serializers.ModelSerializer):
    potential_drivers = EmployeeProfileAllSerializer(many=True)
    drivers_available = EmployeeProfileAllSerializer(many=True)
    drivers_rejected = EmployeeProfileAllSerializer(many=True)
    drivers_accepted = EmployeeProfileAllSerializer(many=True)

    class Meta:
        model = ScheduleOpenAvailability
        fields = '__all__'

