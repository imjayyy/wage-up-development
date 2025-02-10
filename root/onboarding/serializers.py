from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *
from django.conf import settings
import datetime as dt
from accounts.serializers import UserSerializer
from dashboard.models import *


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ('__all__')

class RecursiveDocument(serializers.ModelSerializer):

    class Meta:
        model = Documentation
        fields = ['element', 'id']

class RecursiveCategory(serializers.ModelSerializer):
    class Meta:
        model = MetricCategories
        fields = ('__all__')

class MetricCategoriesSerializer(serializers.ModelSerializer):
    parent = RecursiveCategory(read_only=True)
    class Meta:
        model = MetricCategories
        fields = ('__all__')

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documentation
        fields = ('element', 'element_type', 'html_content', 'formatted_name')

class DocumentSerializer(serializers.ModelSerializer):
    category = MetricCategoriesSerializer()
    class Meta:
        model = Documentation
        fields = ('__all__')

class ChartTypeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documentation
        fields = ('__all__')

class PageDocumentSerializer(serializers.ModelSerializer):
    faq = FAQSerializer(read_only=True, many=True)
    class Meta:
        model = Documentation
        fields = ('__all__')


class MetricGoalSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(read_only=True)
    metric = DocumentSerializer()
    class Meta:
        model = MetricGoals
        fields = ('__all__')

class DemoContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoContent
        fields = ('__all__')

class DemoPageSerializer(serializers.ModelSerializer):
    content = DemoContentSerializer(many=True)
    class Meta:
        model = DemoPage
        fields = ('__all__')

class UserDemoHistorySerializer(serializers.ModelSerializer):
    page = DemoPageSerializer()
    class Meta:
        model = UserDemoHistory
        fields = ("page", "id")

class EnhancementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enhancements
        fields = ("__all__")

class DeploymentsSerializer(serializers.ModelSerializer):
    enhancements = EnhancementSerializer(many=True)
    class Meta:
        model = Deployments
        fields = ("__all__")
