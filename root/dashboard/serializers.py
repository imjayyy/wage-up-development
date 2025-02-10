from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *
from django.conf import settings
import datetime as dt
from accounts.serializers import *


# class CustomDashboardApiSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomDashboardApi
#         fields = '__all__'

# class Std12ESerializerComments(serializers.ModelSerializer):
#
#     class Meta:
#         model = Std12ERaw
#         fields = ('sc_dt', 'q30', 'svc_facl_id', 'sc_id', 'driver_name', 'overall_sat')

class Std12ESerializerQuestions(serializers.ModelSerializer):

    class Meta:
        model = RawStd12EQuestions
        fields = '__all__'

# class Std12MSerializerQuestions(serializers.ModelSerializer):
#
#     class Meta:
#         model = RawStd12MQuestions
#         fields = '__all__'

class LinkEmployeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields = ('slug', 'display_name')

class MapsSerializer(serializers.ModelSerializer):

    #TODO: driver_name should be a fk to driver table

    class Meta:
        model = RawOps
        fields = ('ata', 'driver_name', 'pta', 'ata_minus_pta', 'cm_trk', 'tcd', 'bl_long','bl_lat','call_cost',
                  'svc_facl_id', 'sc_dt', 'resolution', 'miles_dest', 'early', 'late', 'on_time', 'check_id_compliant', 're_tm', 'grid_id')

class MapSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Std12EReduced
        fields = ('ata', 'driver_name', 'pta', 'ata_minus_pta', 'cm_trk', 'tcd', 'bl_long','bl_lat','call_cost',
                  'svc_facl_id', 'sc_dt', 'resolution', 'miles_dest', 'early', 'late', 'on_time', 'check_id_compliant', 'sc_id_surveys',
                  're_tm', 'outc1', 'q24', 'q26', 'driver5', 'driver10', 'bl_near_cty_nm', 'grid_id')

# class Std12MSerializer(serializers.ModelSerializer):
#     emp_driver_id = LinkEmployeeSerializer(read_only=True)
#
#     class Meta:
#         model = RawStd12M
#         original_fields = ('sc_dt', 'emp_driver_id', 'sc_id', 'check_id_compliant', 'call_cost',
#                   'call_center_operator', 'cm_trk', 'dispatch_communicated', 'ata', 'pta', 'ata_minus_pta',
#                   're_tm','tcd','Q10aSatOper_Timely','Q10bSatOper_SpokeClearly','Q10cSatOper_NecessaryHelp',
#                   'Q10dSatOper_Courtesy','Q10eSatOper_KnowLocation','Q10fSatOper_KnowPolicy','Q10gSatOper_HelpfulInfo',
#                   'Q10hSatOper_AskRightQues','Q11OverallSatVehDriver','Q12aSatVehDriver_AppearanceOfVehicle',
#                   'Q12bSatVehDriver_AppearanceOfDriver','Q12cSatVehDriver_Greeting','Q12dSatVehDriver_Identification',
#                   'Q12eSatVehDriver_Courtesy','Q12fSatVehDriver_Calming','Q12gSatVehDriver_Communicating',
#                   'Q12hSatVehDriver_KnewCorrectSvc','Q12iSatVehDriver_SvcPromptly','Q12jSatVehDriver_GoingOutOfWay',
#                   'Q13SatTypeOfVehicle','Q15Suggestions_verbatim','Q4OverallSat','Q5NotSatisfied_verbatim','Q6bSatTimeResp',
#                   'Q7bSatAccEstTimeResp','Q8aArrivedWithin15Min','Q8bKeptInformed','Q9OverallSatOper')
#         fields = [field.lower() for field in original_fields]


# class Std12ESerializer(serializers.ModelSerializer):
#     emp_driver_id = LinkEmployeeSerializer(read_only=True)
#
#     class Meta:
#         model = Std12ERaw
#         fields = ('sc_dt', 'emp_driver_id', 'q30', 'driver10', 'driver5', 'desc2', 'q26', 'q24', 'outc1', 'sc_id', 'check_id_compliant', 'call_cost',
#                   'call_center_operator', 'cm_trk', 'dispatch_communicated', 'ata', 'pta', 'ata_minus_pta', 're_tm', 'tcd')


class Std12ECommentsSerializer(serializers.ModelSerializer):
    # survey = Std12ESerializer(read_only=True)

    class Meta:
        model = CommentsSurveysE
        fields = ('tokenized_comment', 'sentiment')


class Std12ECommentsSerializer2(serializers.ModelSerializer):
    class Meta:
        model = CommentsSurveysE
        fields = ('sentiment', 'survey__sc_dt', 'survey__q30', 'survey__svc_facl_id', 'survey__sc_id', 'survey__driver_name')

"""
THIS CODE HAS NOT YET BEEN TESTED. There is probably additional code needed to handle the m2m relationship
with employee in EmployeeDashboard

"""

class EmployeeDashboardElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDashboardElement
        fields = '__all__'

class OwnerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields = ('id', 'display_name')


class EmployeeDashboardSerializer(serializers.ModelSerializer):
    elements = EmployeeDashboardElementSerializer(read_only=True, many=True)
    owner = OwnerSerializer(read_only=True)

    class Meta:
        model = EmployeeDashboard
        fields = '__all__'


# class TimeseriesPredictionsHourlySerializer(serializers.ModelSerializer):
#     calls_per_hour_per_driver = serializers.ReadOnlyField(source='calls_per_hour_per_driver_foo', read_only=True)
#     class Meta:
#         model = TimeseriesPredictionsHourly
#         exclude = ['id', 'date_predicted']

class TimeseriesPredictionsByHourSerializer(serializers.ModelSerializer):
    # calls_per_hour_per_driver = serializers.ReadOnlyField(source='calls_per_hour_per_driver_foo', read_only=True)
    # rollover_drivers = serializers.IntegerField()
    class Meta:
        model = TimeseriesPredictionsByHourNew
        exclude = ['id', 'date_pred']

class TimeseriesScheduleSerializer(serializers.ModelSerializer):
    agg = serializers.IntegerField(allow_null=True)
    class Meta:
        model = TimeseriesSchedule
        exclude = ['id']

class TimeseriesScheduledDriversSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='get_driver_name', read_only=True)
    class Meta:
        model = TimeseriesScheduledDrivers
        fields = ('employee', 'start_date', 'end_date','duration', 'schedule', 'full_name', 'schedule_type', 'placeholder')

class TimeseriesScheduledDiversTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeseriesScheduledDiversTemplate
        fields = '__all__'

class TimeseriesScheduleTemplateSerializer(serializers.ModelSerializer):
    drivers_template = TimeseriesScheduledDiversTemplateSerializer(many=True)
    class Meta:
        model = TimeseriesScheduleTemplate
        fields = ('organization_id', 'drivers_template', 'id')

    def create(self, validated_data):
        print('Inside create serializer', validated_data)
        drivers = validated_data.pop('drivers_template')
        template = TimeseriesScheduleTemplate.objects.create(**validated_data)

        template.save()
        for d in drivers:
            print('driver: ', d)
            TimeseriesScheduledDiversTemplate.objects.create(template=template, **d)
        return template

class TimeseriesExpectationsSerializer(serializers.ModelSerializer):
    drivers = serializers.ReadOnlyField(source='total_drivers', read_only=True)
    calls = serializers.ReadOnlyField(source='total_calls', read_only=True)

    class Meta:
        model = TimeseriesExpectations
        fields = ('date', 'drivers', 'calls')

class SchedulerReviewByDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchedulerReviewByDriver
        fields = ('__all__')
'''

END UNTESTED CODE

'''
