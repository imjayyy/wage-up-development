
from rest_framework import serializers
from accounts.serializers import ShortEmployeeSerializer
from training.serializers import ShortModuleOverviewSerializer
from payments.serializers import TremendousCampaignSerializer, ManagerBudgetSerializer
from .models import *

class PPCampaignTransactionlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PPCampaignBankTransactionLog
        fields = '__all__'

class CampaignListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignListItem
        fields = ['id', 'text']

class PPCampaignSerializer(serializers.ModelSerializer):
    registration_requirements = ShortModuleOverviewSerializer(read_only=True, many=True)
    tremendousCampaign = TremendousCampaignSerializer(read_only=True)
    list_items = CampaignListItemSerializer(read_only=True, many=True)

    class Meta:
        model = PPCampaign
        fields = [
            'id',
            'title',
            'description',
            'image',
            'start',
            'end',
            'display_start',
            'display_end',
            'footnotes',
            'confirmation_message',
            'registration_requirements',
            'show_performance_metrics',
            'tremendousCampaign',
            'slug',
            'list_items',
        ]

class PPCampaignDriverMetricTrackingTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = PPCampaignDriverMetricTrackingTable
        fields = '__all__'

class PPRegistrationSerializer(serializers.ModelSerializer):
    campaign = PPCampaignSerializer(read_only=True)
    employee = ShortEmployeeSerializer(read_only=True)
    class Meta:
        model = PPCampaignRegistration
        fields = [
            'id',
            'campaign',
            'employee',
            'registration_date',
            'communication_opt_in'
        ]