
from rest_framework import serializers
from training.serializers import ShortModuleOverviewSerializer
from .models import *
from accounts.serializers import TinyEmployeeSerializer



class ManagerBudgetSerializer(serializers.ModelSerializer):
    manager = TinyEmployeeSerializer()

    class Meta:
        model = ManagerBudget
        fields = ('amount', 'manager')

class TremendousCampaignSerializer(serializers.ModelSerializer):
    manager_budget_tremendous_campaign = ManagerBudgetSerializer(many=True)
    class Meta:
        model = TremendousCampaign
        fields =('name', 'total_budget', 'manager_budget_tremendous_campaign')


class PaymentLogSerializer(serializers.ModelSerializer):
    payment_from = TinyEmployeeSerializer()
    payment_to = TinyEmployeeSerializer()
    approved_by = TinyEmployeeSerializer()
    tremendous_campaign = TremendousCampaignSerializer()

    class Meta:
        model = PaymentLog
        fields = ('created_on', 'id', 'payment_method', 'payment_to',
                  'payment_from', 'payment_amount', 'tremendous_campaign',
                  'notes', 'reason', 'reward_id', 'reward_status', 'email_used',
                  'approved', 'approved_by', 'rejection_reason')

class WingspanUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = WingSpanUserEmployee
        fields = '__all__'