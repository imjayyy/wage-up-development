from django.shortcuts import render
import sys

sys.path.insert(0, 'root')
from django.http.response import HttpResponse, FileResponse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .serializers import *
from accounts.models import Employee, Profile
from arena.models import *
from datetime import date
from .models import *
from arena.serializers import HH5Serializer, HH5DriverSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Count


class Campaining(generics.GenericAPIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'

    def __init__(self):
        self.purpose_router = {
            'create_campaign': self.create_campaign,
            'get_campaign_list': self.get_campaign_list,
            'get_campaign': self.get_campaign,
            'create_module': self.create_module,
            'module_list': self.module_list,
            # 'tag_list': self.tag_list,
            'module_list_select': self.module_list_select,
            'get_module': self.get_module,
            'update_modules': self.update_modules,
            'delete_modules': self.delete_modules,
            'complete_modules': self.complete_modules,
            'sign_up_to_campaign': self.sign_up_to_campaign,
            'get_registered_campaign': self.get_registered_campaign,
            'set_campaign_image': self.set_campaign_image
        }

    def post(self, request, *args, **kwargs):
        self.data = request.data
        self.user = self.request.user
        output = self.purpose_router[self.data['purpose']](self.data['parameters'])

        return Response(output, status=status.HTTP_200_OK)

    def create_campaign(self, params):
        '''
        :param params:
        title,
        start,
        end,
        reg_requirements,
        description,
        image,
        existing_modules: [],
        modules_req[]:
            title,
            description,
            pages[]:
                type (question, video),
                video_link,
                video_length_required
                questions:
                    question,
                    type,
                    answers[]:
                        answer,
                        is_correct
        :return:
        '''
        campaign_title = params.get('title', {})
        campaign_start = params.get('start', None)
        campaign_end = params.get('end', None)
        modules_required = params.get('modules_req', [])
        existing_modules = params.get('existing_modules', [])
        positions = params.get('positions', [])
        new_req_modules = []
        new_campaign = PPCampaign.objects.create(
            title=campaign_title,
            start=campaign_start,
            end=campaign_end,
            created_by=Employee.objects.get(user=self.user),
            description=params.get('description', None),
            position_type=', '.join(positions)
        )
        geos = params.get('geography_eligiblity', [])
        if len(geos) > 0:
            [new_campaign.geography_eligiblity.add(Organization.objects.get(id=o['id'])) for o in geos]
            new_campaign.save()
        if params.get('has_req_modules', False):
            for m in modules_required:
                module_title = m.get('title', None)
                module_description = m.get('description', None)
                module_pages = m.get('pages', [])

                new_module = ModuleOverview.objects.create(
                    title=module_title,
                    description=module_description,
                )
                new_req_modules.append(new_module.id)

                if len(module_pages) > 0:
                    for p in module_pages:
                        page_type = p.get('type')
                        video_link = p.get('file', None)
                        video_length_req = p.get('video_length_required')
                        page = ModulePage.objects.create(type=page_type, media_link=video_link,
                                                         media_length_required=video_length_req, overview=new_module)
                        page.save()
                        page_questions = p.get('question', None)
                        if page_questions is not None:
                            question = ModuleQuestion.objects.create(question=page_questions.get('question'), page=page,
                                                                     type=page_questions.get('type'))
                            question.save()
                            print(page_questions.get('type'))
                            if page_questions.get('type') != 'open_ended':
                                [QuestionsAnswer.objects.create(answer=a.get('answer'), is_correct=a.get('is_correct'),
                                                                question=question) for a in
                                 page_questions.get('answers')]
        [new_campaign.registration_requirements.add(ModuleOverview.objects.get(id=m)) for m in new_req_modules]
        [new_campaign.registration_requirements.add(ModuleOverview.objects.get(id=m)) for m in existing_modules]
        new_campaign.save()
        has_image = params.get('image', False)
        # print('image', image_file)
        if has_image:
            image_file = self.data['image']
            file_data = CampaignImageSerializer(data={'id': new_campaign.id, 'image': image_file}, partial=True)
            print('image', file_data, file_data.is_valid())
            if file_data.is_valid():
                file_data.save()
                new_campaign = Campaign.objects.get(id=new_campaign.id)

        output = CampaignSerializer(new_campaign).data
        return output

    def set_campaign_image(self, params):
        image = self.data['image']
        campaign = PPCampaign.objects.get(id=self.data['id'])
        camp_serializer = CampaignImageSerializer(campaign, data={'image': image}, partial=True)
        if camp_serializer.is_valid():
            camp_serializer.save()
            output = CampaignSerializer(PPCampaign.objects.get(id=self.data['id'])).data
        else:
            output = {'image_saved': False}
        return output

    def get_campaign_list(self, params):
        get_by = params.get('get_by', 'active')
        if get_by == 'active':
            campaigns = Campaign.objects.filter(active=True)
        if get_by == 'creator':
            campaigns = Campaign.objects.filter(created_by__user=self.user)
        if get_by == 'creator_active':
            campaigns = Campaign.objects.filter(created_by__user=self.user, active=True)
        if get_by == 'all':
            campaigns = Campaign.objects.all()

        output = campaigns.annotate(registration_count=Count('registered_employees__count')) \
            .values('id', 'title', 'description', 'registration_count')

        return output

    def get_campaign(self, params):
        camp_id = params.get('id', None)
        if camp_id:
            campaign = Campaign.objects.get(id=camp_id)
            output = CampaignSerializer(campaign)
            return output.data
        else:
            return {'message': 'No Campaign ID Given'}

    def update_campaign(self, params):
        pass

    def sign_up_to_campaign(self, params):
        print('self', self)
        print('params', params)
        # checklist
        # get campaign
        camp_id = params.get('id', None)
        campaign = Campaign.objects.get(id=camp_id)
        # get employee using self.user
        employee = Employee.objects.get(user=self.user)

        # get profile using employee
        profile = Profile.objects.get(employee=employee)

        user_email = Profile.objects.filter(user_id=self.user).values('user_id__email')
        # compare email given to profile email and if it's different then add the new email to campaign_preferred_email field in Profile
        payments_email = params.get('payments_email', None)
        if user_email != payments_email:
            profile.campaign_preferred_email = payments_email
            profile.save()
        # create a new CampaignUser using the information above
        new_campaign_user = CampaignUser.objects.create(
            campaign=campaign,
            user=self.user,
            employee=employee,
            email=profile.campaign_preferred_email
        )
        new_campaign_user.save()
        # return TBD
        output = 'This is tbd'
        return output

    def module_list(self, params):
        '''
        :param params:
        :return:
        '''
        modules = ModuleOverview.objects.all()
        modules = ModuleOverviewSerializer(modules, many=True).data
        for x in modules:
            completion = ModuleCompletion.objects.filter(module_id=x['id'], employee_id=self.user.employee().id)
            x.update({'module_completion': completion.values()})
        modules = [m.update({'module_completed': m['module_completion'][0]['completed'] if len(m['module_completion']) > 0 else False}) or m for m in modules]
        return modules

    # def tag_list(self, params):
    #     tags = ModuleTag.objects.all()
    #     tags = ModuleTagSerializer(tags, many=True).data
    #     return tags

    def module_list_select(self, params):
        '''
        :param params:
        :return:
        '''
        modules = ModuleOverview.objects.filter(active=True).values('id', 'title', 'description')
        return modules

    def create_module(self, params):
        '''
        :param params:
        title,
        description,
        pages[]:
            type (question, video),
            video_link,
            video_length_required
            questions[]:
                question,
                type,
                answers:
                    answer,
                    is_correct
        :return:
        '''
        module_title = params.get('title')
        module_description = params.get('description')
        pages = params.getlist('pages[]', [])
        module = ModuleOverview.objects.create(title=module_title, description=module_description)
        if len(pages) > 0:
            for p in pages:
                page_type = p.get('type')
                v_link = p.get('video_link', None)
                v_length = p.get('video_length_required', None)
                page = ModulePage.objects.create(type=page_type, video_link=v_link, video_length_required=v_length,
                                                 overview=module)
                questions = p.getlist('questions[]', [])
                if len(questions) > 0:
                    for q in questions:
                        question = ModuleQuestion.objects.create(question=q.get('question'), type=q.get('type'),
                                                                 page=page)
                        [QuestionsAnswer.objects.create(question=question, answer=a.get('answer'),
                                                        is_correct=a.get('is_correct')).values() for a in
                         q.getlist('answers[]')]
        module.save()
        output = ModuleOverviewSerializer(module).data
        return output

    def get_module(self, params):
        module_id = params.get('module_id')
        module = ModuleOverview.objects \
            .prefetch_related('module_overview', 'module_overview__module_page',
                              'module_overview__module_page__module_question') \
            .get(id=module_id)
        return ModuleOverviewSerializer(module).data

    def update_modules(self, params):
        '''
        :param params:
        module_id,
        new_title,
        new_description
        :return:
        '''
        module = ModuleOverview.objects.get(id=params.get('module_id'))
        new_title = params.get('new_title', None)
        new_description = params.get('new_description', None)
        if new_title:
            module.title = new_title
        if new_description:
            module.description = new_description
        module.save()
        return {'module_saved', True}

    def delete_modules(self, params):
        module = ModuleOverview.objects.get(id=params.get('module_id'))
        module.delete()
        return {'module_deleted': True}

    def complete_modules(self, params):
        '''
        :param params:
        module_id,
        is_completed (boolean)
        page_id
        :return:
        '''
        completed = params.get('is_completed')
        module = ModuleOverview.objects.get(id=params.get('module_id'))
        recorder_module = ModuleCompletion.objects.get_or_create(
            employee=self.user.employee(),
            module=module
        )[0]
        recorder_module.completed = completed

        if completed:
            recorder_module.date_completed = date.today()
            recorder_module.last_completed_page = None  # Optionally reset the last completed page
        else:
            last_page = ModulePage.objects.get(id=params.get('page_id'))
            recorder_module.last_completed_page = last_page
            recorder_module.date_completed = None  # Reset the date if the module is marked incomplete

        recorder_module.save()

        return {'completed': completed}

    def get_registered_campaign(self, params):
        campaign_id = params.get('campaign_id', None)
        campaign = Campaign.objects.get(id=campaign_id)
        registered_users = CampaignUser.objects.filter(campaign=campaign)
        return registered_users.values('employee__full_name', 'employee_id', 'updated')
