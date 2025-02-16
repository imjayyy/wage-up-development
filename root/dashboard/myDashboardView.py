from django.shortcuts import render
import sys
import json
import copy
from django.core.serializers.json import DjangoJSONEncoder

sys.path.insert(0, 'root')
import math

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
import pytz
from accounts.models import *
from .serializers import *
from .models import *
from django.db.models import Q
from training.models import *
from onboarding.serializers import *
from messaging.models import *
from django.core.exceptions import ObjectDoesNotExist
from accounts.actions_logger import ActionsLogger

utc = pytz.UTC


class EmployeeDashboardApi(APIView):

    def __init__(self):
        self.request_obj = None
        self.employee_id = None
        self.user = None

    def get_employee(self, request):
        user_id = request.user.id
        employee = Employee.objects.get(user_id=user_id)
        return employee.id

    def post(self, request, *args, **kwargs):
        '''
        the post endpoint here is only for the creation of new chart elems
        '''

        ##ASSUME ALL POST REQUESTS ARE CREATION REQUESTS UNLESS THEY CONTAIN THE ID OF THE ELEMNT
        self.user = request.user
        self.request_obj = request.data
        self.employee_id = self.get_employee(request)

        '''
        possible requests here for new dashboard.

        //REMEMBER THAT ALL REQUESTS RETURN THE FULL, UPDATED SET OF THE EMPLOYEE'S DASHBOARDS. 
        //THIS ALLOWS EASY UPDATE TO THE DATA ON THE VUE SIDE

        //remember that invalid keywords will throw a TypeError
        //bad values will throw a ValueError --handle them differently

         {
            type: "dashboard",
            name: "dashboard name",
            employees: [array of employee objects]
            elements: [] // array of elements. this is removed before being passed to the model object
            order: int
            // see below for the makeup of the elements objct
         },


      **if you add the id to the above request it makes it an update statement. 
         only the updated fields are required
          {
            type: "dashboard",
            id: 13,
            name: name,
         }


        {
            type: "dashboard",
            id: 13,
            name: name,
            elements: [{id: stuff}, {id}] // see dashboard_element update format
         }


         {
            type: "dashboard",
            id: 13,
            delete: true,
         }


         {
            type: "dashboard_element",
            dashboard_id: int, // these top two can be ommitted in the case of being passed as elements in a dashboard request
            request: the request string,
            name: name,
            comments: "comment string" //optional,
            order: integer, // optional
         }

         **if you add the id to the above request it makes it an update statement. 
         only the updated fields are required
          {
            type: "dashboard_element",
            id: 131,
            name: name,
            order: integer, 
         }


       {
            type: "dashboard_element",
            id: 131,
            delete: true,
         }

        '''

        request_type = self.request_obj.get("type")
        print(request_type)
        if request_type == "dashboard":

            if 'id' in dict.keys(self.request_obj):

                if 'delete' in dict.keys(self.request_obj):
                    self.delete_employee_dashboard()
                elif 'addUser' in dict.keys(self.request_obj):
                    self.addUser()
                else:
                    self.update_employee_dashboard()

            else:
                self.create_employee_dashboard()

            return self.get_employee_dashboard_set(request)

        elif request_type == "viewed_element":
            print('viewed element', self.request_obj)
            if self.request_obj.get('action') == 'update':
                out = self.update_dashboard_element_viewed()
                return Response(out, status=200)
            elif self.request_obj.get('action') == 'get':
                out = self.get_dashboard_element_viewed()
                print('THIS IS THE OUTPUT AFTER', out)

                return Response(out, status=200)

        elif request_type == "dashboard_element":
            if 'id' in dict.keys(self.request_obj):

                if 'delete' in dict.keys(self.request_obj):
                    self.delete_employee_dashboard_element()
                else:
                    self.update_employee_dashboard_element()

            else:
                self.create_employee_dashboard_element()

            return self.get_employee_dashboard_set(request)

        elif request_type == "dashboard_comment":

            if self.request_obj.get('action') == 'update':
                out = self.update_dashboard_comment()
            elif self.request_obj.get('action') == 'delete':
                out = self.delete_dashboard_comment()
            else:
                out = self.add_dashboard_comment()
            return Response(out, status=200)
        elif request_type == "dashboard_annotation":
            if self.request_obj.get('action') == 'update':
                out = self.update_dashboard_annotation()
            else:
                out = self.add_dashboard_annotation()
            return Response(out, status=200)
        else:
            return Response("The type key was either not supplied or the value was invalid. "
                            "Must be one of 'dashboard_element', 'dashboard'", status=500)

    # TODO: THIS CURRENTLY ONLY GETS DASHBOARDS YOU ARE THE OWNER OF, NOT THOSE THAT HAVE BEEN SHARED WITH YOU
    def get(self, request):
        print(" IN GET REQUEST = EmployeeDashboardApi" )
        return self.get_employee_dashboard_set(request)

    def update_dashboard_element_viewed(self):
        read_status, created = DashboardCommentReadStatus.objects.update_or_create(
            dashboard_element_id=self.request_obj.get('dashboard_element_id'),
            organization_id=self.request_obj.get('organization_id'),
            employee_id=self.employee_id,
            viewer=self.user,
            defaults={'viewed': True})
        print(read_status, created)
        return DashboardCommentReadStatusSerializer(read_status).data

    def get_dashboard_element_viewed(self):
        print('THIS IS USER', self.user.id)
        read_elems = DashboardCommentReadStatus.objects.filter(viewer=self.user.id)
        print('THESE ARE READ ELEMS', read_elems)
        return DashboardCommentReadStatusSerializer(read_elems, many=True).data

    def update_dashboard_comment(self):
        print(self.request_obj)
        comment = DashboardComment.objects.get(id=self.request_obj.get('comment_id'))

        for k, v in self.request_obj.items():
            if k in ['rating', 'content']:
                if comment.rating.filter(id=v).exists():
                    comment.rating.remove(v)
                else:
                    comment.rating.add(v)
        comment.save()

        elem_comments = DashboardComment.objects.filter(dashboard_element_id=self.request_obj.get('dashboard_elem_id'))
        print('elem comments in update dashboard comment', elem_comments)

        return DashboardCommentSerializer(elem_comments, many=True).data

    def delete_dashboard_comment(self):
        print(self.request_obj)
        comment = DashboardComment.objects.get(id=self.request_obj.get('comment_id'))
        comment.delete()

        elem_comments = DashboardComment.objects.filter(dashboard_element_id=self.request_obj.get('dashboard_elem_id'))

        return DashboardCommentSerializer(elem_comments, many=True).data

    def update_dashboard_annotation(self):
        print(self.request_obj)
        annotation = DashboardAnnotation.objects.get(id=self.request_obj('annotation_id'))

        update_fields = {k: v for k, v in self.request_obj.items() if k in DashboardAnnotation._meta.fields}

        annotation = annotation(**update_fields)
        annotation.save()

        return DashboardAnnotationSerializer(annotation).data

    def add_dashboard_comment(self):

        for x in DashboardCommentReadStatus.objects.filter(
                dashboard_element_id=self.request_obj.get('dashboard_elem_id'),
                organization_id=self.request_obj.get('organization_id')):
            x.viewed = 0
            x.save()

        try:
            profile_pic = Profile.objects.get(employee_id=self.employee_id).photo_avatar
        except ObjectDoesNotExist:
            profile_pic = None

        new_comment = DashboardComment.objects.create(
            message=self.request_obj.get('message'),
            sender_avatar=profile_pic,
            employee_id=self.employee_id,
            parent_comment_id=self.request_obj.get('parent_comment_id'),
            dashboard_element_id=self.request_obj.get('dashboard_elem_id'),
            annotation_id=self.request_obj.get('annotation_id'),
            organization_id=self.request_obj.get('organization_id')
        )


        elem_comments = DashboardComment.objects.filter(dashboard_element_id=self.request_obj.get('dashboard_elem_id'))
        print('ELEM COMMENTS', elem_comments)




        return DashboardCommentSerializer(elem_comments, many=True).data

    def add_dashboard_annotation(self):

        new_annotation = DashboardAnnotation.objects.create(
            json=self.request_obj.get('json'),
            employee_id=self.employee_id,
            organization_id=self.request_obj.get('organization_id'),
        )

        return DashboardAnnotationSerializer(new_annotation).data

    def addUser(self):
        _id = self.request_obj["id"]
        invited = self.request_obj["invited"]
        dashboard = EmployeeDashboard.objects.get(id=_id)
        for emp_id in invited:
            emp = Employee.objects.get(id=emp_id)
            dashboard.employees.add(emp)
        dashboard.save()

    def get_employee_dashboard_set(self, request):
        self.employee_id = self.get_employee(request)
        print('employee_id is', self.employee_id)
        ALL_USER_DASHBOARD_ACCOUNT_ID = 35300  # dashboard maker account shows for everyone
        dashboard_qs = EmployeeDashboard.objects.filter(
            Q(owner_id__in=[self.employee_id, ALL_USER_DASHBOARD_ACCOUNT_ID]) | Q(employees__in=[self.employee_id]))
        # dashboard_qs = EmployeeDashboard.objects.filter(Q(employees__in=[self.employee_id]))
        dashboards = EmployeeDashboardSerializer(dashboard_qs, many=True)
        return Response(dashboards.data)

    def create_employee_dashboard(self):
        request = self.request_obj
        # if 'old_id' in request['data']:
        #     pass

        try:
            new_dashboard = EmployeeDashboard(
                owner_id=self.employee_id,
                name=request["name"],
            )
            # TODO: ADD MANY TO MANY EMPLOYEE OBJECT.
            new_dashboard.save()

        except KeyError as e:
            print(e)
            return Response("You need at least an owner_id and a name to create a dashboard", status=500)
        except ValueError as e:
            print(e)
            return Response("You passed an invalid value to the EmployeeDashboard creator. Please check your values.",
                            status=500)
        except BaseException as e:
            print(e)
            return Response("Something unusual went wrong while creating the dashboard", status=500)

        action_details = [{
            'db_action_type': 'add',
            'db_model': 'EmployeeDashboard',
            'db_model_id': new_dashboard.id,
            'context': new_dashboard.name
        }]
        if request.get("elements") and len(request.get("elements")):
            for elem in request["elements"]:
                elem["dashboard_id"] = new_dashboard.id
                db_elem = self.create_employee_dashboard_element(elem)
                action_details.append({
                    'db_action_type': 'add',
                    'db_model': 'EmployeeDashboardElement',
                    'db_model_id': db_elem['id'],
                    'context': db_elem['name']
                })
        # try:
        ActionsLogger(user=self.user,
                      model='EmployeeDashboard',
                      display='New Dashboard created %s' % request['name'],
                      action_type='My Dashboard',
                      details=action_details)
        # except Exception as e:
        #     print(e)

        return EmployeeDashboardSerializer(new_dashboard).data

    def delete_employee_dashboard(self):
        _id = self.request_obj["id"]
        dashboard = EmployeeDashboard.objects.get(id=_id)
        dashboard_employees = list(dashboard.employees.all().values_list('id', flat=True))
        if dashboard.owner.id == self.employee_id:
            ActionsLogger(user=self.user,
                          model='EmployeeDashboard',
                          display='Unsubscribed to %s' % dashboard.name,
                          action_type='My Dashboard',
                          details=[{
                              'db_action_type': 'clear_m2m',
                              'db_model': 'EmployeeDashboard',
                              'db_model_id': dashboard.id,
                              'context': 'unsubscribed from dashboard',
                              'from_value': self.employee_id,
                              'field': 'employees'
                          },
                          {
                              'db_action_type': 'update',
                              'db_model': 'EmployeeDashboard',
                              'db_model_id': dashboard.id,
                              'context': 'Removed Ownership',
                              'from_value': self.employee_id,
                              'field': 'owner'
                          }
                          ])
            dashboard.employees.clear()
            dashboard.owner = None
            dashboard.save()
            return True
        elif self.employee_id in dashboard_employees:
            emp = Employee.objects.get(id=self.employee_id)
            dashboard.employees.remove(emp)
            dashboard.save()
            ActionsLogger(user=self.user,
                          model='EmployeeDashboard',
                          display='Unsubscribed to %s' % self.request_obj['name'],
                          action_type='My Dashboard',
                          details=[{
                              'db_action_type': 'remove_m2m',
                              'db_model': 'EmployeeDashboard',
                              'db_model_id': dashboard.id,
                              'context': 'unsubscribed from dashboard',
                              'from_value': emp.id,
                              'field': 'employees'
                          }])
        else:
            raise Exception("not allowed!")

    def update_employee_dashboard(self):
        request = {**self.request_obj}
        elements = request.get('elements')

        if elements and type(elements) == type([]):
            for e in elements:
                self.update_employee_dashboard_element(e)

        request = {k: v for k, v in dict.items(request)
                   if k in
                   [f.name for f in EmployeeDashboard._meta.get_fields() if type(f) != ManyToOneRel]
                   }

        EmployeeDashboard(**request).save(update_fields=list(filter(lambda x: x != 'id', dict.keys(request))))
        return True

    def create_employee_dashboard_element(self, request=None):
        request = request if request is not None else self.request_obj
        try:
            new_dash_elem = EmployeeDashboardElement(
                dashboard_id=request["dashboard_id"],
                request=request["request"]
            )
            if request.get("name"):
                new_dash_elem.name = request.get("name")
            if request.get("comments"):
                new_dash_elem.comments = request.get("comments")
            if request.get("order"):
                new_dash_elem.order = request.get("order")
            if request.get("chart_type"):
                new_dash_elem.chart_type = request.get("chart_type")

            new_dash_elem.save()

        except KeyError as e:
            print(e)
            return Response("You need at least a dashboard_id and a request object to create a dashboard", status=500)
        except ValueError as e:
            print(e)
            return Response(
                "You passed an invalid value to the EmployeeDashboardElement creator. Please check your values.",
                status=500)
        except BaseException as e:
            print(e)
            return Response("Something unusual went wrong while creating the dashboard element", status=500)

        return EmployeeDashboardElementSerializer(new_dash_elem).data

    def delete_employee_dashboard_element(self):
        _id = self.request_obj["id"]
        EmployeeDashboardElement.objects.get(id=_id).delete()
        return True

    def update_employee_dashboard_element(self, element=None):
        if element is None:
            request = self.request_obj
        else:
            request = element

        print("inbound request", request, "dashboard", request["dashboard"])

        request["dashboard"] = EmployeeDashboard.objects.get(id=request["dashboard"])
        # filter out anything that isn't in the field list, and the id
        request = {k: v for k, v in dict.items(request)
                   if k in [f.name for f in EmployeeDashboardElement._meta.get_fields()]}

        EmployeeDashboardElement(**request) \
            .save(update_fields=list(filter(lambda x: x != 'id', dict.keys(request))))
        return True

