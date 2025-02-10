from django.shortcuts import render
import sys
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models.functions import Concat
sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import generics, status
from rest_framework.views import APIView
from .models import *
from accounts.actions_logger import *
from accounts.models import *
from .serializers import *
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
import datetime as dt
import json

# Create your views here.
class Homepage(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)

    www_authentication_realm = 'api'

    def get_widget_types(self):
        types = Widget.objects.all()
        list = types.values_list('type', flat=True)
        return {'types': list}

    def get_widgets(self, parameters):
        emp_permission = self.employee.permission.all().values_list('id', flat=True)
        # if 28 in emp_permission or 10 in emp_permission or 1 in emp_permission:
        if True:
            non_date_widget = WidgetData.objects.filter(start_date=None, end_date=None).values_list('id', flat=True)
            today = dt.datetime.now()
            today = today.replace(hour=0, minute=0)
            date_widget = WidgetData.objects.filter(start_date__lte=today.date(), end_date__gte=today.date()).values_list('id', flat=True)
            all_wid = list(non_date_widget) + list(date_widget)
            widgets = WidgetData.objects.filter(id__in=all_wid)
        else:
            non_date_widget = WidgetData.objects.filter(employee_groups__in=self.employee.group.all(), start_date=None, end_date=None).values_list('id', flat=True)
            today = dt.datetime.now()
            today = today.replace(hour=0, minute=0)
            date_widget = WidgetData.objects.filter(employee_groups__in=self.employee.group.all(), start_date__gte=today.date(), end_date__lte=today.date()).values_list('id', flat=True)
            all_wid = list(non_date_widget) + list(date_widget)
            all_widgets = WidgetData.objects.filter(id__in=all_wid)
            widgets = []
            for a in all_widgets:
                if a not in widgets:
                    widgets.append(a)

        widget_output = WidgetDataSerializer(widgets, many=True).data
        today = dt.datetime.now()
        three_mo = today - dt.timedelta(days=90)
        user_history = UserActions.objects.filter(user=self.user_id, date__gt=three_mo).values('display', 'type', 'url', 'date').order_by('-date')
        groups = EmployeeGroup.objects.all().values('id', 'group_name', 'slug')
        return {'widgets': widget_output, 'history': user_history, 'employee_groups': groups}

    def add_widget(self, parameters):
        widget_type = Widget.objects.get(type=parameters['type'])
        if 'externalType' in parameters:
            w_type = parameters['externalType']
        else:
            w_type = 'simple'

        widget = WidgetData.objects.create(
            widget=widget_type,
            order=parameters['order'],
            grid_size=parameters['grid_size'],
            announcementType=parameters['announcementType'],
            image=parameters['image'],
            message=parameters['message'],
            title=parameters['title'],
            time=parameters['time'],
            url_link=parameters['url_link'],
            type=w_type
        )
        for p in parameters['permissions']:
            group = EmployeeGroup.objects.get(id=p)
            widget.employee_groups.add(group)
        if parameters['type'] == 'announcement' and parameters['start_date'] is not None and parameters['end_date'] is not None:
            print(parameters['start_date'], parameters['end_date'])
            widget.start_date = dt.datetime.strptime(parameters['start_date'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
            widget.end_date = dt.datetime.strptime(parameters['end_date'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
        widget.save()
        output = WidgetDataSerializer(widget).data
        return output

    def edit_widget(self, parameters):
        print(parameters)
        widget = WidgetData.objects.get(id=parameters['widget_id'])
        widget.grid_size = parameters['grid_size']
        widget.message = parameters['message']
        widget.title = parameters['title']
        widget.url_link = parameters['url_link']
        widget.time = parameters['time']
        # if parameters['modal_content'] is not None:
        #     if parameters['modal_content']['id'] is not None:
        #         modal_text = WidgetModalContent.objects.get(id=parameters['modal_content']['id'])
        #         modal_text.html_text = parameters['modal_content']['html_text']
        #         modal_text.save()
        #     else:
        #         print(WidgetModalContent)
        #         modal_text = WidgetModalContent.objects.create(
        #             html_text=parameters['modal_content']['html_text']
        #         )
        #         widget.modal_content.add(modal_text)
        widget.employee_groups.clear()
        for p in parameters['permissions']:
            group = EmployeeGroup.objects.get(id=p)
            widget.employee_groups.add(group)

        widget.save()
        output = WidgetDataSerializer(widget).data
        return output

    def edit_modal_widget(self, parameters):
        widget = WidgetData.objects.get(id=parameters['widget_id'])
        widget_modal_content = WidgetModalContent.objects.filter(id__in=widget.modal_content.all())[0]
        widget_modal_content.html_text = parameters['html_update']
        widget_modal_content.save()
        output = WidgetDataSerializer(widget).data
        return output

    def edit_announcement(self, parameters):
        widget = WidgetData.objects.get(id=parameters['widget_id'])
        edits = parameters['edit']
        widget.title = edits['title']
        widget.message = edits['message']
        widget.url_link = edits['url_link']
        if edits['start_date'] is not None:
            widget.start_date = dt.datetime.strptime(edits['start_date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if edits['end_date'] is not None:
            widget.end_date = dt.datetime.strptime(edits['end_date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        widget.announcementType = edits['announcementType']
        widget.employee_groups.clear()
        for p in edits['employee_groups']:
            group = EmployeeGroup.objects.get(id=p)
            widget.employee_groups.add(group)
        widget.save()
        return {'success': True}

    def re_order_announcements(self, parameters):
        announcement_list = parameters['announcements']
        print(announcement_list)
        for a in announcement_list:
            print(a, a['id'])
            announcement = WidgetData.objects.get(id=a['id'])
            announcement.order = a['order']
            announcement.save()

        non_date_widget = WidgetData.objects.filter(start_date=None, end_date=None).values_list('id', flat=True)
        today = dt.datetime.now()
        today = today.replace(hour=0, minute=0)
        date_widget = WidgetData.objects.filter(start_date__lte=today.date(), end_date__gte=today.date()).values_list(
            'id', flat=True)
        all_wid = list(non_date_widget) + list(date_widget)
        all_announcements = WidgetData.objects.filter(id__in=all_wid, widget__type='announcement')

        # all_announcements = WidgetData.objects.all().order_by('order')
        # print(all_announcements.filter(widget__type='announcement'))
        return WidgetDataSerializer(all_announcements, many=True).data

    def delete_widget(self, parameters):
        widget = WidgetData.objects.get(id=parameters['widget_id']).delete()
        return {'deleted', True}

    def widget_move(self, parameters):
        widgets = WidgetData.objects.all()
        for w in parameters['widget_list']:
            try:
                widget = widgets.get(id=w['id'])
                widget.order = w['order']
                widget.save()
            except:
                continue
        return {'success': True}

    def add_content(self, parameters):
        widget = WidgetData.objects.get(id=parameters['widget_id'])
        print(parameters)
        if parameters['is_file'] == True:
            content = WidgetModalFileSerializer(data={'file': parameters['file']['file'],
                                                      'text': parameters['text'],
                                                      'url_text': parameters['url_text'],
                                                      'is_file': parameters['is_file']},
                                                partial=True)
            if content.is_valid():
                content.save()
                widget.modal_content.add(content.data['id'])
                widget.save()
                output = WidgetDataSerializer(widget).data
                return content.data
            else:
                return content.errors
        else:
            content = WidgetModalContent.objects.create(
                text=parameters['text'],
                url_text=parameters['url_text'],
                url_link=parameters['url_link'],
                is_file=False
            )
            content.save()
            widget.modal_content.add(content)
            widget.save()
            output = WidgetModalContentSerializer(content).data
            return output

    #
    # def edit_content(self, parameters):
    #     content = WidgetContent.objects.get(id=parameters['content_id'])
    #
    #     if content.type == 'Text':
    #         content.message = parameters['message']
    #     elif content.type == 'Link':
    #         content.url_link = parameters['url_link']
    #         content.link_text = parameters['link_text']
    #     elif content.type == 'Image':
    #         content.image = parameters['Image']  # investigate how to upload
    #         content.message = parameters['message']
    #
    #     return {'success': True}
    #
    def delete_content(self, parameters):
        content = WidgetModalContent.objects.get(id=parameters['content_id']).delete()
        return {'deleted': True}

    # def content_move(self, parameters):
    #     contents = WidgetContent.objects.filter(id__in=parameters['id_list'])
    #     for c in parameters['content_list']:
    #         content = contents.get(id=c['id'])
    #         content.order = c['order']
    #         content.save()
    #     return {'success': True}

    def add_remove_driver_form(self, parameters):
        print('add remove submitted')
        # try:
            # new_form = AddRemoveDriver.objects.create(
            #     tm=parameters['tm'],
            #     shop_id=parameters['shop_id'],
            #     multiple_id=parameters['change_req'],
            #     shop_id_list=json.dumps(parameters['list_of_shop_id']),
            #     add_drivers=json.dumps(parameters['add_drivers']),
            #     remove_drivers=json.dumps(parameters['remove_drivers']),
            #     comments=parameters['comments']
            # )
            # new_form.save()
        message = render_to_string('homepage/add_remove_drivers.html',
                                   {
                                       'shop_id': parameters['shop_id'],
                                       'change_req': parameters['change_req'],
                                       'tm': parameters['tm']['name'],
                                       'shop_id_list': parameters['list_of_shop_id'],
                                       'add_drivers': parameters['add_drivers'],
                                       'remove_drivers': parameters['remove_drivers'],
                                       'comments': parameters['comments'],
                                       'submitter_name': self.employee.full_name,
                                       'submitter_email': self.user.email
                                   })
        # to_email = ['jesus.diaz.barriga@thedgcgroup.com']
        # to_email = ['jyarbrough@aaamidatlantic.com', 'egrimes@aaamidatlantic.com']
        to_email = ['ComplianceCoordinatorAlliance@aaacorp.com', 'jyarbrough@aaamidatlantic.com', 'egrimes@aaamidatlantic.com']
        subject = 'Add/Remove Drivers for ' + parameters['shop_id']
        email = EmailMessage(subject, message, 'noreply@wageup.com', to=to_email)
        email.send()
        return {'success': True}
        # except:
        #     return {'success': False}

    def tech_issue_form(self, parameters):
        try:
            # new_form = TechIssue.objects.create(
            #     shop_id=parameters['shop_id'],
            #     tm=parameters['tm'],
            #     point_of_contact=json.dumps(parameters['poc']),
            #     category=parameters['category'],
            #     description=parameters['description']
            # )
            # new_form.save()
            message = render_to_string('homepage/tech_issue.html', {
                'shop_id': parameters['shop_id'],
                'tm': parameters['tm']['name'],
                'poc': parameters['poc'],
                'category': parameters['category'],
                'sub_category': parameters['sub_category'],
                'description': parameters['description'],
                'submitter_name': self.employee.full_name,
                'submitter_email': self.user.email
            })
            # to_email = ['jesus.diaz.barriga@thedgcgroup.com']
            to_email = ['jyarbrough@aaamidatlantic.com', 'egrimes@aaamidatlantic.com']
            mail_subject = 'Tech Issue for ' + parameters['shop_id']
            email = EmailMessage(mail_subject, message, 'noreply@wageup.com', to=to_email)
            email.send()
            return {'success': True}
        except:
            return {'success': False}

    def user_view_widget(self, params):
        print(params)
        ActionsLogger(self.user, 'WidgetData', 'Widget view: {0}'.format(params['widget_id']), 'Homepage', '/homepage')
        print('see Widget')
        widget = WidgetData.objects.get(id=params['widget_id'])
        if self.employee.id not in widget.seen_by.all():
            widget.seen_by.add(self.employee.id)
            widget.save()
        return {'done': True}
        # try:
        #     widget = WidgetData.objects.get(id=params['widget_id'])
        #     if self.user.employee() not in widget.seen_by.all():
        #         widget.seen_by.add(self.user.employee)
        #         widget.save()
        #     return {'done': True}
        # except:
        #     return {'done': True}

    def get_managers(self, params):
        do_not_include = [33259, 54938, 36021, 35085, 22172, 26315]
        managers = Employee.objects.filter(position_type='Territory-Associate', group__in=[7])\
            .exclude(id__in=do_not_include)\
            .order_by('full_name')\
            .values('full_name', 'display_name', 'user__email')
        return managers

    def post(self, request):
        self.data = request.data
        if request.user:
            self.user = request.user
            self.user_id = self.user.id
            self.employee = Employee.objects.get(user_id=self.user_id)

        self.purpose_router = {
            'get_widgets': self.get_widgets,
            'add_widget': self.add_widget,
            'delete_widget': self.delete_widget,
            'edit_widget': self.edit_widget,
            'widget_move': self.widget_move,
            'add_content': self.add_content,
            'delete_content': self.delete_content,
            'edit_announcement': self.edit_announcement,
            'add_remove_driver_form': self.add_remove_driver_form,
            'tech_issue_form': self.tech_issue_form,
            're_order_announcements': self.re_order_announcements,
            'user_view_widget': self.user_view_widget,
            'get_managers': self.get_managers
        }

        output = self.purpose_router[self.data['purpose']](self.data['parameters'])

        return Response(output, status=status.HTTP_200_OK)

    def __init__(self):
        self.user = None
        self.user_id = None
        self.employee = None

class CarouselPictureUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    www_authenticate_realm = 'api'

    def post(self, request, *args, **kwargs):
        print(request.data)
        print(request.data['id'][0])
        print('test')
        queryset = WidgetData.objects.get(pk=request.data['id'])
        print(queryset)

        file_serializer = WidgetImageSerializer(queryset, data=request.data, partial=True)

        if file_serializer.is_valid():
            file_serializer.save()
            queryset = WidgetData.objects.get(id=file_serializer.data['id'])
            output = WidgetDataSerializer(queryset).data
            # print(file_serializer.data.getlist('id[]'))
            # queryset.content.add(file_serializer.data['id'])

            return Response(output, status=status.HTTP_201_CREATED)
        else:
            print(file_serializer.errors)
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    www_authenticate_realm = 'api'

    def post(self, request, *args, **kwargs):
        queryset = WidgetData.objects.get(pk=request.data['id'])
        print(request.data)

        file_serializer = WidgetFileSerializer(queryset, data={'file': request.data['file']}, partial=True)

        if file_serializer.is_valid():
            file_serializer.save()
            file_serializer = file_serializer.data
            queryset = WidgetData.objects.get(id=file_serializer['id'])
            output = WidgetDataSerializer(queryset).data
            return Response(output, status=status.HTTP_201_CREATED)
        else:
            print(file_serializer.errors)
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ModalFileUpload(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    www_authenticate_realm = 'api'

    def post(self, request, *args, **kwargs):
        widget = WidgetData.objects.get(id=request.data['widget_id'])

        file_serializer = WidgetModalContentSerializer(data={
            'file': request.data['file'],
            'text': request.data['text'],
            'url_text': request.data['url_text'],
            'is_file': True
        }, partial=True)

        if file_serializer.is_valid():
            file_serializer.save()
            output = file_serializer.data
            widget.modal_content.add(output['id'])
            widget.save()
            return Response(file_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# user file upload function/view
class UserFileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated,)
    www_authenticate_realm = 'api'

    def post(self, request, *args, **kwargs):
        data = request.data
        if data['file']:
            f_name, f_ext = data['file'].name.split('.')
            file_name = '{0}_{1}_{2}.{3}'.format(data['file_upload_name'], request.user.username, f_name, f_ext)
            save_path = 'homepage_user_uploads/' + file_name
            default_storage.save(save_path, data['file'])
            return Response({'success': True}, status=status.HTTP_200_OK)
        else:
            return Response({'error': True}, status=status.HTTP_400_BAD_REQUEST)