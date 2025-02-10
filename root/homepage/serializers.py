from rest_framework import serializers
# from rest_framework_recursive.fields import RecursiveField
from django.contrib.auth.models import User
from .models import *
from accounts.serializers import *

# class WidgetContentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = WidgetContent
#         fields = ('__all__')

class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ('__all__')

class WidgetModalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetModalContent
        fields = ('__all__')

class WidgetDataSerializer(serializers.ModelSerializer):
    widget = WidgetSerializer()
    modal_content = WidgetModalContentSerializer(many=True)
    class Meta:
        model = WidgetData
        fields = ('__all__')


class WidgetImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetData
        fields = ('image', 'id')

class WidgetFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetData
        fields = ('file', 'id')

class WidgetModalFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetModalContent
        fields = ('id', 'file', 'text', 'url_text', 'is_file')
