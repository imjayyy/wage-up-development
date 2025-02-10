from django.http import HttpResponse
import csv
from django.http import HttpResponse
import csv
from django.contrib import messages
from django.conf import settings
from django.contrib.admin import SimpleListFilter
# from root.dynamoDbQueries import queries
from accounts.models import Employee
import types
import datetime
from backports.zoneinfo import ZoneInfo
from accounts.models import CustomEmail
from django.core.mail import EmailMessage
from collections import defaultdict
from django.db.models import F, Func
import inspect
from django.db.models.fields.files import FieldFile

LAMBDA_EMAILS_ENDPOINT = "https://k8wspgj9xe.execute-api.us-east-1.amazonaws.com/default/wageupEmails-dev-emails"
import requests


def pprint(d, indent=0):
    for key, value in d.items():
        print('\t' * indent + str(key))
        if isinstance(value, dict):
            pprint(value, indent + 1)
        elif isinstance(value, list):
            for l in value:
                if isinstance(l, dict):
                    pprint(l, indent + 1)
                else:
                    print('\t' * (indent + 1) + str(l))
        else:
            print('\t' * (indent + 1) + str(value))


def make_dynamodb_query(query, variables):
    headers = {
        'x-api-key': f'{settings.GAPHQL_API_KEY}'
    }

    request = requests.post(settings.APPSYNC_API_ENDPOINT_URL,
                            json={'query': queries.get(query), 'variables': variables}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        print(headers)
        return "Query failed to run by returning code of {}. {}".format(request.status_code, query)


def send_email(lambda_request):
    resp = requests.post(LAMBDA_EMAILS_ENDPOINT, json=lambda_request)
    return resp.json()


def queryset_object_values(object):
    fields = [field.name for field in list(type(object)._meta.fields)]
    field_values = [(field, getattr(object, field)) for field in fields]
    out = {}
    for field in field_values:
        if isinstance(field[1], FieldFile):
            out[field[0]] = field[1].url
        else:
            out[field[0]] = field[1]
    return out


def download_csv(self, request, queryset):
    filename = self.__class__.__name__ + '.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=' + filename
    row_names = self.list_display
    # row_names = [row for row in row_names if hasattr(queryset[0], row)]
    # print(row_names)
    # print(queryset.values())
    # print(dir(self))
    writer = csv.writer(response)
    writer.writerow([name.upper() for name in row_names])
    for s in queryset:
        row_object_list = []
        for f in row_names:
            try:
                try:
                    attr = getattr(self, f.lower(), "")
                    if attr == "":
                        attr = getattr(s, f.lower(), "")
                    # print(f)
                    # print(type(attr))
                except Exception as e:
                    print(e)
                    attr = ""
                if type(attr) == types.MethodType:

                    try:
                        row_object_list.append(attr(s))
                    except:
                        row_object_list.append("")
                else:
                    row_object_list.append(attr)
            except Exception as e:
                print(e)
                print("attribute couldnt be assigned to csv")
        writer.writerow(row_object_list)
    return response


class InputFilter(SimpleListFilter):
    template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


def send_custom_email(request, obj, email, campaign):
    template = CustomEmail.objects.get(campaign=campaign)
    testing = template.testing
    to_email = [email, 'help@wageup.com']
    if testing:
        to_email = [template.testing_email]
    obj = obj.__dict__
    try:
        message = template.email_body.format(**obj)
    except:
        available_fields = '\n'.join([f'{k} : {v}, ' for k, v in obj.items() if k[0] != '_'])
        messages.error(request,
                       f"That didnt work! You can use the bracket notation {{}} in your custom email fields. available fields for inside brackets is: {available_fields}", )
        return
    print(message)
    mail_subject = template.email_subject
    email = EmailMessage(mail_subject, message, template.from_email, to=to_email)
    email.send()


def flatten_list_of_lists(lol):
    out = []
    for item in lol:
        if type(item) == list:
            for l in item:
                out.append(l)
        else:
            out.append(item)
    return out


def get_val_type(metric_name, val):
    percent_strings = ['freq', 'frequency', 'avg', 'sat']
    number_strings = ['count', 'sum', 'base', 'median', 'total', 'volume']
    if any(st in metric_name.lower() for st in number_strings):
        return 'int'
    if any(st in metric_name.lower() for st in percent_strings):
        return 'percentage'
    if val > 1:
        return 'int'
    return 'percentage'


def clean_val(val, val_type=None, metric_name=None):
    # print(val, val_type)
    if val_type is None:
        return val

    if val_type == 'evaluate':
        val_type = get_val_type(metric_name, val)

    if val_type == 'string':
        return val.replace('_', ' ').title()

    if val is None:
        return 0

    if val_type == 'percentage':
        if val is None:
            return 'N/A'
        return round(val * 100, 2)
    if val_type == 'date':
        if val is None:
            return 'N/A'
        return val.strftime('%Y-%m-%d')
    if val_type == 'int':
        if val is None:
            return 0
        return round(val)
    if val_type == 'dollar':

        if type(val) == str:
            if '$' in val:
                return val
            else:
                if val.isnumeric():
                    return f'${float(val):.2f}'
                else:
                    return val
        else:
            return f'${val:.2f}'


def list_of_dicts_key_order(list_of_dicts, key_order, name_mapping={}, value_mapping={}):
    new_lod = []
    for d in list_of_dicts:
        new_d = {}
        for k in key_order:
            # print(k, d.get(k))
            new_d[name_mapping.get(k, k)] = clean_val(val=d.get(k), val_type=value_mapping.get(k))
        new_lod.append(new_d)
    return new_lod


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 3)'


