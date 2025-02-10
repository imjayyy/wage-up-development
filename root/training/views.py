from django.shortcuts import render
import sys
sys.path.insert(0, 'root')
from django.http.response import HttpResponse, FileResponse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from .serializers import *
from accounts.models import *
from arena.models import *
from .models import *
from arena.serializers import HH5Serializer, HH5DriverSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F


class Training(generics.GenericAPIView):
    """
        Take as post input:
        :type - i.e. driver, employee, market, grid etc.
        slug - what is the slug of the object. i.e. devin-gonier, vadc
        purpose - what function should be called -- i.e. line_graph, scatterplot etc.
    """

    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'
    #
    # def get_authenticate_header(self, request):
    #     return '{0} realm="{1}"'.format(
    #         AUTH_HEADER_TYPES[0],
    #         self.www_authenticate_realm,
    #     )

    def __init__(self):
        self.purpose_router = {
            'get_modules': self.get_modules,
            'next_event': self.next_event,
            'update_user_progress': self.update_user_progress,
            'get_events': self.get_events,
            'get_documents': self.get_documents,
            'questions': self.questions,
            'campaign_user_list': self.campaign_user_list,
            'get_campaign_module': self.get_campaign_module,
            'user_campaign_completion': self.user_campaign_completion,
            'create_shout_out': self.create_shout_out,
            'shout_out_list': self.shout_out_list
        }

    def post(self, request, *args, **kwargs):
        data = request.data
        self.user = self.request.user
        output = self.purpose_router[data['purpose']](data['parameters'])

        return Response(output, status=status.HTTP_200_OK)

    def create_shout_out(self, params):
        shout_out_driver = params.get('driver', {})
        shout_out_station = params.get('station', None)
        shout_out_quote = params.get('quote', None)
        new_shout_out = ShoutOut.objects.create(
            driver=shout_out_driver,
            station=shout_out_station,
            quote=shout_out_quote,
        )
        output = ShoutOutSerializer(new_shout_out).data
        return output

    def set_shout_out_image(self, params):
        image = self.data['image']
        shout_out = ShoutOut.objects.get(id=self.data['id'])
        shout_out_serializer = ShoutOutImageSerializer(shout_out, data={'image': image}, partial=True)
        if shout_out_serializer.is_valid():
            shout_out_serializer.save()
            output = ShoutOutSerializer(ShoutOut.objects.get(id=self.data['id'])).data
        else:
            output = {'image_saved': False}
        return output


    def shout_out_list(self, params):
        shout_outs = ShoutOut.objects.all()
        shout_outs = ShoutOutSerializer(shout_outs, many=True).data
        return shout_outs

    def get_modules(self, parameters):
        modules = ModuleOverview.objects.all()

        module_counts = {}
        for module in modules:
            module_counts[module.id] = module.get_event_count()

        modules = list(modules.values())

        user_histories = UserProgress.objects.filter(user=self.user)
        serializer = UserProgressSerializer(user_histories, many=True)
        user_histories = serializer.data

        print(user_histories)

        output = []
        for module in modules:
            module['event_count'] = module_counts[module['id']]
            for user_history in user_histories:
                print(user_history)
                if user_history['module'] == module['id']:
                    module['user_history'] = user_history
            output.append(module)
        return output

    def campaign_user_list(self, parameters):
        campaign = ModuleOverview.objects.get(id=parameters['campaign_id'])
        progress = UserProgress.objects.get_or_create(user=self.user, module=campaign)[0]
        user_list = UserProgress.objects.filter(module=campaign, passed=True)
        completed = False
        if progress.passed is True:
            completed = True
        user_list = UserProgressSerializer(user_list, many=True).data
        output = {'completed': completed, 'user_list': user_list}
        return output

    def get_campaign_module(self, parameters):
        campaign = ModuleOverview.objects.get(id=parameters['campaign_id'])
        questions = ModuleMultipleChoice.objects.filter(module=campaign)
        progress = UserProgress.objects.get_or_create(user=self.user, module=campaign)[0]

        questions = MultipleChoiceSerializer(questions, many=True).data
        output = {'all_questions': questions, 'user_progress_id': progress.id}
        return output

    def user_campaign_completion(self, parameters):
        module = ModuleOverview.objects.get(id=parameters['campaign_id'])
        campaign = Campaign.objects.get(module=module)
        if parameters['email'] != self.user.email:
            email = parameters['email']
        else:
            email = self.user.email
        user_campaign = CampaignUser.objects.create(user=self.user, campaign=campaign, reward=parameters['reward'], email=email)
        progress = UserProgress.objects.get(id=parameters['progress_id'])
        progress.passed = True
        progress.updated = dt.datetime.now()
        progress.save()

        completion_list = UserProgress.objects.filter(module=module, passed=True)
        output = UserProgressSerializer(completion_list, many=True).data
        return output

    def get_events(self, parameters):
        output = ModuleFlow.objects.filter(module=parameters['module_id'])
        serializer = ModuleFlowSerializer(output, many=True)
        return serializer.data

    def next_event(self, parameters):
        next_event_id = parameters['current_event'] + 1
        output = ModuleFlow.objects.filter(module=parameters['module_id'], event_order = next_event_id).values()
        return output

    def check_multiple_choice(self, selection, multiple_choice_object):
        if multiple_choice_object.correct_answer == selection:
            return True
        else:
            return False

    def resolve_current_state(self, current_state, value):
        if value in current_state:
            if current_state[value] is not None:
                return current_state[value]
            else:
                return 0
        else:
            return 0

    def update_user_progress(self, parameters):

        event = ModuleFlow.objects.get(module=parameters['module_id'], event_order=parameters['event_order'])
        try:
            current_state_obj = UserProgress.objects.filter(module=parameters['module_id'], user=self.user).order_by('-last_event')
            current_state = list(current_state_obj.values())[0]
            current_state_obj = current_state_obj[0]
            if current_state_obj.last_event == event:
                return "This event has already been processed!, please call next event or reset"
            if 'reset' in parameters:
                current_state_obj.delete()
                return "current state for this module was deleted. You can start over now!"
        except IndexError:
            current_state = {}
            current_state_obj = False
        # check to see if this is actually a new event or not by
        # checking current state latest to event id and see if they are the same


        print(current_state)
        update_data = {
            'correct_questions': self.resolve_current_state(current_state, 'correct_questions'),
            'incorrect_questions': self.resolve_current_state(current_state, 'incorrect_questions'),
            'passed': self.resolve_current_state(current_state, 'passed'),
            'final_grade': self.resolve_current_state(current_state, 'final_grade'),
            'module': parameters['module_id'],
            'last_event': event.id,
            'updated': dt.datetime.now(),
            'user': self.user.id
        }
        if event.event_type == 'multiple_choice':
            print("multiple choice question!")
            correct = self.check_multiple_choice(parameters['selection'], event.multiple_choice)
            if correct:
                update_data['correct_questions'] += 1
            else:
                update_data['incorrect_questions'] += 1

            total_questions_answered = update_data['correct_questions'] + update_data['incorrect_questions']

            module_metadata = ModuleOverview.objects.get(id=parameters['module_id'])
            if total_questions_answered == module_metadata.question_count:
                final_grade = update_data['correct_questions'] / total_questions_answered
                if final_grade >= module_metadata.pass_threshold:
                    update_data['passed'] = True
                else:
                    update_data['passed'] = False
                update_data['final_grade'] = final_grade
        print(update_data)

        if not current_state_obj:
            serializer = UpdateUserProgress(data=update_data)
            if serializer.is_valid():
                serializer.save()
                return serializer.data
            else:
                return serializer.errors
        else:
            current_state_obj.correct_questions = update_data['correct_questions']
            current_state_obj.incorrect_questions = update_data['incorrect_questions']
            current_state_obj.passed = update_data['passed']
            current_state_obj.final_grade = update_data['final_grade']
            current_state_obj.last_event = event
            current_state_obj.updated = dt.datetime.now()
            current_state_obj.save()
            return update_data

    def get_documents(self, parameters):
        documents = UserDocument.objects.filter(active=True).order_by('doc_name')
        output = UserDocumentSerializer(documents, many=True)
        return output.data

    def questions(self, parameters):
        action = parameters['action']
        if action == 'new_video':
            video_details = parameters['video_details']
            video_questions = parameters['questions']
            if video_details['date_range'] is not None:
                start_date = video_details['date_range']['start']
                end_date = video_details['date_range']['end']
            else:
                start_date = None
                end_date = None
            video = TrainingVideo.objects.create(
                name=video_details['name'],
                video_url=video_details['video_url'],
                display_start=start_date,
                display_end=end_date
            )
            video.save()
            for q in video_questions:
                q['video_ref'] = video.id
                question = TrainingVideoQuestionSerializer(data=q)
                if question.is_valid():
                    question.save()
                else:
                    print(question.errors)

            output = TrainingVideoSerializer(video).data
        elif action == 'edits':
            action_type = parameters['action_type']
            video = TrainingVideo.objects.get(pk=parameters['video_id'])
            if action_type == 'edit_video':
                pass
            elif action_type == 'add_question':
                new_questions = parameters['new_questions']
                old_questions = parameters['old_questions']
        else:
            videos = TrainingVideo.objects.all()
            output = TrainingVideoSerializer(videos, many=True).data

        return output

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_user_employee(request):
    print('get_user_id', request.GET)
    try:
        user_id = request.GET['user_id']
        try:
            user = User.objects.get(pk=user_id)
            employee = Employee.objects.get(user=user)
        except:
            employee = Employee.objects.get(id=user_id)
            user = None

        if employee:
            user_id = employee.user.id
            user = employee.user
            employee_id = employee.id
        else:
            employee_id = None

        if employee or user:
            if user:
                email = user.email
            else:
                email = None
            return Response({'is_good': True, 'employee': employee_id, 'user_id': user_id, 'user_email': email}, status=status.HTTP_200_OK)
        else:
            return Response({'is_good': False}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({'is_good': False}, status=status.HTTP_400_BAD_REQUEST)

# POST USER LIST
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def campaign_user_list(request):
    print(request.data)
    params = request.data['parameters']
    user = User.objects.get(pk=params['user_id'])
    campaign = ModuleOverview.objects.get(id=params['campaign_id'])
    progress = UserProgress.objects.get_or_create(user=user, module=campaign)[0]


    conf_count = hh5_drivers_sat_statistics.objects.filter(registered=True)
    registered_count = UserProgress.objects.filter(module=campaign,
                                                   user_id__in=[x for x in Employee.objects.filter(id__in=conf_count.values_list('employee_id', flat=True)).values_list('user_id', flat=True) ])
    print('confirm vs registerd count:', conf_count.count(), registered_count.count())
    if conf_count.count() > registered_count.count():
        employee_list = Employee.objects.filter(id__in=conf_count.values_list('employee_id', flat=True)).values_list('user_id', flat=True)
        reg_emp_list = Employee.objects.filter(user_id__in=registered_count.values_list('user_id', flat=True)).values_list('user_id', flat=True)
        for e in employee_list:
            if e not in reg_emp_list:
                UserProgress.objects.update_or_create(user_id=e, module=campaign, passed=True, updated=dt.datetime.now())
    # user_list = UserProgress.objects.filter(module=campaign, passed=True)
    completed = False
    emp = Employee.objects.get(user_id=user.id)
    org = Organization.objects.get(id=emp.organization.id)
    if org.id !=7:
        stations = Organization.objects.filter(id__in=org.lineage('Station')).values_list('name', flat=True)
    else:
        stations = Organization.objects.filter(type='Station').values_list('name', flat=True)
    print('got stations')
    if emp.position_type == 'Driver':
        reg_list = None
        emp_id = emp.id
        try:
            dd = hh5_drivers_sat_statistics.objects.get(employee_id=emp_id)
            # driver_details = {'employee_id': dd.employee_id,
            #                   'tech_id': dd.tech_id,
            #                   'station_name': dd.station_name,
            #                   'registered': dd.registered,
            #                   'id_name_helper': dd.id_name_helper,
            #                   'call_volume': dd.call_volume,
            #                   'count_overall_totly_stsfd': dd.count_overall_totly_stsfd,
            #                   'count_driver_totly_stsfd': dd.count_driver_totly_stsfd}
            driver_details = HH5Serializer(dd).data
        except:
            dd = hh5_drivers.objects.get(employee_id=emp_id)
            driver_details = HH5DriverSerializer(dd).data
        user_list = None
        reg_list_count = None
    else:
        driver_details = None
        reg_list = hh5_drivers_sat_statistics.objects.filter(station_name__in=stations).exclude(id_name_helper=None).order_by('id_name_helper')
        print('getting reg list')
        reg_list_count = reg_list.count()
        reg_list = reg_list[0:100]
        reg_list = reg_list.annotate(
            territory=F('employee__organization__parent__name'),
            username=F('employee__user__username'),
            registration_group=F('employee__hh5_driver_employee__registration_group'),
            cohort=F('employee__hh5_driver_employee__hh5_station_cohort'),
            g1_base=F('employee__hh5_employee_sat_ext__g1_base_size'),
            g1_count=F('employee__hh5_employee_sat_ext__g1_count'),
            g1_pcnt=F('employee__hh5_employee_sat_ext__g1_pcnt'),
            g2_base=F('employee__hh5_employee_sat_ext__g2_base_size'),
            g2_count=F('employee__hh5_employee_sat_ext__g2_count'),
            g2_pcnt=F('employee__hh5_employee_sat_ext__g2_pcnt'),
            g3_base=F('employee__hh5_employee_sat_ext__g3_base_size'),
            g3_count=F('employee__hh5_employee_sat_ext__g3_count'),
            g3_pcnt=F('employee__hh5_employee_sat_ext__g3_pcnt'),
            g4_base=F('employee__hh5_employee_sat_ext__g4_base_size'),
            g4_count=F('employee__hh5_employee_sat_ext__g4_count'),
            g4_pcnt=F('employee__hh5_employee_sat_ext__g4_pcnt'),
            dec_group_base=F('employee__hh5_employee_sat_ext__dec_group_base'),
            dec_group_count=F('employee__hh5_employee_sat_ext__dec_group_count'),
        ).values('id',
                 'employee_id',
                 'id_name_helper',
                 'territory',
                 'station_name',
                 'username',
                 'registration_group',
                 'cohort',
                 'call_volume',
                 'base_size_sat_overall',
                 'count_overall_totly_stsfd',
                 'count_driver_totly_stsfd',
                 'pcnt_overall_totly_stsfd',
                 'base_size_driver',
                 'pcnt_driver_totly_stsfd',
                 'g1_base',
                 'g1_count',
                 'g1_pcnt',
                 'g2_base',
                 'g2_count',
                 'g2_pcnt',
                 'g3_base',
                 'g3_count',
                 'g3_pcnt',
                 'g4_base',
                 'g4_count',
                 'g4_pcnt',
                 'dec_group_base',
                 'dec_group_count',
                 'registered')
        user_list = hh5_drivers.objects.filter(registered=1, org__name__in=stations)
        # user_list = hh5_drivers.objects.filter(registered=1)
        print('hh5 driver serializer')
        user_list = user_list.annotate(territory=F('employee__organization__parent__name')).values(
            'id',
            'employee_id',
            'driver_name',
            'org_id',
            'station_name',
            'email',
            'date_joined',
            'username',
            'registration_time',
            'registered',
            'registered_email',
            'reward_type',
            'registration_group',
            'hh5_station_cohort',
            'territory'
        )
        # user_list = HH5DriverSerializer(user_list, many=True).data
        # u_list = Employee.objects.filter(id__in=org_list).values_list('user_id', flat=True)
        # user_list = UserProgress.objects.filter(module=campaign, passed=True, user_id__in=u_list)

    if progress.passed is True:
        completed = True
    print('filtering hh5 drivers')

    # user_list = UserProgressSerializer(user_list, many=True).data
    output = {'completed': completed, 'user_list': user_list, 'register_list': reg_list, 'driver_details': driver_details, 'total_registered': reg_list_count}
    return Response(output, status=status.HTTP_200_OK)

# POST to get questions
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def get_campaign_module(request):
    params = request.data['parameters']
    user = User.objects.get(pk=params['user_id'])
    campaign = ModuleOverview.objects.get(id=params['campaign_id'])
    questions = ModuleMultipleChoice.objects.filter(module=campaign)
    progress = UserProgress.objects.get_or_create(user=user, module=campaign)[0]

    questions = MultipleChoiceSerializer(questions, many=True).data
    output = {'all_questions': questions, 'user_progress_id': progress.id}
    return Response(output, status=status.HTTP_200_OK)

# POST to register after completion
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def user_campaign_completion(request):
    params = request.data['parameters']
    user = User.objects.get(pk=params['user_id'])
    employee = Employee.objects.get(user=user)
    module = ModuleOverview.objects.get(id=params['campaign_id'])
    campaign = Campaign.objects.get(module=module)
    if params['email'] != user.email:
        email = params['email']
    else:
        email = user.email
    user_campaign = CampaignUser.objects.create(user=user, campaign=campaign, reward=params['reward'],
                                                email=email, employee=employee)
    progress = UserProgress.objects.get(id=params['progress_id'])
    progress.passed = True
    progress.updated = dt.datetime.now()
    progress.save()
    try:
        dd = hh5_drivers_sat_statistics.objects.get(employee_id=employee.id)
        # driver_details = {'employee_id': dd.employee_id,
        #                   'tech_id': dd.tech_id,
        #                   'station_name': dd.station_name,
        #                   'registered': dd.registered,
        #                   'id_name_helper': dd.id_name_helper,
        #                   'call_volume': dd.call_volume,
        #                   'count_overall_totly_stsfd': dd.count_overall_totly_stsfd,
        #                   'count_driver_totly_stsfd': dd.count_driver_totly_stsfd}
        driver_details = HH5Serializer(dd).data
    except:
        dd = hh5_drivers.objects.get(employee_id=employee.id)
        # driver_details = {'employee_id': dd.employee_id,
        #                   'tech_id': dd.tech_id,
        #                   'station_name': dd.station_name,
        #                   'registered': dd.registered,
        #                   'id_name_helper': dd.id_name_helper,
        #                   'call_volume': dd.call_volume,
        #                   'count_overall_totly_stsfd': dd.count_overall_totly_stsfd,
        #                   'count_driver_totly_stsfd': dd.count_driver_totly_stsfd}
        driver_details = HH5DriverSerializer(dd).data
    # driver = hh5_drivers.objects.get(employee_id=employee.id)
    # driver.email_campaign_invite_using_registration_email()

    # completion_list = UserProgress.objects.filter(module=module, passed=True)
    # output = UserProgressSerializer(completion_list, many=True).data
    return Response(driver_details, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def get_hh5_stats(request):
    params = request.data['parameters']
    all_stats = params['complete_list']
    user = User.objects.get(pk=params['user_id'])
    emp = Employee.objects.get(user_id=user.id)
    org = Organization.objects.get(id=emp.organization.id)
    if org.id !=7:
        stations = Organization.objects.filter(id__in=org.lineage('Station')).values_list('name', flat=True)
    else:
        stations = Organization.objects.filter(type='Station').values_list('name', flat=True)
    reg_list = hh5_drivers_sat_statistics.objects.filter(station_name__in=stations).exclude(
        id_name_helper=None).order_by('id_name_helper')
    print('getting reg list')
    if all_stats is False:
        lower = params['lower']
        upper = params['upper']
        reg_list = reg_list[lower:upper]

    reg_list = reg_list.annotate(
        territory=F('employee__organization__parent__name'),
        username=F('employee__user__username'),
        registration_group=F('employee__hh5_driver_employee__registration_group'),
        cohort=F('employee__hh5_driver_employee__hh5_station_cohort'),
        g1_base=F('employee__hh5_employee_sat_ext__g1_base_size'),
        g1_count=F('employee__hh5_employee_sat_ext__g1_count'),
        g1_pcnt=F('employee__hh5_employee_sat_ext__g1_pcnt'),
        g2_base=F('employee__hh5_employee_sat_ext__g2_base_size'),
        g2_count=F('employee__hh5_employee_sat_ext__g2_count'),
        g2_pcnt=F('employee__hh5_employee_sat_ext__g2_pcnt'),
        g3_base=F('employee__hh5_employee_sat_ext__g3_base_size'),
        g3_count=F('employee__hh5_employee_sat_ext__g3_count'),
        g3_pcnt=F('employee__hh5_employee_sat_ext__g3_pcnt'),
        g4_base=F('employee__hh5_employee_sat_ext__g4_base_size'),
        g4_count=F('employee__hh5_employee_sat_ext__g4_count'),
        g4_pcnt=F('employee__hh5_employee_sat_ext__g4_pcnt'),
        dec_group_base=F('employee__hh5_employee_sat_ext__dec_group_base'),
        dec_group_count=F('employee__hh5_employee_sat_ext__dec_group_count'),
    ).values('id',
             'employee_id',
             'id_name_helper',
             'territory',
             'station_name',
             'username',
             'registration_group',
             'cohort',
             'call_volume',
             'base_size_sat_overall',
             'count_overall_totly_stsfd',
             'count_driver_totly_stsfd',
             'pcnt_overall_totly_stsfd',
             'base_size_driver',
             'pcnt_driver_totly_stsfd',
             'g1_base',
             'g1_count',
             'g1_pcnt',
             'g2_base',
             'g2_count',
             'g2_pcnt',
             'g3_base',
             'g3_count',
             'g3_pcnt',
             'g4_base',
             'g4_count',
             'g4_pcnt',
              'dec_group_base',
             'dec_group_count',
             'registered')
    # user_list = hh5_drivers.objects.filter(registered=1, org__name__in=stations)
    # # user_list = hh5_drivers.objects.filter(registered=1)
    # print('hh5 driver serializer')
    # user_list = user_list.annotate(territory=F('employee__organization__parent__name')).values(
    #     'id',
    #     'employee_id',
    #     'driver_name',
    #     'org_id',
    #     'station_name',
    #     'email',
    #     'date_joined',
    #     'username',
    #     'registration_time',
    #     'registered',
    #     'registered_email',
    #     'reward_type',
    #     'registration_group',
    #     'hh5_station_cohort',
    #     'territory'
    # )
    return Response(reg_list, status=status.HTTP_200_OK)