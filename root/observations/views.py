from django.http import HttpResponse

from django.shortcuts import render
import sys
sys.path.insert(0, 'root')
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from .serializers import *
from accounts.models import *
from .models import *
from django.db.models import Max
from django.apps import apps


from django.template.loader import render_to_string
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Q
import requests
# from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import os
from django.conf import settings
from django.http import HttpResponse, Http404

from django.core import files
from io import BytesIO
from dashboard.models import *
# from observations.models import *
# from observations.serializers import *
import itertools
from operator import itemgetter
from email.mime.image import MIMEImage
import base64
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.http import JsonResponse
# from messaging.views import Messaging as messaging_views

class Comments_(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def get_notifications(self, parameters):
        employee = Employee.objects.get(user=self.user)
        all_comments = []
        subscriptions = Subscriptions.objects.filter(subscriptions__id=employee.id).values_list('organization_subject', flat=True)
        subed_comments = Comments.objects.filter(organization__id__in=subscriptions, private=False).exclude(seen_by__id=employee.id)
        for s in subed_comments:
            all_comments.append(s.id)

        mentions = Comments.objects.filter(mentions__id=employee.id, private=False).exclude(seen_by__id=employee.id)
        for m in mentions:
            if m.id not in all_comments:
                all_comments.append(m.id)

        # TODO: how to count new chart comment (people of interest maybe)
        chart_comments = Comments.objects.filter(organization__id__in=subscriptions, private=False).exclude(chart_element=None)
        chart_comments = chart_comments.exclude(seen_by__id=employee.id)
        for c in chart_comments:
            if c.id not in all_comments:
                all_comments.append(c.id)

        private_comments = Comments.objects.filter(Q(mentions=employee) | Q(employee=employee), private=True).exclude(seen_by__id=employee.id)
        for p in private_comments:
            if p.id not in all_comments:
                all_comments.append(p.id)

        chart_count = chart_comments.count()
        total_count = len(all_comments)
        output = {
            'all_notifications': {
                'total': total_count,
                'observations': {
                    'total': total_count - chart_count,
                    'mentions': mentions.count(),
                    'private': private_comments.count(),
                    'subscriptions': {
                        'total': subed_comments.count(),
                    },
                },
                'dashboard': {
                    'total': chart_count,
                    'key_metrics': 2,
                    'members_satisfaction': 1,
                    'call_vol': 0,
                    'response_time': 0,
                    'kmi': 0,
                    'satisfaction_service_type': 0
                }
            }
        }
        for sub in subscriptions:
            output['all_notifications']['observations']['subscriptions'][sub] = subed_comments.filter(organization__id=sub).count()

        print(output)
        return {'DATA': output}


    def send_email(self, html_message):
        mail_subject = self.mail_subject
        plain_message = strip_tags(html_message)

        print(self.email)
        #return

        mail = EmailMultiAlternatives(mail_subject, plain_message, "messaging@wageup.com", self.email)
        mail.mixed_subtype = 'related'
        mail.attach_alternative(html_message, "text/html")

        #logo
        with open(settings.BASE_DIR + '/media/logo.png', 'rb') as logo:
            img = MIMEImage(logo.read(), 'png')
            img.add_header('Content-Id', '<logo.png>')
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            mail.attach(img)
        for fname, i in self.img.items():
            img = MIMEImage(base64.b64decode(i[i.find(",")+1:].encode('ascii')), 'png')
            img.add_header('Content-Id', '<' + fname + '>')
            img.add_header("Content-Disposition", "inline", filename=fname)
            mail.attach(img)
        mail.send()

    def generate_email(self, parameters):
        if 'send_to' in parameters:
            self.email = list(set([self.user.email] + [d['value'] for d in parameters['send_to']]))
        else:
            self.email = self.user.email

        self.email =[]
        for emp_id in parameters['mentions']:
            try:
                emp_id = Employee.objects.get(id=emp_id).user_id
                print(emp_id)
                user=User.objects.get(id=emp_id)
                self.email.append(user.email)
            except Exception as e:
                self.from_email = "messaging@wageup.com"
                print("something went wrong: ", e)

        # insert into all emails this text:
        db_updated = DashboardUpdateHistory.objects.latest('date_updated').date_updated.strftime("%b %d")
        intro_text = """
        <p>This is an email alert generated by WageUp to let you know that someone mentioned you in a message about performance for ACA Roadside events. Click on the link below for more information.  
         </p><p>The data was updated on <b>%s</b></p>
        """ % db_updated

        #print(intro_text)
        parameters['lambda_data']['data'].insert(0, {'intro_text': intro_text})



        lambda_response = requests.post("https://ve1mc0qia6.execute-api.us-east-1.amazonaws.com/dev/", json=parameters['lambda_data'])
        # print(lambda_response.json())
        lambda_response = lambda_response.json()
        #print(lambda_response, "RESPONSE FROM LAMBDA")
        html = lambda_response['body']['html'].replace('/\\"/g', '"')
        self.img = lambda_response['body']['imgs']

        self.mail_subject = parameters['mail_subject']


        self.send_email(html)
        return html





    def new_comment(self, parameters):
        '''
        :param parameters:
        :example:
        {
            "purpose":"new_comment",
            "parameters":{
                "commentDate":"2020-03-10",
                "requestData":{},
                "commentText":"testing testing",
                "organization_id":	"7"
                "survey_id": 12345 # OPTIONAL
            }
        }
        '''
        employee = Employee.objects.get(user=self.user)

        try:
            if parameters['type'] != 'Driver':
                organization = Organization.objects.get(slug=parameters['slug'])
            else:
                organization = None
        except:
            organization = None
        try:
            if parameters['type'] == 'Driver':
                empDash = Employee.objects.get(slug=parameters['slug'])
            else:
                empDash = None
        except:
            empDash = None

        if parameters['isPrivate'] or len(parameters['mentions']) > 0:

            email_data = {
                "mail_subject": "You have received a new mention!",
                "attachments": [],
                "lambda_data": {"data": []},
                'mentions': parameters['mentions']
            }
            self.generate_email(email_data)




        comment = Comments.objects.create(
            commentText=parameters['commentText'],
            employee=employee,
            organization=organization,
            employeeDashboard=empDash,
            private=parameters['isPrivate']
        )
        comment.seen_by.add(employee)
        if 'mentions' in parameters:
            for mention in parameters['mentions']:
                emp = Employee.objects.get(id=mention)
                comment.mentions.add(emp)

        if 'topics' in parameters:
            for topic in parameters['topics']:
                top = Topics.objects.get(name=topic)
                comment.topics.add(top)

        if 'groups' in parameters:
            for group in parameters['groups']:
                g = EmployeeGroup.objects.get(group_name=group)
                comment.groups.add(g)

        if 'survey_id' in parameters:
            comment.survey.add(Std12EReduced.objects.get(id=parameters.get('survey_id')))

        if 'chart_element_id' in parameters:
            comment.requestData=parameters['requestData']

            comment.chart_element_id = parameters['chart_element_id']

        comment.save()

        output = CommentsDataSerializer(comment).data
        return output

    # def get_survey_comments(self, parameters):
    #     print(parameters)
    #     # survey = Std12EReduced.objects.get(id=parameters.get('survey_id'))
    #     ids = parameters.get('survey_ids')
    #     surveys = Std12EReduced.objects.filter(pk__in=ids)
    #     # return CommentsDataSerializer(survey.comment).data
    #     return CommentsDataSerializer(surveys.comment).data

    def get_org_comments(self, parameters):
        '''
        {
            "purpose":"get_org_comments",
            "parameters":{
                "organization_id":	"7"
            }
        }
        :param parameters:
        :return:
        '''
        employee = Employee.objects.get(user=self.user)

        if 'organization_id' in parameters:
            org = Organization.objects.get(slug=parameters['organization_id'])
            comments = Comments.objects.filter(organization=org, reply_to=None, private=False).order_by('-commentDate')
            if "charts_only" in parameters:
                comments = comments.filter(chart_element__isnull=False)
            try:
                subscriptions = Subscriptions.objects.get(organization_subject=org)
            except ObjectDoesNotExist:
                subscriptions = Subscriptions.objects.create(organization_subject=org)
            sub_data = SubscriptionSerializer(subscriptions).data
            user_subs = Subscriptions.objects.filter(subscriptions__id=employee.id).exclude(id=subscriptions.id)
        elif 'employee_id' in parameters:
            emp = Employee.objects.get(slug=parameters['employee_id'])
            comments = Comments.objects.filter(employeeDashboard=emp, reply_to=None, private=False).order_by('-commentDate')

            print("COMMENTS", emp, comments)
            if "charts_only" in parameters:
                comments = comments.filter(chart_element__isnull=False)
            try:
                subscriptions = Subscriptions.objects.get(employee_subject=emp)
            except ObjectDoesNotExist:
                subscriptions = Subscriptions.objects.create(employee_subject=emp)
            sub_data = SubscriptionSerializer(subscriptions).data
            user_subs = Subscriptions.objects.filter(subscriptions__id=employee.id).exclude(id=subscriptions.id)
        else:
            comments = Comments.objects.filter(Q(mentions=employee) | Q(employee=employee), reply_to=None, private=False)
            sub_data = None
            user_subs = Subscriptions.objects.filter(subscriptions__id=employee.id)

        total_comments = comments.count()
        load_more = total_comments > 5

        org_comments = CommentsDataSerializer(comments[0:5], many=True).data
        user_sub_data = SubscriptionSerializer(user_subs, many=True).data
        return {'comments': org_comments, 'subscriptions': sub_data, 'user_subscriptions': user_sub_data, 'load_more': load_more}

    def update_comment(self, parameters):
        '''
        {
            "purpose": "update_comment",
            "parameters": {
                "comment_id: 22,
                "edit_type" : ("text", "important"),
                "comment_edit": if edit_type == "text" then String else if edit_type == "important" then Boolean
            }
        }
        '''
        try:
            comment = Comments.objects.get(id=parameters['comment_id'])
            edit_type = parameters['edit_type']
            comment_edit = parameters['comment_edit']
            if comment.edited is False and edit_type == 'text':
                comment.edited = True

            if edit_type == 'text':
                comment.commentText = comment_edit
            elif edit_type == 'important':
                comment.important = comment_edit
            elif edit_type == 'like':
                employee = Employee.objects.get(user=self.user)
                if employee in comment.comment_likes.all():
                    comment.comment_likes.remove(employee)
                else:
                    comment.comment_likes.add(employee)
            print('comment saved', comment)

            comment.save()

            return {'success': True}
        except:
            return {'success': False}

    def get_subscriptions(self, params):
        ''' should handle subscriptions for specific locations and or subjects (trend table...) '''
        if params['sub_type'] == 'organization':
            org_id = params['organization_id']
            try:
                subscription = Subscriptions.objects.get(organization_subject__slug=org_id)
            except:
                subscription = Subscriptions.objects.create(organization_subject__slug=org_id)

            return SubscriptionSerializer(subscription).data


    def subscribe(self, params):
        if params['sub_type'] == 'organization':
            org_id = params['organization_id']
            org = Organization.objects.get(slug=org_id)
            try:
                subscription = Subscriptions.objects.get(organization_subject=org)
            except:
                subscription = Subscriptions.objects.create(organization_subject=org)

            employee = Employee.objects.get(user=self.user_id)
            if employee in subscription.subscriptions.all():
                subscription.subscriptions.remove(employee)
                return {'subscribed': False}
            else:
                subscription.subscriptions.add(employee)
                return {'subscribed': True}

    def delete_comment(self, parameters):
        '''Need comment_id in the request in order to delete the comment'''
        comment = Comments.objects.get(id=parameters['comment_id'])
        comment.delete()

        return {'message': 'Delete Successful'}

    def get_survey_comments(self, parameters):
        '''

            "purpose": "get_survey_comments",
            "parameters": {
                "survey_id": 1235
            }
        '''
        if parameters.get('employee_id'):
            comments = Comments.objects.filter(employee__id=parameters.get('employee_id')).exclude(survey=None).order_by('-commentDate')
        elif type(parameters.get('survey_ids')) == list:
            comments = Comments.objects.filter(survey__id__in=parameters.get('survey_ids'))
        else:
            comments = Comments.objects.filter(survey__id__in=[parameters.get('survey_ids')])
        print('THESE ARE THE COMMENTS', comments)
        if 'lower_bound' in parameters:
            comments = comments[parameters['lower_bound']: parameters['upper_bound']]

        comment_length = comments.count()
        return {
            'comments': CommentsDataSerializer(comments, many=True).data,
            'count': comment_length
                }



    def get_comments_handler(self, parameters):
        '''
        {
            "purpose": "get_comments_handler",
            "parameters": {
                "comment_type": String ("all", "subscribed", "mentions", "charts"),
                "range": [Number(start), Number(end)],
                "sub_id": Number (Subscription Number),
                "comment_ids": [Array of Comment Ids],
                "organization_id": Number(Needed for comment_type: "all")
            }
        }
        '''
        employee = Employee.objects.get(user=self.user)
        try:
            org = Organization.objects.get(slug=parameters['organization_id'])
        except:
            org = None
        low, high = parameters['range']
        comment_listed = parameters['comment_ids']
        if parameters['comment_type'] == 'subscribed':
            sub = Subscriptions.objects.get(id=parameters['sub_id'])
            comments = Comments.objects.filter(organization=sub.organization_subject, reply_to=None, private=False).exclude(id__in=comment_listed).order_by('-commentDate')
        elif parameters['comment_type'] == 'mentions':
            comments = Comments.objects.filter(Q(mentions__id=employee.id) | Q(groups__name=employee.position_type), reply_to=None, private=False).exclude(id__in=comment_listed).order_by('-commentDate')
        elif parameters['comment_type'] == 'surveys':
            comments = Comments.objects.filter(employee__id=parameters.get('employee_id')).exclude(survey=None).order_by('-commentDate')
        elif parameters['comment_type'] == 'charts':
            sub = Subscriptions.objects.get(id=parameters['sub_id'])
            comments = Comments.objects.filter(organization=sub.organization_subject, reply_to=None, private=False).exclude(chart_element=None).order_by('-commentDate')
            comments = comments.exclude(id__in=comment_listed)
        elif parameters['comment_type'] == 'private':
            comments = Comments.objects.filter(Q(employee=employee) | Q(mentions__id=employee.id), private=True, reply_to=None).distinct().order_by('-commentDate')
            comments = comments.exclude(id__in=comment_listed)
        else:
            all_comments = []
            subs = Subscriptions.objects.filter(subscriptions__id=employee.id).values_list('organization_subject', flat=True)
            sub_comments = Comments.objects.filter(organization__in=subs, reply_to=None, private=False).exclude(id__in=comment_listed).distinct()
            for s in sub_comments:
                all_comments.append(s)
            if org.id not in subs:
                org_comments = Comments.objects.filter(organization=org, reply_to=None, private=False).exclude(id__in=comment_listed)
                for o in org_comments:
                    all_comments.append(o)
            mentions = Comments.objects.filter(mentions__id=employee.id, reply_to=None, private=False).exclude(id__in=comment_listed)
            for m in mentions:
                if m not in all_comments:
                    all_comments.append(m)
            total_comments = len(all_comments)
            if total_comments > high:
                load_more = True
            else:
                load_more = False
            output = CommentsDataSerializer(all_comments, many=True).data
            return {'comments': output, 'load_more': load_more}

        total_comments = comments.count()
        if total_comments > high:
            load_more = True
        else:
            load_more = False
        comments = comments[low:high]
        output = CommentsDataSerializer(comments, many=True).data
        return {'comments': output, 'load_more': load_more}

    def createUserNotification(self, parameters):
        inUsereNotif=UserCommentNotifications.objects.filter(employee_id=self.user.id).count()
        if inUsereNotif==0:
            UserCommentNotifications.objects.create(employee_id=self.user.id, organization_id=parameters['organization_id'])

    def updateUserNotificationsInOrg(self, parameters):
        update_users_in_org_except_current=UserCommentNotifications.objects.filter(organization_id=parameters['organization_id']).exclude(employee_id=self.user.id)
        update_users_in_org_except_current.update(newNotificationCount=F('newNotificationCount')+1)

    def get_topics(self, parameters):
        topics = Topics.objects.all()
        print(topics)
        return topics.values()

    def add_topic(self, parameters):
        topic = Topics.objects.create(
            name=parameters['topic_name']
        )

        return TopicSerializer(topic).data

    def get_groups(self, parameters):
        groups = EmployeeGroup.objects.all()
        print(groups)
        output = GroupSerializer(groups, many=True)
        return output.data

    def add_group(self, parameters):
        group = EmployeeGroup.objects.create(
            name=parameters['group_name']
        )
        output = GroupSerializer(group)

        return output.data

    def new_thread(self, parameters):
        '''
        {
            "purpose":"new_thread",
            "parameters":{
                "commentDate":"2020-03-10",
                "requestData":{},
                "commentText":"testing testing",
                "organization_id":	"7"
            }
        }
        :param parameters:
        :return:
        '''
        self.createUserNotification(parameters)


        # newThread=CommentThread.objects.create(requestData=parameters['requestData'], commentDate=parameters['commentDate'])

        Comments.objects.create(commentDate=parameters['commentDate'], commentText=parameters['commentText'], requestData=parameters['requestData'],
                                employee=self.user, organization_id=parameters['organization_id'], order=0, thread=newThread)

        self.updateUserNotificationsInOrg(parameters)

    def reply(self, params):
        '''
        {
            "purpose":"reply",
            "parameters":{
                "commentDate":"2020-03-10",
                "requestData":{},
                "commentText":"testing testing",
                "comment_id":"1"
            }
        }
        :param parameters:
        :return:
        '''
        # self.createUserNotification(parameters)
        comment = Comments.objects.get(id=params['comment_id'])
        employee = Employee.objects.get(user=self.user_id)
        reply_count = Comments.objects.filter(reply_to=comment).count()

        increment_order = reply_count + 1

        new_comment = Comments.objects.create(commentDate=params['commentDate'],
                                commentText=params['commentText'],
                                employee=employee,
                                reply_to=comment,
                                organization_id=comment.organization_id,
                                employeeDashboard=comment.employeeDashboard,
                                order=increment_order)
        new_comment.save()
        output = CommentsDataSerializer(new_comment).data
        return {'comment': output}

    def all_threads_by_org(self, parameters):
        '''
        {
            "purpose":"all_threads_by_org",
            "parameters":{
                "organization_id":	"7",
            }
        }
        :param parameters:
        :return:
        '''

        self.user_zero_notif()
        org_filter = Comments.objects.filter(organization_id=parameters['organization_id']).order_by('commentDate').values()

        threads = {}
        for comment in org_filter.iterator():
            if comment['thread_id'] is None:
                continue
            if comment['thread_id'] not in threads:
                threads[comment['thread_id']] = []
            threads[comment['thread_id']].append(comment)
        return threads

    def user_zero_notif(self):
        '''
        called from other messages
        all_threads_by_org
        '''
        inUsereNotif = UserCommentNotifications.objects.filter(employee_id=self.user.id).count()
        if inUsereNotif > 0:
            UserCommentNotifications.objects.filter(employee_id=self.user.id).update(newNotificationCount=0)

    def comments_seen_handler(self, parameters):
        comment_ids = parameters['comments']
        employee = Employee.objects.get(user=self.user)
        comments = Comments.objects.filter(id__in=comment_ids).exclude(seen_by__id=employee.id)
        for c in comments:
            c.seen_by.add(employee)
            c.save()

        return {'seen_updated': True}

    def post(self, request):
        self.data = request.data
        if request.user:
            self.user = request.user
            self.user_id = self.user.id



        self.purpose_router = {
            'get_notifications': self.get_notifications,
            'new_comment': self.new_comment,
            'get_org_comments': self.get_org_comments,
            'new_thread': self.new_thread,
            'reply': self.reply,
            'all_threads_by_org': self.all_threads_by_org,
            'update_comment': self.update_comment,
            'get_topics': self.get_topics,
            'add_topic': self.add_topic,
            'get_groups': self.get_groups,
            'add_group': self.add_group,
            'delete_comment': self.delete_comment,
            'subscribe': self.subscribe,
            'get_comments_handler': self.get_comments_handler,
            'get_survey_comments': self.get_survey_comments,
            'comments_seen_handler': self.comments_seen_handler
        }

        output = self.purpose_router[self.data['purpose']](self.data['parameters'])
        return Response(output, status=status.HTTP_200_OK)
