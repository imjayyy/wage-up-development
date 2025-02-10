from haystack.generic_views import SearchView
import json
from django.http import JsonResponse
from haystack.query import SearchQuerySet
from ast import literal_eval
from django.views.decorators.csrf import csrf_exempt
from accounts.models import *
import datetime as dt
#TODO: reorganize this into a class structure

class WageupSearchView(SearchView):
    """My custom search view."""

    def get_queryset(self):
        queryset = super(WageupSearchView, self).get_queryset()
        # further filter queryset based on some set of criteria
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super(WageupSearchView, self).get_context_data(*args, **kwargs)
        # do something
        return context


def general_search(content, count):
    organizations = []
    sorting_order = ['Club',  'Station-State', 'Facility-Rep', 'Station-Business', 'Station', 'Club-Facility-Type',]
    num = int(count)
    print('start query', dt.datetime.now())
    sqs_all = SearchQuerySet().autocomplete(displayname=content).models(Organization)
    org_count = len(sqs_all)
    sort_sqs = sorted(sqs_all, key=lambda x: sorting_order.index(x.type))

    sqs = sort_sqs[num-5:num]#.order_by("displayname")
    print('sorted query', dt.datetime.now())
    if len(sqs) < 5:
        diff = 5 - len(sqs)
        end = num - org_count
        emp_sqs = SearchQuerySet().autocomplete(displayname=content).models(Employee)[end-diff:end]
        sqs = sqs + emp_sqs
    suggestions = []
    for result in sqs:
        out = {'name': result.displayname,
                            'link': '/dashboard/' + result.slug + '/',
                            'type': result.model_name,
                            'object_type': result.type,
                            'email': result.email,
                            'id': int(str(result.id).split('.')[-1])
                            }
        if out['type'] == 'employee':
            out['emp_org_id'] = result.organization_id
        suggestions.append(out)
    suggestions = sorted(suggestions, key=lambda x: x['type'], reverse=True)

    # print(suggestions)
    has_more = True
    if len(sqs) < 5:
        has_more = False
    return {'result': suggestions, 'has_more': has_more}


def employee_search(content):
    #print(content)
    #sqs = SearchQuerySet().filter(content=content).order_by("displayname")
    sqs = SearchQuerySet().autocomplete(displayname=content).models(Employee)
    suggestions = []
    for result in sqs:
        suggestions.append({'name': result.displayname,
                            'link': '/dashboard/' + result.slug + '/',
                            'type': result.model_name,
                            'login_id': result.login_id,
                            # just result.id returns "accounts.employee.10653"
                            'id': int(str(result.id).split('.')[-1])
                            })
    suggestions = sorted(suggestions, key=lambda x: x['name'], reverse=True)
    return suggestions

def organization_search(content):

    sqs = SearchQuerySet().autocomplete(displayname=content).models(Organization)
    suggestions = []
    for result in sqs:
        suggestions.append({'name': result.displayname,
                            'link': '/dashboard/' + result.slug + '/',
                            'type': result.model_name,
                            'id': int(str(result.id).split('.')[-1])
                            })
    suggestions = sorted(suggestions, key=lambda x: x['name'], reverse=True)
    return suggestions


def sat_app_emp_search(content):
    sqs = SearchQuerySet().autocomplete(displayname=content)
    suggestions = []
    for result in sqs:
        suggestions.append({'name': result.displayname,
                            'link': '/dashboard/' + result.slug + '/',
                            'type': result.model_name,
                            #'login_id': result.login_id,
                            'email': result.email,
                            'username': result.username,
                            'id': int(str(result.id).split('.')[-1])
                            })
    suggestions = sorted(suggestions, key=lambda x: x['type'], reverse=True)
    return suggestions


def user_email_search(content):

    #sqs = SearchQuerySet().filter(content=content).exclude(email__isnull=True)
    sqs = SearchQuerySet().autocomplete(displayname=content)
    suggestions = []
    for result in sqs:
        try:
            suggestions.append({'name': result.displayname,
                                'link': '/dashboard/' + result.slug + '/',
                                'org': result.organization_id,
                                'email': result.email,
                                })
        except:
            print("something went wrong")
    # suggestions = sorted(suggestions, key=lambda x: x['type'], reverse=True)
    return suggestions


@csrf_exempt
def ajaxsearch_employee(request):
    content = request.POST.get('q', '')
    print("SUBMITTED", content)
    print("POST", request.POST)
    print("SEARCHING EMPLOYEES")
    suggestions = employee_search(content)
    print(suggestions)
    employees = [s for s in suggestions if s["type"] == "employee"]
    return JsonResponse(employees, safe=False)

@csrf_exempt
def ajaxsearch_organizations(request):
    content = request.POST.get('q', '')
    print("SUBMITTED", content)
    print("POST", request.POST)
    print("SEARCHING ORGANIZATIONS")
    suggestions = organization_search(content)
    print(suggestions)
    # employees = [s for s in suggestions if s["type"] == "employee"]
    return JsonResponse(suggestions, safe=False)



@csrf_exempt
def ajaxsearch_employee_email(request):
    print("SEARCHING FOR EMAILS...")
    content = request.POST.get('q', '')
    print("SUBMITTED", content)
    print("POST", request.POST)
    suggestions = user_email_search(content)
    employees = [s for s in suggestions if s["email"] is not None]
    return JsonResponse(employees, safe=False)


@csrf_exempt
def ajaxsearch(request):
    content = request.POST.get('q', '')
    count = request.POST.get('c', '')
    print("SUBMITTED", content)
    print("POST", request.POST)
    print(count)
    suggestions = general_search(content, count)
    return JsonResponse(suggestions, safe=False)


@csrf_exempt
def ajaxsearch_sat_app(request):
    content = request.POST.get('q', '')
    print("SUBMITTED", content)
    print("POST", request.POST)
    suggestions = sat_app_emp_search(content)
    return JsonResponse(suggestions, safe=False)