def local_now(user):
    try:
        org = Employee.objects.get(user=user).organization
        market = org.get_parent_to('Club-Region')
        if market.slug == 'great-plains':
            tz = ZoneInfo('US/Central')
        else:
            tz = ZoneInfo('US/Eastern')
        return datetime.datetime.now(tz=tz)
    except:
        return datetime.datetime.now()


from collections import defaultdict


def combine_dicts(dicts, lookup_field, strict=True, concat_same_key=False):
    print('DICTS', dicts)
    d = defaultdict(dict)
    print('concat same key', concat_same_key)
    try:
        for i in dicts:
            assert type(i[0]) == dict, f"{i} is not a list of dicts"
    except Exception as e:
        print(e)

    for i, q in enumerate(dicts):
        if type(q) == dict:
            q = [q, ]
        q = flatten_list_of_lists(q)
        for elem in q:
            assert type(elem) == dict, f"{elem} in {q} is not a dictionary"
            n = 1
            if strict:
                if i == 2:
                    if elem[lookup_field] is not None and elem[lookup_field] in d:
                        d[elem[lookup_field]].update(elem)
                    else:
                        print(elem[lookup_field], d)
                else:
                    d[elem[lookup_field]].update(elem)
            else:
                if isinstance(concat_same_key, list):
                    for key in concat_same_key:
                        # if elem.get(key) is not None:
                        val = elem.pop(key)
                        existing_val = d[elem[lookup_field]].get(key)
                        if existing_val is not None:
                            if not isinstance(existing_val, list):
                                existing_val = [existing_val]
                            existing_val.append(val)
                            d[elem[lookup_field]][key] = existing_val
                        else:
                            d[elem[lookup_field]][key] = [val]
                else:
                    if elem.get(concat_same_key):
                        val = elem.pop(concat_same_key)
                        existing_val = d[elem[lookup_field]].get(concat_same_key)
                        if existing_val is not None:
                            if not isinstance(existing_val, list):
                                existing_val = [existing_val]
                            existing_val.append(val)
                            d[elem[lookup_field]][concat_same_key] = existing_val
                        else:
                            d[elem[lookup_field]][concat_same_key] = [val]
                d[elem[lookup_field]].update(elem)

    out = sorted(d.values(), key=lambda k: k[lookup_field])
    try:
        print(out[0])
    except Exception as e:
        print(e)
    return out


from django.db import connection
# from dashboard.models import DirectViews
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status

LAMBDA_EXCEL_FROM_REQUEST_ENDPOINT = "https://t7gxv0pkl5.execute-api.us-east-1.amazonaws.com/default/django_to_excel"


class rawSQLView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    # authentication_classes = ()

    # serializer_class = None

    www_authenticate_realm = 'api'

    def post(self, request):
        if request.data.get('options'):
            return Response(list(DirectViews.objects.all().values()))
        self.tableName = request.data.get('tableName')

        self.filter = request.data.get('filter')
        self.no_limit = request.data.get('no_limit')
        self.page = request.data.get('page')
        validTableNames = list(DirectViews.objects.all().values_list('tableName', flat=True))
        print(validTableNames, self.tableName)
        assert self.tableName in validTableNames, "This table name is not allowed!"
        assert ';' not in self.tableName, "That doesnt look right!"
        assert ' ' not in self.tableName, "No Spaces!"
        assert not any(s in self.tableName.lower() for s in ['update', 'insert', 'delete', 'drop', 'truncate', 'alter'])
        if request.data.get('excel'):
            info = DirectViews.objects.get(tableName=self.tableName)
            request = {"sheets": [{
                "request": {"tableName": self.tableName, "filter": {}, "no_limit": True},
                "endpoint": "/client-reports/",
                "conditionalFormatting": None,
                "name": self.tableName,
            }]}
            if info.lambdaOptions is not None:
                request["sheets"][0].update(info.lambdaOptions)
            request['password'] = "C4QwE4hvemtmhLXS"
            s3_link = requests.post(LAMBDA_EXCEL_FROM_REQUEST_ENDPOINT, json=request)
            response = s3_link.json()
            print(response)
            attachmentLink = response['link']
            return Response({"link": attachmentLink})
        return self.getTable()

    def dictfetchall(self, cursor):
        "Return all rows from a cursor as a dict"
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    def filterData(self, data):
        print(data[0])
        if self.filter:
            for k, v in self.filter.items():
                print(k, v)
                if type(v) == list:
                    v = [x.lower() for x in v]
                    data = [d for d in data if {k.lower(): v for k, v in d.items()}.get(k.lower()) in v]
                else:
                    data = [d for d in data if {k.lower(): v for k, v in d.items()}.get(k.lower()) == v]

        if len(data) > 500 and not self.no_limit:
            if self.page:
                return data[self.page * 500: (self.page + 1) * 500]
            else:
                return data[0:500]

        return data

    def getTable(self):

        with connection.cursor() as cursor:
            cursor.execute(f"select * from {self.tableName}")
            data = self.dictfetchall(cursor)

        data = self.filterData(data)

        return Response(data)
