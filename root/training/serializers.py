from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *
from accounts.serializers import UserSerializer, EmployeeSerializer
from performance_points.models import PPCampaign
from django.conf import settings
import datetime as dt

class UpdateUserProgress(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = ('__all__')

    def update(self, instance, validated_data):
        instance.correct_questions = validated_data['correct_questions']
        instance.incorrect_questions = validated_data['incorrect_questions']
        instance.passed = validated_data['passed']
        instance.final_grade = validated_data['final_grade']
        instance.last_event = validated_data['last_event']
        instance.save()
        return instance

class MultipleChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleMultipleChoice
        fields = ('question', 'answer_one', 'answer_two', 'answer_three', 'answer_four', 'answer_five', 'correct_answer', 'answer_explanation')

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleMultipleChoice
        fields = ('__all__')

class ModuleFlowSerializer(serializers.ModelSerializer):
    multiple_choice = MultipleChoiceSerializer(read_only=True)
    class Meta:
        model = ModuleFlow
        fields = ('__all__')


class UserProgressSerializer(serializers.ModelSerializer):
    last_event = ModuleFlowSerializer(read_only=True)
    user = UserSerializer()
    employee = serializers.ReadOnlyField(source='get_organization', read_only=True)
    class Meta:
        model = UserProgress
        fields = ('__all__')

class UserDocumentCatSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDocumentCategory
        fields = ('__all__')

class UserDocumentSerializer(serializers.ModelSerializer):
    category = UserDocumentCatSerializer()
    class Meta:
        model = UserDocument
        fields = ('__all__')

class DocumentSerializer(serializers.Serializer):
    file = serializers.FileField()

class TrainingVideoQuestionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingViedoQuestionAnswer
        fields = ('__all__')

class TrainingVideoQuestionSerializer(serializers.ModelSerializer):
    possible_answer = TrainingVideoQuestionAnswerSerializer(many=True)

    class Meta:
        model = TrainingVideoQuestion
        fields = ['video_ref', 'question', 'possible_answer']

    def create(self, validated_data):
        answers = validated_data.pop('possible_answer')
        question = TrainingVideoQuestion.objects.create(**validated_data)
        for a in answers:
            TrainingViedoQuestionAnswer.objects.create(question=question, **a)
        question.save()
        return question

class TrainingVideoSerializer(serializers.ModelSerializer):
    follow_up_questions = TrainingVideoQuestionSerializer(source='video_reference', many=True)

    class Meta:
        model = TrainingVideo
        fields = ['id', 'name', 'video_url', 'display_start', 'display_end', 'follow_up_questions']

class CampaignImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PPCampaign
        fields = ['id', 'image']


class QuestionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionsAnswer
        fields = ('__all__')

class ModuleQuestionSerializer(serializers.ModelSerializer):
    answers = QuestionAnswerSerializer(many=True)

    class Meta:
        model = ModuleQuestion
        fields = ['id', 'question', 'answers']

class ModulePageSerializer(serializers.ModelSerializer):
    page_questions = ModuleQuestionSerializer(many=True)
    class Meta:
        model = ModulePage
        fields = ('__all__')

# class ModuleTagSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ModuleTag
#         fields = ('__all__')

class ModuleCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleCompletion
        fields = ('__all__')


class ModuleOverviewSerializer(serializers.ModelSerializer):
    overview_pages = ModulePageSerializer(many=True)
    # tags = ModuleTagSerializer(many=True)
    module_completion = ModuleCompletionSerializer(many=True)
    class Meta:
        model = ModuleOverview
        fields = ['id', 'title', 'description', 'overview_pages', 'module_completion', 'active', 'campaign']



class ShortModuleOverviewSerializer(serializers.ModelSerializer):
    # tags = ModuleTagSerializer(many=True)

    class Meta:
        model = ModuleOverview
        fields = ['id', 'title', 'description']



class CampaignSerializer(serializers.ModelSerializer):
    registration_requirements = ModuleOverviewSerializer(many=True)
    created_by = EmployeeSerializer()

    class Meta:
        model = PPCampaign
        fields = ['id', 'title', 'start', 'end', 'active', 'registration_requirements', 'geography_eligiblity', 'registration_eligibility', 'created_by', 'description', 'image']