import sys

sys.path.insert(0, 'root')
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from accounts.models import *
from .serializers import *
from .models import *
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from functools import reduce
import operator
from django.db.models import Q
# from gensim.models import Word2Vec
# from training.models import *
from django.db.models import F, Func
from django.db.models.fields import DateField
from django.db.models import Avg, Count, Sum, Min, Max
from django.db.models import Count
from django.db.models import Value as V
import json
import dateutil.relativedelta as relativedelta
# import scipy.stats as ss
from django.db.models import FloatField, F, DecimalField
from django.db.models.functions import Cast, TruncDate, Coalesce, TruncHour, Concat, ExtractHour

from django.db.models import FloatField, ExpressionWrapper
# from onboarding.serializers import *
from django.db.models import Case, CharField, Value, When
# from onboarding.views import GoogleAnalytics as ga
# from messaging.models import *
from .dashboardUtilities import DashboardBase
import itertools
from accounts.actions_logger import ActionsLogger
from django.db.models import BooleanField, IntegerField
from collections import OrderedDict
from collections import defaultdict
from .schedulerUtilities import *
import math
from operator import itemgetter
from datetime import timedelta

class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 3)'

class DaySplit(Func):
    template = """CONVERT(%(expressions)s, DATE)"""

class DashboardRouter(DashboardBase):
    """
        Take as post input:
        :type - i.e. driver, employee, market, grid etc.
        slug - what is the slug of the object. i.e. devin-gonier, vadc
        purpose - what function should be called -- i.e. line_graph, scatterplot etc.
    """

    # note DONT USE THE INIT METHOD, you can update that in dashboardUtilities.py

    def run_training_calcs(self, ob, show_drivers=False):
        station_business_children = self.get_children_to_station_business(ob)
        if station_business_children is None:
            raise Exception("no eligible children")
        training = UserProgress.objects.filter(user__employee__organization__in=station_business_children,
                                               user__employee__position_type='Driver')
        eligible_employees = Dashboard.objects.exclude(
            employee_id__isnull=True).filter(
            parent_id__in=[o.id for o in station_business_children],
            time_type='mtd_prev_3_months', has_tablet_volume__gte=1).count()
        if show_drivers:
            training_values = training.annotate(
                first_name=F('user__employee__first_name'),
                last_name=F('user__employee__last_name'),
                driver_id=F('user__employee__id'),
                driver_slug=F('user__employee__slug')) \
                .values('first_name', 'last_name', 'passed', 'final_grade', 'updated', 'driver_id', 'driver_slug')
        training_count = training.count()
        output = {}
        if not show_drivers:
            output['data'] = [
                {
                    'label': 'Total Drivers',
                    'value': eligible_employees,
                },
                {
                    'label': 'Drivers Completed Training',
                    'value': training_count
                },
                {
                    'label': 'Training Completion Percent (%)',
                    'value': round(training_count / eligible_employees * 100, 1)
                }

            ]

            output['groupName'] = "mtd_prev_3_months"
            output['name'] = ob.name
            output['id'] = ["Organization", ob.id, ob.slug]

        if show_drivers:
            output = []
            for d in training_values:
                driver_dict = {}
                driver_dict['groupName'] = "mtd_prev_3_months"
                driver_dict['name'] = d['first_name'] + ' ' + d['last_name']
                driver_dict['id'] = ["Employee", d['driver_id'], d['driver_slug']]
                driver_dict['data'] = [
                    {
                        'label': 'passed',
                        'value': d['passed']
                    },
                    {
                        'label': 'final_grade',
                        'value': round(d['final_grade'] * 100, 1)
                    },
                    {
                        'label': 'updated',
                        'value': d['updated'].strftime('%Y-%m-%d %H:%M:%S')
                    },
                ]
                output.append(driver_dict)
        return output

    def updateUserGoals(self, parameters):
        if "editOrgGoals" in parameters:
            employee = None
        else:
            employee = self.user.employee()

        try:
            existingGoal = MetricGoals.objects.get(
                metric_id=parameters['metric_id'],
                employee=employee,
                month=parameters['month'],
                organization=self.object)
        except ObjectDoesNotExist:
            existingGoal = False

        if existingGoal:
            existingGoal.target = parameters['target']
            existingGoal.range = parameters['range']
            existingGoal.save()
            return MetricGoalSerializer(existingGoal).data
        else:
            newGoal = MetricGoals(
                metric_id=parameters['metric_id'],
                employee=employee,
                target=parameters['target'],
                month=parameters['month'],
                organization=self.object,
                range=parameters['range'])
            newGoal.save()
            return MetricGoalSerializer(newGoal).data

    def training(self, parameters):
        if parameters['relation'] == 'children':
            output = []

            if self.model_reference == 'Employee':
                return None

            if self.object.type == 'Station':
                self.object = self.object.parent

            if self.object.type == 'Station-Business':
                return self.run_training_calcs(self.object, True)
            else:
                children = self.object.children()
                if children.first() is not Employee:
                    for child in children.exclude(
                            type__in=['Grid', 'Call-Center', 'Call-Center-Group', 'Call-Center-Operator', 'Station',
                                      'Booth']):
                        try:
                            output.append(self.run_training_calcs(child))
                        except:
                            print("couldnt add", child.name)
                    return output
        else:
            return self.run_training_calcs(self.object)

    def survey_comments(self):
        parameters = self.parameters

        filter_sentiment_topics = self.parameters.get('use_sentiment_topic_filter', True)

        relevant_comments = CommentsSurveysE.objects.filter(survey__is_valid_record=True)

        if filter_sentiment_topics:
            relevant_comments = relevant_comments.filter(~Q(survey__survey_e_comment_topics__topic__in=('call_center_operator', 'app', 'IVR', 'coverage'))
                        | Q(sentiment__gt=0.5))
        relevant_comments = relevant_comments.annotate(removed=Case(When(~Q(survey__survey_e_comment_topics__topic__in=('call_center_operator', 'app', 'IVR', 'coverage'))
                        | Q(sentiment__gt=0.5), then=0), default=1, output_field=IntegerField()))

        if 'search' in parameters:
            words_used = []
            search_terms = parameters['search']
            model = Word2Vec.load('static/std12e_bigram.model')
            for term in search_terms:
                this_search = [term, ]
                if 'skip_related_words' not in parameters:
                    try:
                        related_words = model.most_similar(positive=[term])
                        related_words = related_words[:3]
                        for r in related_words:
                            this_search.append(r[0])

                    except:
                        print("couldnt find related words")
                relevant_comments = relevant_comments.filter(
                    reduce(operator.or_, (Q(tokenized_comment__contains=x) for x in this_search)))
                words_used.append(this_search)

        if "sentiment" in parameters:
            relevant_comments = relevant_comments.filter(**parameters['sentiment'])

        # organization
        if self.object.id != 1:  # if its not aca-club
            filter = self.get_index_type(self.object_type)
            filter_query = {'survey__' + filter.lower(): self.object.id}
            print(filter_query)
            # print(len(relevant_comments))
            relevant_comments = relevant_comments.filter(**filter_query)
            print(relevant_comments)
            # print(len(relevant_comments))
        # # dates
        # print("SURVEY COMMENTS", parameters)

        filter_d = {}
        for filter, value in parameters['filters'].items():
            filter_param = 'survey__' + filter
            filter_d[filter_param] = value

        relevant_comments = relevant_comments.filter(**filter_d)

        if "topic" in parameters:
            print("TOPIC IS SET TO", parameters['topic'])
            topic_comments = CommentTopics.objects.filter(topic=parameters['topic']).values('survey_id')
            relevant_comments = relevant_comments.filter(survey_id__in=topic_comments)
            with open('templates/category_words.json', 'r') as f:
                topicJson = json.loads(f.read())
            words_used = [topicJson[parameters['topic']]]

        relevant_comments = relevant_comments.order_by('-survey__sc_dt')[parameters['lower_bound']: parameters['upper_bound']]

        appeals_ineligible_reason = Case(When(Q(survey__sc_svc_prov_type='F'), then=Value('Is Fleet')),
                                              When(Q(survey__overall_sat=1), then=Value('Overall Sat is TS')),
                                              When(Q(survey__q30__isnull=True), then=Value('No Comment')),
                                              When(Q(survey__reroute=1), then=Value('Is a Reroute')),
                                              When(Q(survey__reroute_360=1), then=Value('Is a Reroute')),
                                              When(Q(survey__remove=1), then=Value('December Manual Appeal Removal')),
                                              When(Q(survey__first_spot_delay=1), then=Value('Is already removed by manual appeal')),
                                              When(Q(survey__appeals_request__isnull=False), then=Value('Appeal already submitted')),
                                              When(Q(survey__sc_dt_surveys__lt='2020-12-01'), then=Value('Survey is too old')),
                                              When(Q(survey__duplicate=1), then=Value('Is Duplicate')), default=Value('Is eligible'),
                                              output_field=CharField()
                                              )


        values = ['sentiment',
                    'survey__id',
                    'sc_dt',
                    'recordeddate',
                    'q30',
                    'svc_facl_id',
                    'sc_id', 'driver_name',
                    'overall_sat',
                    'survey__driver10',
                    'survey__emp_driver_id',
                    'survey__emp_driver_id__user__email',
                    'topics_string',
                    'survey__org_business_id__name']

        if not filter_sentiment_topics:
            values.append('removed')


        relevant_comments = relevant_comments.annotate(sc_dt=F('survey__sc_dt_surveys'), q30=F('survey__q30'),
                                                       svc_facl_id=F('survey__svc_facl_id'), sc_id=F('survey__sc_id'),
                                                       overall_sat=F('survey__outc1'),
                                                       recordeddate=F('survey__recordeddate'),
                                                       removed=Min('removed'),
                                                       driver_name=F('survey__driver_name')).values('survey__id', 'sc_dt', 'q30', 'svc_facl_id', 'sc_id', 'overall_sat', 'recordeddate','removed','driver_name' )\
            .values(*values)
        # print('relevant comment', relevant_comments[9])
        output = {'data': relevant_comments}

        if parameters.get('sheet_name'):
            output['sheet_name'] = parameters.get('sheet_name')

        if 'search' in parameters or 'topic' in parameters:
            output['query_terms_used'] = words_used

        return output

    def clean_filter_dict(self, filter):
        swap_filter = {}
        for filter, value in filter.items():
            if type(value) == list and '__in' not in filter:
                filter = filter + '__in'
                if len(value) > 0:
                    swap_filter[filter] = value
                else:
                    continue
            if value == 'unknown':
                filter = filter + '__isnull'
                value = True
                swap_filter[filter] = value
            else:
                swap_filter[filter] = value
        return swap_filter

    def surveys__emulated_surveys(self):
        print('emulated_surveys')
        question_serializer = Std12ESerializerQuestions(RawStd12EQuestions.objects.all(), many=True)
        surveys = self.surveys.extra(
            select={'spot_minutes': "ROUND(TIMESTAMPDIFF(SECOND, FST_SPOT_TIME, LST_SPOT_TIME)/60, 1)"})
        surveys = surveys.annotate(first_spot_fac=F('fst_shop'))
                                   # appeals_eligible=self.appeals_eligible_annotation,
                                   # appeals_status=F('appeals_request__request_data__status'),
                                   # appeals_eligible_reason=self.appeals_ineligible_reason,)

        # print(surveys.values('sc_svc_prov_type', 'overall_sat', 'q30', 'reroute', 'reroute_360', 'first_spot_delay',
        #     'remove', ,'sc_dt', 'duplicate')),

        surveys = surveys.order_by('sc_dt')

        if self.parameters.get('appeals_eligible_only'):
            surveys = surveys.filter(appeals_eligible=True)

        if self.parameters.get('appeals_submitted_only'):
            surveys = surveys.filter(appeals_status__isnull=False)


        if self.last_n:
            surveys = surveys.order_by('-sc_dt_surveys')[:int(self.last_n)]
        elif 'sc_id_surveys' in self.filters:
            print('sc_id_surveys')
            pass
        else:
            surveys = surveys[self.parameters['lower_bound']: self.parameters['upper_bound']]

        emulated_surveys = surveys.values('id', 'sc_dt', 'emp_driver_id__slug', 'emp_driver_id', 'emp_driver_id__display_name', 'org_business_id__name',
                                          'outc1', 'q30', 'driver10', 'driver5', 'desc2', 'q26', 'q24', 'sc_id',
                                          'check_id_compliant','call_center_operator', 'cm_trk', 'dispatch_communicated', 'ata',
                                          'pta', 'ata_minus_pta', 're_tm', 'tcd', 'sc_dt_surveys',
                                          'sc_id_surveys', 'spot_minutes', 'first_spot_fac',
                                          'org_svc_facl_id__name', 'recordeddate')

        for s in emulated_surveys:
            try:
                s['sc_id'] = s['sc_id_surveys']
                s['sc_dt'] = s['sc_dt_surveys'].strftime('%Y-%m-%d')
                s['re_tm'] = s['re_tm'].strftime('%Y-%m-%d %H:%M:%S')
            except:
                print(s)

        output = {'data': list(emulated_surveys), 'metadata': question_serializer.data}
        return output

    def surveys__qa(self):
        print('qa')
        fk_lookup = {
            'Stations': 'org_svc_facl_id',
            'Drivers': 'emp_driver_id',
            'Station-Business': 'org_business_id'
        }
        fk = fk_lookup[self.parameters.get('org_type')]
        g = {
            'Stations': [fk, f'{fk}__name', f'{fk}__parent_id',f'{fk}__slug', f'{fk}__facility_type'],
            'Drivers': [fk, f'{fk}__full_name', f'{fk}__organization__name',f'{fk}__slug', f'{fk}__raw_data_driver_id'],
            'Station-Business': [fk, f'{fk}__name', f'{fk}__parent_id',f'{fk}__slug', f'{fk}__facility_type'],
        }
        g['Driver-Station'] = g['Drivers'] + g['Stations']

        self.agg_params['reroute_count'] = Sum('reroute')
        self.agg_params['osat_no_reroute'] = Avg('overall_sat')
        self.agg_params['max_sc_dt'], self.agg_params['min_sc_dt'], = Max('sc_dt_surveys'), Min('sc_dt_surveys')

        if self.parameters.get('org_type') == 'Drivers':
            self.agg_params['state'] = F(f'{fk}__organization__parent_id')
            self.agg_params['tier_fac_type'] = F(f'{fk}__organization__facility_type')
        else:
            self.agg_params['state'] = F(f'{fk}__parent_id')
            self.agg_params['tier_fac_type'] = F(f'{fk}__facility_type')

        out = self.surveys.values(*g[self.parameters.get('org_type')]).annotate(**self.agg_params)

        out = map(self.assign_survey_tier, out)
        out = list(out)

        filters_applied = self.clean_survey_filters()

        return {'data': out, 'filters': filters_applied, 'sheet_name': self.parameters.get('sheet_name')}

    def surveys__children(self):
        print('surveys_children')
        print(self.agg_params)
        if self.model_reference != 'Employee':
            if self.index_type != 'Club':
                self.surveys = self.surveys.filter(**{self.get_index_type(self.index_type).lower(): self.object.id})
            child_type = (self.get_index_type(self.parameters.get('child_type')) or self.default_children(self.object.type)).lower()
            child_type = 'emp_driver_id' if 'fleet-drivers' in self.parameters else child_type
            name_suffix = '__name' if child_type[:3] == 'org' else '__full_name'
            grouping = child_type if child_type in ['bl_near_cty_nm', 'bl_state_cd'] else f'{child_type}{name_suffix}'
            if child_type == 'org_svc_facl_id':
                self.surveys = self.surveys.annotate(name=F(grouping), slug=F(child_type + '__slug'),
                                           parent_territory=F(child_type + '__grandparent__name')).values('name',
                                                                                                          'slug',
                                                                                                          'parent_territory').annotate(
                    **self.agg_params)
            elif child_type in ['bl_near_cty_nm', 'bl_state_cd']:
                self.surveys = self.surveys.annotate(name=F(grouping)).values('name').annotate(**self.agg_params)
            else:
                print('grouping is: ', grouping, child_type)

                if self.parameters.get('ranking'):
                    self.agg_params['facility_type'] = F('org_svc_facl_id__facility_type')

                self.surveys = self.surveys.annotate(name=F(grouping), slug=F(child_type + '__slug'),
                                           record_id=F(child_type + '_id')).values('name', 'slug',
                                                                                   'record_id').annotate(
                    **self.agg_params)

            osat_no_rules_avg = list(self.pre_exclusion_surveys.values(name=F(grouping)).annotate(osat_no_rules_avg=Avg('overall_sat')).values('name', 'osat_no_rules_avg'))
            # print(osat_no_rules_avg)
            d = defaultdict(dict)
            for i, q in enumerate([self.surveys, osat_no_rules_avg]):
                for elem in q:
                    if i == 1:
                        if elem['name'] is not None and elem['name'] in d:
                            d[elem['name']].update(elem)
                    else:
                        d[elem['name']].update(elem)
            # print(d.values())
            if self.parameters.get('ranking'):

                default_response = {
                    "name": "n/a",
                    "slug": "na-non-slug",
                    "record_id": 0,
                    "response_sat_avg": 0,
                    "response_sat_count": 0,
                    "overall_sat_avg": 0,
                    "overall_sat_count": 0,
                    "facility_sat_avg": 0,
                    "driver_sat_count": 0,
                    "request_service_sat_avg": 0,
                    "request_service_sat_count": 0,
                    "kept_informed_sat_avg": 0,
                    "kept_informed_sat_count": 0,
                    "facility_type": "FLEET",
                    "total_ranking": 1,
                    "rank": 1
                }

                user_emp = self.request.user.employee()

                if user_emp.position_type != 'Driver':
                    return [default_response]

                if self.object.type in ['Club']:
                    return [default_response]

                print(user_emp.slug)
                if user_emp.organization.type == 'Station-Business':
                    fac_type = self.parameters.get('fac_type', user_emp.organization.facility_type)
                    if fac_type is not None:
                        fac_types = ['fleet'] if fac_type.lower() == 'fleet' else ['psp', 'non-psp', None]
                    else:
                        fac_types = ['psp', 'non-psp', None]
                    ranked = list(filter(lambda d: d['overall_sat_count'] >=5 and d['facility_type'].lower() in fac_types if d['facility_type'] is not None else None in fac_types,  self.surveys))
                else:
                    ranked = list(filter(lambda d: d['overall_sat_count'] >=5,  self.surveys))
                unranked = list(filter(lambda d: d['overall_sat_count'] <5,  self.surveys))


                ranked = sorted(ranked, key=lambda k: (k['overall_sat_avg'],
                                                                 k['overall_sat_count'],
                                                                 k['facility_sat_avg'],
                                                                 k['driver_sat_count'],
                                                                 ), reverse=True)
                # [d.update({'rank': r+1, 'total_ranking': len(ranked)}) for r, d in enumerate(ranked)]
                total_ranking = len(ranked)
                for i, k in enumerate(ranked):
                    ranked[i]['total_ranking'] = total_ranking
                    if i == 0:
                        ranked[i]['rank'] = 1
                        continue
                    p = ranked[i-1]
                    this_driver = (k['overall_sat_avg'],
                         k['overall_sat_count'],
                         k['facility_sat_avg'],
                         k['driver_sat_count'])
                    prev_driver = (p['overall_sat_avg'],
                         p['overall_sat_count'],
                         p['facility_sat_avg'],
                         p['driver_sat_count'])
                    if this_driver == prev_driver:
                        ranked[i]['rank'] = ranked[i-1]['rank']
                    else:
                        ranked[i]['rank'] = ranked[i-1]['rank'] + 1

                [d.update({'rank': 'N/A', 'total_ranking': total_ranking}) for r, d in enumerate(unranked)]
                my_rank = list(filter(lambda x: x['slug'] == user_emp.slug, ranked))
                my_unrank = list(filter(lambda x: x['slug'] == user_emp.slug, unranked))

                return my_rank + my_unrank

            else:
                self.surveys = sorted(d.values(), key=lambda k: k['name'])

            remove_cols = ['reroute_360_count', 'sister_reroute_count',
                           'first_spot_delay_count', 'pending_appeal_count',
                           'rejected_appeal_count', 'approved_appeal_reroute_count',
                           'approved_appeal_remove_count', 'response_sat_count',
                           'kept_informed_sat_count', 'request_service_sat_count', 'perf_metrics_used']


            output = self.clean_up_surveys_list(self.surveys, remove_cols=remove_cols)
            filters_used = self.clean_survey_filters()
            filters_used['LAST UPDATED: '] = self.last_update

            return output if output is not None else []
        else:
            return []

    def surveys__topic_aggregator(self):
        print('topic aggregator')
        parameters = self.parameters
        topic_comments = CommentTopics.objects
        # organization
        if self.object.id != 7:  # if its not aca-club
            filter = self.get_index_type(self.object_type)
            filter_query = {'survey__' + filter.lower(): self.object.id}
            topic_comments = topic_comments.filter(**filter_query)

        filter_d = {}
        for filter, value in self.filters.items():
            filter_param = 'survey__' + filter
            if type(value) == list and '__in' not in filter:
                filter_param = filter_param + '__in'
            filter_d[filter_param] = value

        print("COMMENT FILTERS", filter_d)
        topic_comments = topic_comments.filter(**filter_d)

        if "sentiment" in parameters:
            topic_comments = topic_comments.filter(**parameters['sentiment'])

        topic_data = topic_comments.values('topic').annotate(count=Count('topic'),
                                                             avg_sentiment=Avg('sentiment'))
        print("TOPIC DATA", topic_data)
        topics = {}
        out = []
        for t in topic_data:
            topics[t['topic']] = t
        for topic, data in topics.items():
            print(data)
            out.append(
                {
                    'name': topic.upper(),
                    'data': [{'label': 'count', 'djangoLabel': 'Comment Count', 'value': data['count']},
                             {'label': 'avg_sentiment', 'djangoLabel': 'Average Sentiment',
                              'value': data['avg_sentiment']}]
                }
            )
        return out

    def surveys__raw_records(self):
        parameters = self.parameters
        surveys = self.surveys
        print('raw records')
        surveys = surveys.extra(
            select={'spot_minutes': "ROUND(TIMESTAMPDIFF(SECOND, FST_SPOT_TIME, LST_SPOT_TIME)/60, 1)"})
        surveys = surveys.annotate(first_spot_fac=F('fst_shop'),
                                   # appeals_eligible=self.appeals_eligible_annotation,
                                   # appeals_status=F('appeals_request__request_data__status'),
                                    # appeals_eligible_reason = self.appeals_ineligible_reason,
                                   )



        conversions = OrderedDict({
            # 'q_chl': 'q_chl',
            'facility_id': 'sp_fac_id',
            'facility_name': 'org_business_id__name',
            'service_date': 'sc_dt_surveys',
            'call_id': 'sc_id_surveys',
            'survey_recorded': 'recordeddate',
            # 'territory_name': 'org_territory_id__name',
            'driver': 'emp_driver_id__full_name',
            'auto_reroute': 'auto_reroute',
            'auto_remove': 'auto_remove',
            'service_resolution': 'resolution_desc',
            'trouble_type': 'tlc_desc',
            'overall_satisfaction': 'outc1',
            'driver_sat': 'driver10',
            'response_time': 'q24',
            'kept_informed': 'q26',
            'requesting_service': 'driver5',
            'pta': 'pta',
            'ata': 'ata',
            'driver_called': 'driver_called',
            'spot_minutes': 'spot_minutes',
            'first_spot_fac': 'first_spot_fac',
            'verbatim': 'q30',
            # 'fleet_supervisor_name': 'fleet_supervisor__full_name',
            'survey_id': 'id',
            # 'appeals_eligible': 'appeals_eligible',
            # 'appeals_status': 'appeals_status',
            # 'appeals_eligible_info': 'appeals_eligible_reason'
        })

        if 'search_field' in parameters:
            for field, search_value in parameters['search_field'].items():
                if field == 'appeals_eligible':
                    s_val = search_value.lower() in 'yes'
                    surveys = surveys.filter(appeals_eligible=s_val)
                if field == 'auto_reroute':
                    if search_value.lower() in 'yes':
                        surveys = surveys.filter(~Q(sc_svc_prov_type='F') & Q(reroute_360=1) & Q(sister_reroute=0))
                        # Case(When(~Q(sc_svc_prov_type='F') & Q(reroute_360=1) & Q(sister_reroute=0), then=Value('Yes')),
                        #      When(first_spot_delay=1, then=Value('Yes')), default=Value('No'),
                        #      output_field=CharField()),
                    else:
                        surveys = surveys.exclude(
                            ~Q(sc_svc_prov_type='F') & Q(reroute_360=1) & Q(sister_reroute=0) | Q(first_spot_delay=1))
                if field == 'auto_remove':
                    if search_value.lower() in 'yes':
                        surveys = surveys.filter(~Q(sc_svc_prov_type='F') & Q(duplicate=1))
                        # Case(When(~Q(sc_svc_prov_type='F') & Q(reroute_360=1) & Q(sister_reroute=0), then=Value('Yes')),
                        #      When(first_spot_delay=1, then=Value('Yes')), default=Value('No'),
                        #      output_field=CharField()),
                    else:
                        surveys = surveys.exclude(
                            ~Q(sc_svc_prov_type='F') & Q(duplicate=1))

                else:
                    print('search field object', parameters['search_field'])
                    searchParams = {conversions[field] + '__icontains': search_value}
                    print('search parameters', searchParams)
                    surveys = surveys.filter(**searchParams)

        if 'sort_field' in parameters:
            if parameters['sort_direction'] == 'asc':
                surveys = surveys.order_by(conversions[parameters['sort_field']])
            else:
                surveys = surveys.order_by('-' + conversions[parameters['sort_field']])
        else:
            surveys = surveys.order_by('-sc_dt_surveys')

        survey_length = surveys.count()

        if 'lower_bound' in parameters:
            surveys = surveys[parameters['lower_bound']: parameters['upper_bound']]
        else:
            if survey_length > 250 and not ('unboundOverride' in parameters):
                return {'Warning': "<p>There are too many surveys. There are " + str(
                    survey_length) + " in total. The limit is set to 250 when sending Emails.</p>"
                                     "<p>Please constrain your query by modifying the filter parameters (e.g. date). "
                                     "Loading too many surveys for the purposes of sending an email can crash your browser. "
                                     "If you just hit the email button, then limit your search and try again.</p>"
                                     "<p><b> HINT:</b> "
                                     "You can however export all of them as an excel file using the Export ALL as XLS button.</p>"}

        annotation_d = {}
        [annotation_d.update({k: F(v)}) for k,v in conversions.items() if k != v]
        annotation_d.update({
            'driver_called': Case(When(cm_trk=1, then=Value('Yes')),
                                  When(cm_trk=0, then=Value('No')),
                                  default=Value('No'), output_field=CharField()),
            'auto_reroute': Case(When(~Q(sc_svc_prov_type='F') & Q(reroute_360=1) & Q(sister_reroute=0), then=Value('Yes')),
                                 When(first_spot_delay=1, then=Value('Yes')), default=Value('No'),
                                 output_field=CharField()),
            'auto_remove': Case(When(~Q(sc_svc_prov_type='F') & Q(duplicate=1), then=Value('Yes')), default=Value('No'), output_field=CharField()),
        })
        vals = list(conversions.keys()) + ['driver_called']
        # print("QUERY IS: ", surveys.annotate(**annotation_d).query)
        raw_records = list(surveys.annotate(**annotation_d).values(*vals))

        for s in raw_records:
            s['response_time_sat'] = self.survey_response_mapping(s['response_time'])
            s['kept_informed_sat'] = self.survey_response_mapping(s['kept_informed'])
            s['requesting_service_sat'] = self.survey_response_mapping(s['requesting_service'])
            s['overall_satisfaction'] = self.survey_response_mapping(s['overall_satisfaction'])
            s['driver_sat'] = self.survey_response_mapping(s['driver_sat'])
            s['service_date'] = s['service_date'].strftime('%Y-%m-%d') if s['service_date'] is not None else None
            s['survey_recorded'] = s['survey_recorded'].strftime('%Y-%m-%d') if s['survey_recorded'] is not None else None

            for d in ['requesting_service', 'kept_informed', 'response_time']:
                del s[d]

            # if self.fac_type != 'fleet':
            #     del s['fleet_supervisor_name']

        filters_applied = self.clean_survey_filters()

        return [filters_applied, raw_records, survey_length]

    def surveys__comp_timeseries(self):
        how_many = self.parameters.get('comp_timeseries_count')
        print('how_many', how_many)
        current_period = Std12ETierTimePeriods.objects.filter(type=self.fac_type, show_until__gte=dt.datetime.today()).order_by(
            'start')[0]
        periods = Std12ETierTimePeriods.objects.filter(type=self.fac_type, show_until__lt=dt.datetime.today()).order_by(
            '-start')[:how_many-1]
        print(current_period)
        final_out = []
        final_out = self.update_periods(current_period, final_out)
        for period in periods:
            final_out = self.update_periods(period, final_out)
        print('SURVEY TIME SERIES FINAL OUT', final_out)
        return final_out

    def update_periods(self, period, final_out):
        surveys = self.surveys
        self.period, self.comp_period = period, period
        time_filters = {
            'sc_dt_surveys__gte': period.start,
            'sc_dt_surveys__lte': period.end,
            'date_updated_surveys__lte': period.recorded_cutoff_time,
        }
        print(time_filters)

        surveys = surveys.filter(**time_filters).aggregate(**self.agg_params)
        osat_no_rules_avg = self.pre_exclusion_surveys.filter(**time_filters).aggregate(
            osat_no_rules_avg=Avg('overall_sat'), osat_no_rules_count=Count('overall_sat'))
        surveys.update(osat_no_rules_avg)

        period_out = self.clean_up_surveys_list(surveys)[0]
        period_out['period_start'], period_out['period_end'], period_out[
            'cutoff'] = period.start, period.end, period.recorded_cutoff_time
        final_out.append(period_out)
        return final_out

    def single_survey(self, parameters):
        survey = Std12EReduced.objects.filter(id=parameters.get('survey_id'))
        emulated_survey = survey.values('id', 'sc_dt', 'emp_driver_id__slug', 'emp_driver_id__display_name',
                                          'outc1', 'q30', 'driver10', 'driver5', 'desc2', 'q26', 'q24', 'sc_id',
                                          'check_id_compliant','call_center_operator', 'cm_trk', 'dispatch_communicated', 'ata',
                                          'pta', 'ata_minus_pta', 're_tm', 'tcd', 'sc_dt_surveys',
                                          'sc_id_surveys')
        print('THE ONE SURVEY WE ARE RETURNING', emulated_survey)
        return emulated_survey

    def get_num_denom(self, metric):
        print('metric changes', metric)
        to_replace = 'avg' if 'avg' in metric else 'freq'
        denom, num = metric.replace(to_replace, 'count'), metric.replace(to_replace, 'sum')

        special_denoms = {
            'battery_opp_ata_avg': ('battery_ata_sum', 'battery_volume'),
            'batt_truk_avg': ('batt_truck_num', 'num_ops'),
            'test_rate_avg': ('matched_tests', 'num_ops'),
            'edocs_conv_avg': ('edocs_count', 'num_ops'),
            'edocs_avg': ('edocs_count', 'edocs_denom'),
            'vin_avg': ('vin_count', 'matched_tests'),
            'battery_ol_to_clr_avg': ('battery_ol_to_clr_sum', 'battery_volume')
        }
        if metric in special_denoms.keys():
            return special_denoms[metric][1], special_denoms[metric][0]

        if getattr(DashboardBatteryAggregations, denom, False) and getattr(DashboardBatteryAggregations, num, False):
            return denom, num
        elif not getattr(DashboardBatteryAggregations, denom, False):
            return ExpressionWrapper(
                F(num) / F(metric), output_field=FloatField()), num
        elif not getattr(DashboardBatteryAggregations, num, False):
            return denom, ExpressionWrapper(
                F(denom) * F(metric), output_field=FloatField())

    def annotation_grouper(self, metric, newName=False):
        print(metric, newName)
        if not newName: newName = metric
        if 'freq' in metric or 'avg' in metric:
            denom, num = self.get_num_denom(metric)
            # print(denom, num)
            return {
                newName: ExpressionWrapper(Sum(num) / Sum(denom), output_field=FloatField())
            }
        if 'median' in metric:
            # this is an average of medians... not too good
            return {
                newName: Avg(metric)
                # newName: ExpressionWrapper(Avg(
                #     ExpressionWrapper(F(metric) * F('volume'), output_field=FloatField())
                # ) / F('volume'), output_field=FloatField())
            }
        else:
            return {
                newName: Sum(metric)
            }

    def battery_aggregator(self, parameters):
        agg_params = {}
        for metric in ['num_ops', 'test_rate_avg', 'edocs_count', 'edocs_conv_avg', 'edocs_avg',
                       'vin_avg', 'comp_battery_overall_sat_avg', 'comp_battery_overall_sat_count']:
            agg_params.update(self.annotation_grouper(metric))

        today = dt.date.today()
        current_month = today.month
        timeseries_count = range(parameters.get('timeseries_count'))
        print('TIMESERIES COUNT', timeseries_count)
        battery_output = []

        if hasattr(self.object, 'position_type'):
            print('CURRENT MONTH', current_month)
            for count in timeseries_count:
                month_filter = current_month
                if  month_filter - count < 1:
                    month_filter = 12 + (month_filter - count)
                else:
                    month_filter = month_filter - count
                battery_metric_month = DashboardBatteryAggregations.objects.filter(sc_dt__month=month_filter,
                                                                                   index_type='EMP_DRIVER_ID',
                                                                                   employee_id=self.request.user.employee(),
                                                                                   time_type='D')
                battery_metric_month = battery_metric_month.aggregate(**agg_params)
                battery_output.append(battery_metric_month)

        else:
            for count in timeseries_count:
                battery_metric_month = DashboardBatteryAggregations.objects.filter(sc_dt__month=current_month - count,
                                                                                   organization_id=self.request.user.employee().organization,
                                                                                   time_type='D')
                battery_metric_month = battery_metric_month.aggregate(**agg_params)
                battery_output.append(battery_metric_month)
        print('BATTERY OUTPUT', battery_output)
        return battery_output

    def mtk_campaign_survey_month_data(self, parameters):
        if self.object_type in self.organization_types:
            try:
                organization_score = self.queryset.get(time_type='M', sc_dt='2024-05-01').comp_any_overall_sat_avg
            except ObjectDoesNotExist:
                organization_score = None
            except MultipleObjectsReturned:
                organization_score = None

            return {'organization_score': organization_score}
        if self.object_type in self.employee_types:
            try:

                # Get the current date and time
                now = dt.datetime.now()

                # Check if the current day is greater than the 15th
                if now.day > 15:
                    # First day of the current month
                    first_day = dt.datetime(now.year, now.month, 1)
                else:
                    # First day of the previous month
                    # Handle the transition to the previous month
                    first_day_of_current_month = dt.datetime(now.year, now.month, 1)
                    first_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
                    first_day = dt.datetime(first_day_of_previous_month.year, first_day_of_previous_month.month, 1)

                # biz rules on
                #
                driver_score = self.queryset.get(time_type='M', sc_dt=first_day.strftime('%Y-%m-%d')).comp_any_overall_sat_avg
                ts_survey_count = self.queryset.get(time_type='M', sc_dt=first_day.strftime('%Y-%m-%d')).comp_any_overall_sat_sum
                #
                # biz rules offc

                # driver_score = self.queryset.get(time_type='M', sc_dt=first_day.strftime('%Y-%m-%d')).aaa_mgmt_any_overall_sat_avg
                # ts_survey_count = self.queryset.get(time_type='M', sc_dt=first_day.strftime('%Y-%m-%d')).aaa_mgmt_any_overall_sat_sum



            except ObjectDoesNotExist:
                driver_score = None
                ts_survey_count = None
            except MultipleObjectsReturned:
                driver_score = None
                ts_survey_count = None
            return {'driver_score': driver_score, 'ts_survey_count': ts_survey_count}
    def survey_aggregator(self, parameters):
        today = dt.date.today()
        current_month = today.month
        print('CURRENT MONTH', current_month)
        print('SURVEY AGG FIRED', parameters)
        filters = parameters.get('filters', {}) # what we wanna keep
        print('original filters', filters)

        self.filters_original_values = {}

        if filters.get('date_updated_surveys__lte'):
            # fix date cutoffs here, because we want the very beginning of the next day (i.e. less than)
            self.filters_original_values['date_updated_surveys__lte'] = filters['date_updated_surveys__lte']
            filters['date_updated_surveys__lte'] = (dt.datetime.strptime(filters['date_updated_surveys__lte'], '%Y-%m-%d') + relativedelta.relativedelta(days=1)).strftime("%Y-%m-%d")

        self.distribution_exclusion = Q(distribution='SMS') & Q(sc_dt_surveys__lt='2022-05-01')

        exclusions = {} # what we wanna remove
        exclusions_but_osat = {}
        today = dt.date.today()

        surveys = Std12EReduced.objects.filter(is_valid_record=True)

        self.last_update = Std12EReduced.objects.aggregate(max_db_updated=Max('date_updated_surveys'))[
            'max_db_updated'].strftime("%b-%d")

        # rule switching

        self.apply_business_rules = self.object_type in ['Driver', 'Station', 'Station-Business']
        print("business rules are set to", self.apply_business_rules)

        if 'qa' in parameters:
            self.apply_business_rules = True

        if 'biz_rules' in parameters:
            self.apply_business_rules = parameters['biz_rules']
        # facility type ...

        org = self.object if self.model_reference == 'Organization' else self.object.organization
        self.fac_type = 'fleet' if org.facility_type == 'Fleet' else 'csn'
        if 'fac_type__in' in filters or 'sc_svc_prov_type__in' in filters:
            self.fac_type = 'fleet' if filters.get('sc_svc_prov_type__in') == ['F'] else 'csn'
        if 'fac_type' in parameters:
            self.fac_type = parameters.get('fac_type')
            surveys = surveys.exclude(sc_svc_prov_type='F') if self.fac_type == 'csn' else surveys.filter(sc_svc_prov_type='F')

        # get survey period information

        period = \
            Std12ETierTimePeriods.objects.filter(start__lte=today, show_until__gt=today, type=self.fac_type).order_by(
                'start')[0]

        self.comp_period = period

        self.apply_period_filters = ('comp' in parameters and 'last_n' not in filters) or \
                (('sc_dt_surveys__gte' not in filters and 'sc_dt_surveys__lte' not
                  in filters) and 'last_n' not in filters) \
                                    # or ('ranking' in parameters)

        default_exclusions = {}

        # apply default parameters

        if self.apply_business_rules:
            parameters['reroute_filter_applied'] = True

            default_exclusions_but_osat ={
                'reroute':  {'with_ts_val': True},
            }

            if parameters.get('reroute') == False:
                del default_exclusions_but_osat['reroute']

        else:
            default_exclusions_but_osat = {}

        [exclusions.setdefault(k, v) for k, v in default_exclusions.items()]
        [exclusions_but_osat.setdefault(k, v) for k, v in default_exclusions_but_osat.items()]


        # handle special filters related to remove and reroute

        if 'remove' in parameters:
            if parameters.get('remove') == 'auto':
                if 'appeals_request__request_data__status' in exclusions: del exclusions['appeals_request__request_data__status']
                if 'remove' in exclusions: del exclusions['remove']
                exclusions['duplicate'] = True
            elif parameters.get('remove') == 'appealed':
                exclusions['appeals_request__request_data__status'] = 'Approved-Remove'
                if 'duplicate' in exclusions: del exclusions['duplicate']
            elif parameters.get('remove') == 'appealed_auto':
                exclusions.update({
                    'duplicate': parameters.get('duplicate', True),
                    'appeals_request__request_data__status': 'Approved-Remove',
                    'remove': True,
                })
            elif parameters.get('remove') == 'none':
                exclusions = {}
            print("REROUTE USER CRITERIA", parameters.get('remove'), exclusions)


        if 'reroute' in parameters:
            if parameters.get('reroute') == 'auto':
                exclusions_but_osat = {
                    'reroute_360': {'with_ts_val': True, 'caveat_m': 'sister_reroute',
                                    'caveat_val': parameters.get('sister_reroute', True)},
                    'first_spot_delay': {'with_ts_val': True},
                }
            elif parameters.get('reroute') == 'appealed':
                exclusions_but_osat = {
                    'appeals_request__request_data__status': {'with_ts_val': 'Approved-Reroute'}
                }
            elif parameters.get('reroute') == 'appealed_auto':
                exclusions_but_osat = {
                    'reroute_360': {'with_ts_val': True, 'caveat_m': 'sister_reroute',
                                    'caveat_val': parameters.get('sister_reroute', True)},
                    'first_spot_delay': {'with_ts_val': True},
                    'appeals_request__request_data__status': {'with_ts_val': 'Approved-Reroute'}
                }
            elif parameters.get('reroute') in ('NONE', 'none'):
                exclusions_but_osat = {}

            print("REROUTE USER CRITERIA", parameters.get('reroute'), exclusions_but_osat)

        if exclusions_but_osat.get('reroute', exclusions_but_osat.get('reroute_360')) == 'show_only_reroutes':
            filters['reroute'], filters['reroute_360'] = True, True

        default_filters = {}

        if parameters.get('comp_timeseries'):
            print("not applying sc_dt filters")

        elif self.apply_period_filters:
            default_filters.update({
                'sc_dt_surveys__gte': period.start.strftime("%Y-%m-%d"),
                'sc_dt_surveys__lte': period.end.strftime("%Y-%m-%d"),
                'date_updated_surveys__lte': period.recorded_cutoff_time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            default_filters.update({
                'sc_dt_surveys__gte': "2020-01-01",
                'sc_dt_surveys__lte': dt.date.today().strftime("%Y-%m-%d"),
                'date_updated_surveys__lte': (dt.date.today() + relativedelta.relativedelta(days=1)).strftime("%Y-%m-%d"),
            })

        [filters.setdefault(k, v) for k, v in default_filters.items()]

        # various exceptions as arguments in parameters

        if 'unseenSurveys' in parameters and not ('lastEmailSurveys' in parameters):
            import json
            lastSession = ga.get_user_data(ga, {'user': str(self.user.id)})['sessions']
            lastSession = \
                [s['sessionDate'] for s in lastSession if
                 str(s['sessionDate']) != dt.date.today().strftime("%Y-%m-%d")][0]
            filters['date_updated_surveys__gte'] = lastSession

        if 'lastEmailSurveys' in parameters:
            print(parameters)
            lastEmail = EmailLogs.objects.filter(generated_by_id=parameters['send_to_id'], type='newSurveys')
            lastEmail = lastEmail.order_by('-date_delivered')[0].date_delivered
            print('LAST EMAIL', lastEmail)
            filters['date_updated_surveys__gte'] = lastEmail.strftime("%Y-%m-%d")

        if 'last_n_days' in parameters:
            filters['sc_dt_surveys__lte'] = dt.date.today().strftime("%Y-%m-%d")
            filters['sc_dt_surveys__gte'] = (
                    dt.date.today() - dt.timedelta(days=int(parameters['last_n_days']))).strftime("%Y-%m-%d")

        self.last_n = filters.get('last_n') or parameters.get('last_n')
        if 'last_n' in filters:
            del filters['last_n']

        # clean filters
        filters, exclusions = self.clean_filter_dict(filters), self.clean_filter_dict(exclusions)
        print('filters', filters)
        print('exclusions', exclusions)
        surveys = surveys.filter(**filters)


        print('fixing date updated filter string')

        if self.index_type != 'Club' and 'qa' not in parameters:
            surveys = surveys.filter(**{self.get_index_type(self.index_type).lower(): self.object.id})

            if parameters.get('emp_org'):
                surveys = surveys.filter(org_business_id=parameters.get('emp_org'))

        self.pre_exclusion_surveys = surveys

        if self.last_n:
            surveys = surveys.filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))

        for k,v in exclusions.items():
            print('excluding', k, v)
            surveys = surveys.exclude(**{k: v})

        agg_params = {
        }

        print("filters", filters, "exclusions", exclusions, "exclusions_but_osat", exclusions_but_osat)

        # create aggregation info
        for metric in ['response_sat', 'overall_sat', 'facility_sat', 'request_service_sat', 'kept_informed_sat']:
            cond = None
            new_name = 'driver_sat' if metric == 'facility_sat' else metric
            for k,v in exclusions_but_osat.items():
                with_ts_val = v['with_ts_val']
                sat_cond = (Q(**{k: with_ts_val}) & Q(**{metric:1}))
                is_null_condition = Q(**{f'{k}__isnull': True})
                if type(with_ts_val) == bool:
                    no_ts_cond = Q(**{k: not with_ts_val})
                else:
                    no_ts_cond = ~Q(**{k: with_ts_val})
                if 'caveat_m' in v:
                    no_ts_cond = (Q(**{k: not with_ts_val}) | Q(**{v['caveat_m']: v['caveat_val']}))
                comb_cond = (no_ts_cond | is_null_condition | sat_cond)
                cond = cond & comb_cond if cond is not None else comb_cond
                # print(cond)
            if cond is not None:
                agg_params.update({
                    f'{metric}_avg': Round(Avg(metric, filter=(cond)))
                })
                agg_params.update({
                    f'{new_name}_count': Count(metric, filter=(cond))
                })
            else:
                agg_params.update({
                    f'{metric}_avg': Round(Avg(metric))
                })
                agg_params.update({
                    f'{new_name}_count': Count(metric)
                })

        print(agg_params)
        # print('filters', filters, 'exclusions', exclusions, 'agg_params', agg_params)

        # various request types


        self.appeals_eligible_annotation = Case(When(
            ~Q(sc_svc_prov_type='F') & ~Q(overall_sat=1) & Q(q30__isnull=False) & Q(reroute=0) & Q(reroute_360=0) & Q(first_spot_delay=0) &
            Q(remove=0) & Q(appeals_request__isnull=True) & Q(sc_dt_surveys__gte='2020-12-01') & Q(duplicate=0), then=True), default=False, output_field=BooleanField())
        self.appeals_ineligible_reason = Case(When(Q(sc_svc_prov_type='F'), then=Value('Is Fleet')),
                                              When(Q(overall_sat=1), then=Value('Overall Sat is TS')),
                                              When(Q(q30__isnull=True), then=Value('No Comment')),
                                              When(Q(reroute=1), then=Value('Is a Reroute')),
                                              When(Q(reroute_360=1), then=Value('Is a Reroute')),
                                              When(Q(remove=1), then=Value('December Manual Appeal Removal')),
                                              When(Q(first_spot_delay=1), then=Value('Is already removed by manual appeal')),
                                              When(Q(appeals_request__isnull=False), then=Value('Appeal already submitted')),
                                              When(Q(sc_dt_surveys__lt='2020-12-01'), then=Value('Survey is too old')),
                                              When(Q(duplicate=1), then=Value('Is Duplicate')), default=Value('Is eligible'),
                                              output_field=CharField()
                                              )


        self.tiers = list(Std12ETiers.objects.all().values())
        self.surveys, self.agg_params, self.parameters,  = surveys, agg_params, parameters
        self.exclusions, self.exclusions_but_osat, self.filters = exclusions, exclusions_but_osat, filters

        actions = [
            ('children', self.surveys__children),
            ('qa', self.surveys__qa),
            ('comment_finder', self.survey_comments),
            ('topic_aggregator', self.surveys__topic_aggregator),
            ('emulated_surveys', self.surveys__emulated_surveys),
            ('raw_records', self.surveys__raw_records),
            ('comp_timeseries', self.surveys__comp_timeseries)
        ]

        self.action = None
        for a in actions:
            if a[0] in parameters:
                self.action = a[0]
                return a[1]()


        if self.last_n:
            surveys = surveys.order_by('-sc_dt_surveys')[:int(self.last_n)]

        # print(surveys.aggregate(Count('overall_sat')))
        surveys = surveys.aggregate(**agg_params)
        osat_no_rules_avg = self.pre_exclusion_surveys.aggregate(osat_no_rules_avg=Avg('overall_sat'), osat_no_rules_count=Count('overall_sat'))
        surveys.update(osat_no_rules_avg)

        default_out = self.clean_up_surveys_list(surveys)
        print('SURVEY AGG DEFAULT OUT', default_out)
        return default_out



    def clean_survey_filters(self):
        filters_applied = {}
        # cleaned_exclusions = self.clean_filter_fields(self.exclusions, prefix='EXCLUDING ')
        cleaned_exclusions = {}
        # cleaned_exclusions_but_osat = self.clean_filter_fields(self.exclusions_but_osat, prefix="EXCLUDING (IF NOT TS) ")
        cleaned_exclusions_but_osat = {'Business Rules': 'On'} if self.apply_business_rules else {'Business Rules': 'Off'}

        if self.parameters.get('reroute') in ['none', 'appealed_auto', 'auto', 'appealed']:
            cleaned_exclusions_but_osat = {'Reroutes': self.parameters.get('reroute').upper().replace('_', ' & ')}

        if self.parameters.get('remove') in ['none', 'appealed_auto', 'auto', 'appealed']:
            cleaned_exclusions = {'Remove': self.parameters.get('remove').upper().replace('_', ' & ')}

        applied_filters = self.filters
        print("CLEANING DATE UPDATED", self.filters_original_values)
        applied_filters.update(self.filters_original_values)

        cleaned_filters = self.clean_filter_fields(applied_filters)
        print(cleaned_exclusions, cleaned_exclusions_but_osat, cleaned_filters)
        filters_applied.update(cleaned_exclusions)
        filters_applied.update(cleaned_exclusions_but_osat)
        filters_applied.update(cleaned_filters)
        return filters_applied

    def special_survey_rounding(self, n):
        n = n * 1000
        if n - math.floor(n) < 0.5:
            out = math.floor(n)
        else:
            out = math.ceil(n)
        return out/10

    def assign_survey_tier(self, scores):
        scores['tier'] = 'Below'
        scores['tier_index'] = 0
        scores['sat_threshold'] = 0
        scores['next_level'] = None
        print('assign_survey_tier', scores)
        for i, tier_name in enumerate(['Below', 'Tier-1', 'Tier-2', 'Tier-3']):
            if self.fac_type.lower() == 'fleet' and tier_name == 'Tier-3':
                continue
            tier = next(item for item in self.tiers if item["name"] == tier_name)
            print('assign_survey_tier', tier)
            metrics = tier.get('metrics').split(',') if tier.get('metrics') is not None else None
            score = [scores.get(metric.strip(), 0) for metric in metrics]
            score = round(sum([s * 100 if s is not None else 0 for s in score]), 1)
            if score >= tier['bottom'] and score < tier['top']:
                scores['tier'] = tier['name']
                scores['color'] = {
                    'Below': 'red-10',
                    'Tier-1': 'amber-10',
                    'Tier-2': 'purple-10',
                    'Tier-3': 'green-10'
                }[tier['name']]
                scores['sat_threshold'] = score
                scores['performance_score'] = score
                scores['perf_metrics_used'] = tier.get('metrics').replace('facility', 'driver').replace(' avg',
                                                                                                        '').upper().replace(
                    '_', ' ')
                scores['tier_index'] = i
                if tier['name'] == 'Tier-3' or (self.fac_type.lower() == 'fleet' and tier_name == 'Tier-2'):
                    scores['next_level'] = {
                        'Next Tier': tier.get('name'),
                        'Difference': score - tier['bottom'],
                        'Threshold': tier['bottom'],
                        'score': score
                    }
            elif score < tier['bottom'] and scores['next_level'] is None:
                scores['next_level'] = {
                    'Next Tier': tier.get('name'),
                    'Difference': score - tier['bottom'],
                    'Threshold': tier['bottom'],
                    'score': score
                }

        return scores

    def clean_up_surveys_list(self, surveys, remove_cols=[]):

        if type(surveys) == dict:
            surveys = [surveys, ]

        if type(surveys) != list:
            surveys = list(surveys)

        if surveys is None:
            return []

        for survey in surveys:

            if self.filters.get('sc_dt_surveys__lte') and self.filters.get('sc_dt_surveys__gte'):
                survey['start_date_agg'] = self.filters.get('sc_dt_surveys__gte')
                survey['end_date_agg'] = self.filters.get('sc_dt_surveys__lte')

            elif survey.get('start_date_agg') and survey.get('end_date_agg'):
                survey['start_date_agg'] = survey['start_date_agg'].strftime("%Y-%m-%d")
                survey['end_date_agg'] = survey['end_date_agg'].strftime('%Y-%m-%d')

            # print('start date ', survey['start_date_agg'], survey['end_date_agg'])

            survey = self.assign_survey_tier(survey)

            for col in remove_cols:
                if col in survey: del survey[col]

            if 'children' in self.parameters:
                for k, v in survey.items():
                    if 'count' in k:
                        survey[k] = int(v) if v is not None else 0

                if 'slug' not in survey:
                    survey['slug'] = survey['name'] + '-city'

        if len(surveys) > 0:
            surveys[0]['applied_filters'] = self.clean_survey_filters()
        return surveys

    # def survey_aggregator_old(self, parameters):
    #
    #     surveys = Std12EReduced.objects
    #
    #     parameters['reroute_filter_applied'] = False
    #
    #     if self.model_reference == 'Organization':
    #         if self.object.facility_type == 'Fleet':
    #             self.fac_type = 'fleet'
    #         else:
    #             self.fac_type = 'csn'
    #     else:
    #         if self.object.organization.facility_type == 'Fleet':
    #             self.fac_type = 'fleet'
    #         else:
    #             self.fac_type = 'csn'
    #
    #     if 'fac_type__in' in parameters['filters']:
    #         if parameters['filters']['sc_svc_prov_type__in'] == ['F']:
    #             self.fac_type = 'fleet'
    #         else:
    #             self.fac_type = 'csn'
    #
    #     if 'fac_type' in parameters:
    #         if parameters['fac_type'] == 'csn':
    #             surveys = surveys.exclude(sc_svc_prov_type='F')
    #             self.fac_type = 'csn'
    #         elif parameters['fac_type'] == 'fleet':
    #             self.fac_type = 'fleet'
    #             surveys = surveys.filter(sc_svc_prov_type='F')
    #
    #     tiers = list(Std12ETiers.objects.filter(type=self.fac_type).values())
    #
    #     # handle usual filter checks
    #     if 'accreditation__in' not in parameters['filters'] or 'comp' in parameters:
    #         parameters['filters']['accreditation'] = "Yes"
    #
    #     if 'directional_error__in' not in parameters['filters'] or 'comp' in parameters:
    #         parameters['filters']['directional_error'] = "No"
    #
    #     # if 'sc_club_code__in' not in parameters['filters'] or 'comp' in parameters:
    #     #     parameters['filters']['sc_club_code'] = 212
    #
    #     # reroute filter
    #     apply_reroute = False
    #     apply_remove = False
    #
    #     if self.model_reference == 'Employee':
    #         apply_reroute = True
    #         apply_remove = True
    #     elif self.object.type in ['Station', 'Station-Business']:
    #         apply_reroute = True
    #         apply_remove = True
    #     elif 'qa' in parameters:
    #         apply_reroute = True
    #         apply_remove = True
    #
    #     show_only_reroute = False
    #     if 'reroute' in parameters:
    #         if parameters['reroute'] == 'show_only_reroutes':
    #             show_only_reroute = True
    #             apply_reroute = False
    #         else:
    #             apply_reroute = parameters['reroute']
    #         print('APPLYING REROUTE OVERRIDE', parameters['reroute'])
    #
    #     if 'remove' in parameters:
    #         apply_remove = parameters['remove']
    #
    #     parameters['remove_filter_applied'] = False
    #     if apply_remove:
    #         print("APPLYING REMOVE FILTER")
    #         surveys = surveys.exclude(remove=True)
    #         parameters['remove_filter_applied'] = True
    #
    #     # class Round(Func):
    #     #     function = 'ROUND'
    #     #     template = '%(function)s(%(expressions)s, 3)'
    #
    #     if apply_reroute:
    #         print("Object is at Station-Business Level or Lower, so we are applying the reroute filter")
    #
    #         agg_params = {
    #             'response_sat_avg': Round(Avg('response_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(response_sat=1))))),
    #             'overall_sat_avg': Round(Avg('overall_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (
    #                     Q(reroute=1) & Q(overall_sat=1))))),
    #             'facility_sat_avg': Round(Avg('facility_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(facility_sat=1))))),
    #             'request_service_sat_avg': Round(Avg('request_service_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(request_service_sat=1))))),
    #             'kept_informed_sat_avg': Round(Avg('kept_informed_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(kept_informed_sat=1))))),
    #
    #             'response_sat_count': Count('response_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(response_sat=1)))),
    #             'overall_sat_count': Count('overall_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))),
    #             'driver_sat_count': Count('facility_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(facility_sat=1)))),
    #             'request_service_sat_count': Count('request_service_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(request_service_sat=1)))),
    #             'kept_informed_sat_count': Count('kept_informed_sat', filter=(
    #                     Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(kept_informed_sat=1)))),
    #
    #             'reroute_count': Sum('reroute'),
    #             'start_date_agg': Min('sc_dt_surveys'),
    #             'end_date_agg': Max('sc_dt_surveys')
    #         }
    #
    #         parameters['reroute_filter_applied'] = True
    #
    #     else:
    #
    #         agg_params = {
    #             'response_sat_avg': Round(Avg('response_sat')),
    #             'overall_sat_avg': Round(Avg('overall_sat')),
    #             'facility_sat_avg': Round(Avg('facility_sat')),
    #             'request_service_sat_avg': Round(Avg('request_service_sat')),
    #             'kept_informed_sat_avg': Round(Avg('kept_informed_sat')),
    #
    #             'response_sat_count': Count('response_sat'),
    #             'overall_sat_count': Count('overall_sat'),
    #             'driver_sat_count': Count('facility_sat'),
    #             'request_service_sat_count': Count('request_service_sat'),
    #             'kept_informed_sat_count': Count('kept_informed_sat'),
    #
    #             'reroute_count': Sum('reroute'),
    #             'reroute_avg': Cast(Sum('reroute'), FloatField()) / Cast(Count('overall_sat'), FloatField()),
    #
    #             'start_date_agg': Min('sc_dt_surveys'),
    #             'end_date_agg': Max('sc_dt_surveys')
    #         }
    #
    #     today = dt.date.today()
    #
    #     period = \
    #         Std12ETierTimePeriods.objects.filter(start__lte=today, show_until__gt=today, type=self.fac_type).order_by(
    #             'start')[0]
    #
    #     # set periods for comp requirements
    #     if ('comp' in parameters and 'last_n' not in parameters['filters']) or \
    #             (('sc_dt_surveys__gte' not in parameters['filters'] and 'sc_dt_surveys__lte' not
    #               in parameters['filters']) and 'last_n' not in parameters['filters']):
    #         print("Applying Comp parameters")
    #
    #         # TODO: this is to keep things up for a week later than scores should be cutoff
    #         parameters['filters']['sc_dt_surveys__gte'] = period.start
    #         parameters['filters']['sc_dt_surveys__lte'] = period.end
    #         self.comp_period = period.name
    #         self.comp_start = period.start
    #         self.comp_end = period.end
    #
    #     if 'date_updated_surveys__lte' in parameters['filters']:
    #         parameters['filters']['date_updated_surveys__lte'] = parameters['filters'][
    #                                                                  'date_updated_surveys__lte'] + " 23:59:59"
    #
    #     elif 'qa' in parameters:
    #         parameters['filters']['date_updated_surveys__lte'] = period.recorded_cutoff_time
    #
    #     if 'comp' in parameters:
    #         parameters['filters']['date_updated_surveys__lte'] = period.recorded_cutoff_time
    #         print(parameters['filters'])
    #     else:
    #         print(parameters['filters'])
    #
    #     if 'unseenSurveys' in parameters and not ('lastEmailSurveys' in parameters):
    #         import json
    #         lastSession = ga.get_user_data(ga, {'user': str(self.user.id)})['sessions']
    #         lastSession = \
    #             [s['sessionDate'] for s in lastSession if
    #              str(s['sessionDate']) != dt.date.today().strftime("%Y-%m-%d")][0]
    #         parameters['filters']['date_updated_surveys__gte'] = lastSession
    #         parameters['filters']['sc_dt_surveys__lte'] = dt.date.today().strftime("%Y-%m-%d")
    #         parameters['filters']['sc_dt_surveys__gte'] = "2020-01-01"
    #         # print(lastSession, 'lastsession', dt.date.today().strftime("%Y-%m-%d"), lastSession != dt.date.today().strftime("YYYY-MM-DD"))
    #
    #     if 'lastEmailSurveys' in parameters:
    #         print(parameters)
    #         lastEmail = EmailLogs.objects.filter(generated_by_id=parameters['send_to_id'], type='newSurveys')
    #         lastEmail = lastEmail.order_by('-date_delivered')[0].date_delivered
    #         print('LAST EMAIL', lastEmail)
    #         parameters['filters']['date_updated_surveys__gte'] = lastEmail.strftime("%Y-%m-%d")
    #         parameters['filters']['sc_dt_surveys__lte'] = dt.date.today().strftime("%Y-%m-%d")
    #         parameters['filters']['sc_dt_surveys__gte'] = "2020-01-01"
    #
    #     if 'last_n_days' in parameters:
    #         parameters['filters']['sc_dt_surveys__lte'] = dt.date.today().strftime("%Y-%m-%d")
    #         parameters['filters']['sc_dt_surveys__gte'] = (
    #                 dt.date.today() - dt.timedelta(days=int(parameters['last_n_days']))).strftime("%Y-%m-%d")
    #
    #     if 'last_upload_n_days' in parameters:
    #         del parameters['filters']['sc_dt_surveys__lte']
    #         del parameters['filters']['sc_dt_surveys__gte']
    #         parameters['filters']['date_updated_surveys__gte'] = (
    #                 dt.date.today() - dt.timedelta(days=int(parameters['last_upload_n_days']))).strftime("%Y-%m-%d")
    #
    #     swap_filter = {}
    #     for filter, value in parameters['filters'].items():
    #         if type(value) == list and '__in' not in filter:
    #             filter = filter + '__in'
    #             if len(value) > 0:
    #                 swap_filter[filter] = value
    #             else:
    #                 continue
    #         if value == 'unknown':
    #             filter = filter + '__isnull'
    #             value = True
    #             swap_filter[filter] = value
    #         else:
    #             swap_filter[filter] = value
    #     parameters['filters'] = swap_filter
    #
    #     if 'last_n' in parameters['filters']:
    #         last_n = parameters['filters']['last_n']
    #         del parameters['filters']['last_n']
    #     else:
    #         last_n = False
    #
    #     if show_only_reroute:
    #         print('Show only reroute')
    #         parameters['filters']['reroute'] = True
    #
    #     print("THESE ARE THE SURVEY FILTERS", parameters['filters'])
    #     surveys = surveys.filter(**parameters['filters'])
    #
    #     if 'qa' in parameters:
    #
    #         if parameters['org_type'] == 'Stations':
    #             default_child = 'org_svc_facl_id'
    #             g1 = default_child + '__name'
    #             g2 = default_child + '__parent_id'
    #         elif parameters['org_type'] == 'Drivers':
    #             default_child = 'emp_driver_id'
    #             g1 = default_child + '__full_name'
    #             g2 = default_child + '__organization__name'
    #         elif parameters['org_type'] == 'Territory':
    #             default_child = 'org_territory_id'
    #             g1 = default_child + '__name'
    #             g2 = default_child + '__parent_id'
    #
    #         elif parameters['org_type'] == 'Driver-Station':
    #             default_child = ['org_svc_facl_id', 'emp_driver_id']
    #             # g1 = default_child + '__name'
    #             # g2 = default_child + '__parent_id'
    #
    #         # surveys = surveys.filter(date_updated_surveys__lte='2019-10-24')
    #
    #         # print(surveys.query)
    #         agg_params['aca_driver_id'] = Max('drv_id')
    #
    #         agg_params['tier_score'] = Round(Avg('overall_sat', filter=(
    #                 Q(reroute=0) | Q(reroute__isnull=True) | (
    #                 Q(reroute=1) & Q(overall_sat=1))))) * 100 + Round(Avg('facility_sat', filter=(
    #                 Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(facility_sat=1))))) * 100
    #
    #         if parameters['org_type'] == 'Driver-Station':
    #             surveys = surveys.values(default_child[0], default_child[0] + '__name',
    #                                      default_child[0] + '__parent_id', default_child[0] + "__slug",
    #                                      default_child[1], default_child[1] + '__full_name',
    #                                      default_child[1] + '__organization__name',
    #                                      default_child[1] + "__slug").annotate(**agg_params)
    #         else:
    #             surveys = surveys.values(default_child, g1, g2, default_child + "__slug").annotate(**agg_params)
    #
    #         return surveys
    #
    #     elif 'children' in parameters and self.model_reference != 'Employee':
    #         print("CHILDREN", self.index_type)
    #         if self.index_type != 'Club':
    #             surveys = surveys.filter(**{self.get_index_type(self.index_type).lower(): self.object.id})
    #
    #         default_child = self.default_children(self.object.type).lower()
    #
    #         if 'child_type' in parameters:
    #             default_child = self.get_index_type(parameters['child_type']).lower()
    #
    #         if 'fleet-drivers' in parameters:
    #             print("Fleet driver request")
    #             default_child = 'emp_driver_id'
    #
    #         if default_child[:3] == 'org':
    #             grouping = default_child + '__name'
    #         elif default_child in ['bl_near_cty_nm', 'bl_state_cd']:
    #             grouping = default_child
    #         else:
    #             grouping = default_child + '__full_name'
    #
    #         print("Grouping by: ", grouping)
    #         if default_child == 'org_svc_facl_id':
    #             surveys = surveys.annotate(name=F(grouping), slug=F(default_child + '__slug'),
    #                                        parent_territory=F(default_child + '__grandparent__name')).values('name',
    #                                                                                                          'slug',
    #                                                                                                          'parent_territory').annotate(
    #                 **agg_params)
    #         elif default_child in ['bl_near_cty_nm', 'bl_state_cd']:
    #             surveys = surveys.annotate(name=F(grouping)).values('name').annotate(**agg_params)
    #         else:
    #             surveys = surveys.annotate(name=F(grouping), slug=F(default_child + '__slug'),
    #                                        record_id=F(default_child + '_id')).values('name', 'slug',
    #                                                                                   'record_id').annotate(
    #                 **agg_params)
    #         # print("CHILDREN", surveys)
    #
    #         output = self.clean_up_surveys_list(surveys, tiers, parameters)
    #
    #         if output is None:
    #             return []
    #         else:
    #             return output
    #     elif 'children' in parameters and self.model_reference == 'Employee':
    #         return []
    #     else:
    #
    #         if self.index_type != 'Club':
    #             surveys = surveys.filter(**{self.get_index_type(self.index_type).lower(): self.object.id})
    #
    #         if last_n:
    #             surveys = surveys.filter(Q(reroute=0) | Q(reroute__isnull=True) | (Q(reroute=1) & Q(overall_sat=1)))
    #             # surveys = surveys.order_by('-sc_dt_surveys')[:int(last_n)]
    #
    #         if not any(q in ['emulated_surveys', 'comment_finder', 'raw_records', 'topic_aggregator'] for q in
    #                    parameters.keys()):
    #             surveys = surveys.aggregate(**agg_params)
    #             return self.clean_up_surveys_list(surveys, tiers, parameters)
    #
    #         if 'emulated_surveys' in parameters:
    #             question_serializer = Std12ESerializerQuestions(RawStd12EQuestions.objects.all(), many=True)
    #             surveys = surveys.extra(
    #                 select={'spot_minutes': "ROUND(TIMESTAMPDIFF(SECOND, FST_SPOT_TIME, LST_SPOT_TIME)/60, 1)"})
    #             surveys = surveys.annotate(first_spot_fac=F('fst_shop'))
    #             if last_n:
    #                 surveys = surveys.order_by('-sc_dt_surveys')[:int(last_n)]
    #             else:
    #                 surveys = surveys[parameters['lower_bound']: parameters['upper_bound']]
    #
    #             emulated_surveys = surveys.values('sc_dt', 'emp_driver_id__slug', 'emp_driver_id__display_name',
    #                                               'outc1', 'q30', 'driver10', 'driver5', 'desc2', 'q26', 'q24', 'sc_id',
    #                                               'check_id_compliant',
    #                                               'call_center_operator', 'cm_trk', 'dispatch_communicated', 'ata',
    #                                               'pta', 'ata_minus_pta', 're_tm', 'tcd', 'sc_dt_surveys',
    #                                               'sc_id_surveys', 'spot_minutes', 'first_spot_fac',
    #                                               'org_svc_facl_id__name')
    #
    #             # print('emulated_surveys', emulated_surveys[0])
    #
    #             for s in emulated_surveys:
    #                 try:
    #                     s['sc_id'] = s['sc_id_surveys']
    #                     s['sc_dt'] = s['sc_dt_surveys'].strftime('%Y-%m-%d')
    #                     s['re_tm'] = s['re_tm'].strftime('%Y-%m-%d %H:%M:%S')
    #                 except:
    #                     print(s)
    #
    #             output = {'data': list(emulated_surveys), 'metadata': question_serializer.data}
    #             return output
    #
    #         if 'comment_finder' in parameters:
    #             print("COMMENT FINDER")
    #             return self.survey_comments(parameters, surveys)
    #
    #         print(parameters)
    #         if 'topic_aggregator' in parameters:
    #             topic_comments = CommentTopics.objects
    #             # organization
    #             if self.object.id != 7:  # if its not aca-club
    #                 filter = self.get_index_type(self.object_type)
    #                 filter_query = {'survey__' + filter.lower(): self.object.id}
    #                 topic_comments = topic_comments.filter(**filter_query)
    #
    #             filter_d = {}
    #             for filter, value in parameters['filters'].items():
    #                 filter_param = 'survey__' + filter
    #                 if type(value) == list and '__in' not in filter:
    #                     filter_param = filter_param + '__in'
    #                 filter_d[filter_param] = value
    #
    #             print("COMMENT FILTERS", filter_d)
    #             topic_comments = topic_comments.filter(**filter_d)
    #
    #             if "sentiment" in parameters:
    #                 topic_comments = topic_comments.filter(**parameters['sentiment'])
    #
    #             topic_data = topic_comments.values('topic').annotate(count=Count('topic'),
    #                                                                  avg_sentiment=Avg('sentiment'))
    #             print("TOPIC DATA", topic_data)
    #             topics = {}
    #             out = []
    #             for t in topic_data:
    #                 topics[t['topic']] = t
    #             for topic, data in topics.items():
    #                 print(data)
    #                 out.append(
    #                     {
    #                         'name': topic.upper(),
    #                         'data': [{'label': 'count', 'djangoLabel': 'Comment Count', 'value': data['count']},
    #                                  {'label': 'avg_sentiment', 'djangoLabel': 'Average Sentiment',
    #                                   'value': data['avg_sentiment']}]
    #                     }
    #                 )
    #             return out
    #
    #         if 'raw_records' in parameters:
    #
    #             surveys = surveys.extra(
    #                 select={'spot_minutes': "ROUND(TIMESTAMPDIFF(SECOND, FST_SPOT_TIME, LST_SPOT_TIME)/60, 1)"})
    #             surveys = surveys.annotate(first_spot_fac=F('fst_shop'))
    #
    #             conversions = {
    #                 'overall_satisfaction': 'outc1',
    #                 'response_time': 'q24',
    #                 'kept_informed': 'q26',
    #                 'requesting_service': 'driver5',
    #                 'driver_sat': 'driver10',
    #                 'facility_id': 'sp_fac_id',
    #                 'facility_name': 'org_business_id__name',
    #                 'pta': 'pta',
    #                 'ata': 'ata',
    #                 'call_id': 'sc_id_surveys',
    #                 'survey_recorded': 'recordeddate',
    #                 'service_resolution': 'resolution_desc',
    #                 'territory_name': 'org_territory_id__name',
    #                 'trouble_type': 'tlc_desc',
    #                 'driver': 'emp_driver_id__full_name',
    #                 'service_date': 'sc_dt_surveys',
    #                 'verbatim': 'q30',
    #                 'fleet_supervisor_name': 'fleet_supervisor__full_name'
    #             }
    #
    #             if 'search_field' in parameters:
    #                 for field, search_value in parameters['search_field'].items():
    #                     print('search field object', parameters['search_field'])
    #                     searchParams = {conversions[field] + '__icontains': search_value}
    #                     print('search parameters', searchParams)
    #                     surveys = surveys.filter(**searchParams)
    #
    #             if 'sort_field' in parameters:
    #
    #                 if parameters['sort_direction'] == 'asc':
    #                     surveys = surveys.order_by(conversions[parameters['sort_field']])
    #                 else:
    #                     surveys = surveys.order_by('-' + conversions[parameters['sort_field']])
    #             else:
    #                 surveys = surveys.order_by('-sc_dt_surveys')
    #
    #             survey_length = surveys.count()
    #
    #             if 'lower_bound' in parameters:
    #                 surveys = surveys[parameters['lower_bound']: parameters['upper_bound']]
    #             else:
    #                 if survey_length > 250 and not ('unboundOverride' in parameters):
    #                     return {'Warning': "<p>There are too many surveys. There are " + str(
    #                         survey_length) + " in total. The limit is set to 250 when sending Emails.</p>"
    #                                          "<p>Please constrain your query by modifying the filter parameters (e.g. date). Loading too many surveys for the purposes of sending an email can crash your browser. If you just hit the email button, then limit your search and try again.</p>"
    #                                          "<p><b> HINT:</b> "
    #                                          "You can however export all of them as an excel file using the Export ALL as XLS button.</p>"}
    #
    #             raw_records = list(surveys.annotate(overall_satisfaction=F('outc1'),
    #                                                 response_time=F('q24'),
    #                                                 kept_informed=F('q26'),
    #                                                 requesting_service=F('driver5'),
    #                                                 driver_sat=F('driver10'),
    #                                                 facility_id=F('sp_fac_id'),
    #                                                 facility_name=F('org_business_id__name'),
    #                                                 call_id=F('sc_id_surveys'),
    #                                                 survey_recorded=F('recordeddate'),
    #                                                 service_resolution=F('resolution_desc'),
    #                                                 territory_name=F('org_territory_id__name'),
    #                                                 trouble_type=F('tlc_desc'),
    #                                                 # reroute_rate=F('reroute'),
    #                                                 driver=F('emp_driver_id__full_name'),
    #                                                 service_date=F('sc_dt_surveys'),
    #                                                 verbatim=F('q30'),
    #                                                 driver_called=Case(When(cm_trk=1, then=Value('Yes')),
    #                                                                    When(cm_trk=0, then=Value('No')),
    #                                                                    default=Value('No'), output_field=CharField()),
    #                                                 fleet_supervisor_name=F('fleet_supervisor__full_name')).values(
    #                 'facility_id',
    #                 'facility_name',
    #                 'service_date',
    #                 'call_id',
    #                 'survey_recorded',
    #                 'territory_name',
    #                 'driver',
    #                 'fleet_supervisor_name',
    #                 'reroute',
    #                 'remove',
    #                 'service_resolution',
    #                 'trouble_type',
    #                 'overall_satisfaction',
    #                 'driver_sat',
    #                 'response_time',
    #                 'kept_informed',
    #                 'requesting_service',
    #                 'pta',
    #                 'ata',
    #                 'driver_called',
    #                 'verbatim', 'spot_minutes', 'first_spot_fac'))
    #
    #             # print("RAW RECORDS", raw_records)
    #
    #             for s in raw_records:
    #                 s['overall_satisfaction'] = self.survey_response_mapping(s['overall_satisfaction'])
    #                 s['response_time_sat'] = self.survey_response_mapping(s['response_time'])
    #                 s['kept_informed_sat'] = self.survey_response_mapping(s['kept_informed'])
    #                 s['requesting_service_sat'] = self.survey_response_mapping(s['requesting_service'])
    #                 s['driver_sat'] = self.survey_response_mapping(s['driver_sat'])
    #                 s['service_date'] = s['service_date'].strftime('%Y-%m-%d') if s[
    #                                                                                   'service_date'] is not None else None
    #                 s['survey_recorded'] = s['survey_recorded'].strftime('%Y-%m-%d') if s[
    #                                                                                         'survey_recorded'] is not None else None
    #                 del s['requesting_service']
    #                 del s['kept_informed']
    #                 del s['response_time']
    #
    #             new_d = self.clean_survey_filters(parameters['filters'])
    #             print(new_d, parameters['filters'], "FILTER CONVERSION")
    #
    #             if parameters['reroute_filter_applied']:
    #                 # print("Adding reroute to filter list")
    #                 new_d['REROUTE FILTER APPLIED'] = "YES"
    #
    #             if parameters['remove_filter_applied']:
    #                 print("ADDING PRINT STATEMENT FOR REMOVE")
    #                 new_d['REMOVE FILTER APPLIED'] = "YES"
    #
    #             # if "lower_bound" in parameters:
    #             #     new_d['PAGE'] = int(parameters['lower_bound']/100) + 1
    #
    #             for r in range(len(raw_records)):
    #                 for k in ['facility_id',
    #                           'facility_name',
    #                           'service_date',
    #
    #                           'call_id',
    #                           'survey_recorded',
    #                           'territory_name',
    #                           'driver',
    #                           'fleet_supervisor_name',
    #                           'reroute',
    #                           'remove',
    #                           'service_resolution',
    #                           'trouble_type',
    #                           'overall_satisfaction',
    #                           'driver_sat',
    #                           'response_time_sat',
    #                           'kept_informed_sat',
    #                           'requesting_service_sat',
    #                           'pta', 'ata', 'driver_called', 'spot_minutes', 'first_spot_fac',
    #                           'verbatim', ]:
    #                     if self.fac_type != 'fleet' and k == 'fleet_supervisor_name':
    #                         del raw_records[r][k]
    #                     else:
    #                         raw_records[r][k] = raw_records[r].pop(k)
    #
    #             print(new_d)
    #             return [new_d, raw_records, survey_length]
    #
    #         if not surveys:
    #             return []

    def format_output(self, data, parameters, label='sc_dt', time_type=False):
        output_dict = {}

        for metric in parameters['metrics']:
            if metric in ['id_name_helper', 'sc_dt', 'anomaly_vol', 'week_day']:
                continue
            output_dict[metric] = []

        for period in list(data):

            for metric in parameters['metrics']:
                if metric in ['id_name_helper', 'sc_dt', 'anomaly_vol', 'week_day']:
                    continue

                if period[label] is None:
                    continue
                metric_dict = {
                    'value': self.convert_percentage(period[metric], self.field_name_conversion(metric)),
                    'label': period[label],
                    'value_type': self.field_name_conversion(metric)
                }

                if metric == 'volume':
                    # print("bypassing anomaly_vol")
                    metric_dict['anomaly'] = 0

                metric_dict['value'] = metric_dict.get('value')

                # if 'value' not in metric_dict or metric_dict.get('value') == None:  # check to see if there is actually a value here...
                #     metric_dict['value'] = None
                output_dict[metric].append(metric_dict)

        output = []
        for k, v in output_dict.items():
            output.append({
                'groupName': k,
                'time_type': time_type,
                'data': v,

            })

        return output

    def maps_logging(self, parameters):
        action_url = '/dashboard/' + self.object.slug + '?section=maps'
        action_display = 'New Maps Log'
        print(action_display)
        ActionsLogger(self.request.user, 'RawOps', action_display, 'Maps', action_url)
        return {"complete": True}

    def maps(self, parameters):
        MAP_LIMIT = False
        warning = False

        if 'map_limit' in parameters:
            MAP_LIMIT = parameters['map_limit']

        if parameters['mode'] == 'operations':
            raw_data = RawOps.objects.all().exclude(bl_lat__isnull=True).exclude(bl_long__isnull=True)
        elif parameters['mode'] == 'surveys':
            raw_data = Std12EReduced.objects.all().exclude(bl_lat__isnull=True).exclude(bl_long__isnull=True)
            raw_data = raw_data.exclude(outc1__isnull=True)

        if 'weekday_filter' in parameters:
            raw_data = raw_data.filter(sc_dt__week_day=parameters['weekday_filter'])

        if 'start_hour' in parameters:
            print('setting start hour', parameters['start_hour'])
            raw_data = raw_data.filter(re_tm__hour__gte=parameters['start_hour'])

        if 'end_hour' in parameters:
            print('setting end hour', parameters['end_hour'])
            raw_data = raw_data.filter(re_tm__hour__lt=parameters['end_hour'])

        if 'from_date' in parameters:
            print('setting start date', parameters['from_date'])
            raw_data = raw_data.filter(sc_dt__gte=parameters['from_date'])

        if 'end_date' in parameters:
            print('setting end date', parameters['end_date'])
            raw_data = raw_data.filter(sc_dt__lte=parameters['end_date'])

        # filter org
        cities = self.object.get_cities()
        if self.object.type != 'Club' and self.model_reference != 'employee':
            f = {}
            f[self.get_index_type(self.object_type).lower()] = self.object.id
            print(f)
            raw_data = raw_data.filter(**f)

            try:
                children = list(self.object.children().values('slug', 'real_name', 'type', 'name').exclude(
                    real_name='unassigned-club-region').exclude(type='Grid'))
            except FieldError:
                children = []

            if (self.object_type in ['Station-Business', 'Station']) or (
                    self.object_type == 'Territory' and self.object.facility_type == 'Fleet'):
                drivers_in_raw_data = list(raw_data.values_list('emp_driver_id', flat=True).distinct())
                # print(drivers_in_raw_data)
                children = children + list(
                    self.object.employees().filter(id__in=drivers_in_raw_data).annotate(type=F('position_type'),
                                                                                        name=F('display_name')).values(
                        'slug', 'type', 'name'))

            grids = self.object.get_grids()
            grids = list(
                grids.filter(id__in=raw_data.values_list('org_grid', flat=True)).values('slug', 'real_name', 'type',
                                                                                        'name'))

            children = {'children': children, 'grids': grids, 'cities': cities}

        else:
            children = {'children': list(
                Organization.objects.filter(type='Club-Region').values('slug', 'real_name', 'type', 'name')),
                'cities': cities, 'grids': []}

        survey_field_lookup = {v: k for k, v in self.survey_key_converter.items()}

        if 'filters' in parameters:
            if 'tcd' in parameters['filters']:
                tcd = parameters['filters']['tcd']
                tcd_matcher = {'Battery': 3, 'Tow': 6, }
                if tcd in ['Battery', 'Tow']:
                    raw_data = raw_data.filter(tcd__startswith=tcd_matcher[tcd])
                else:
                    raw_data = raw_data.exclude(tcd__startswith='3').exclude(tcd__startswith='6')
            if 'onTime' in parameters['filters']:
                q = {parameters['filters']['onTime'].lower().replace(' ', '_'): True}
                raw_data = raw_data.filter(**q)
            if 'childFilter' in parameters['filters']:
                org_object = Organization.objects.get(slug=parameters['filters']['childFilter'])
                raw_data = raw_data.filter(**{self.get_index_type(org_object.type).lower(): org_object.id})
            if 'gridFilter' in parameters['filters']:
                org_object = Organization.objects.get(slug=parameters['filters']['gridFilter'])
                raw_data = raw_data.filter(**{self.get_index_type(org_object.type).lower(): org_object.id})
            if 'driverFilter' in parameters['filters']:
                emp_object = Employee.objects.get(slug=parameters['filters']['driverFilter'])
                raw_data = raw_data.filter(emp_driver_id=emp_object.id)
            if 'city' in parameters['filters']:
                raw_data = raw_data.filter(bl_near_cty_nm=parameters['filters']['city'])
            if 'state' in parameters['filters']:
                raw_data = raw_data.filter(bl_state_cd=parameters['filters']['state'])
            for f in ['ata', 'pta', 'ata_minus_pta']:
                if f in parameters['filters']:
                    val = parameters['filters'][f]
                    raw_data = raw_data.filter(**{f + '__gte': val[0], f + '__lte': val[1]})
            if parameters['mode'] == 'surveys':
                if 'satFilter' in parameters['filters']:
                    for f in ['Overall Sat', 'Response Time Sat', 'Driver Sat']:
                        if f in parameters['filters']['satFilter']:
                            field = survey_field_lookup[f.lower().replace(' ', '_')]
                            val = parameters['filters']['satFilter'][f]
                            if len(val) > 0:
                                q = {field + '__in': val}
                                print(q)
                                raw_data = raw_data.filter(**q)

        original_length = raw_data.count()
        print('getting length', original_length)

        if original_length < 1:
            warning = {'title': 'No Calls Found!',
                       'text': 'No Calls Found With those Settings! Try Changing and resubmitting'}
            return {'map_data': [], 'children': children, 'date_range': (None, None),
                    'warning': warning, 'filter_params': {},
                    'limits': {'user_defined_limit': MAP_LIMIT, 'original_length': original_length}}

        if original_length > 10000 and (not MAP_LIMIT or MAP_LIMIT > 10000):
            MAP_LIMIT = 10000

        if MAP_LIMIT:
            if 'from_date' in parameters and 'end_date' in parameters:
                if original_length > 10000:
                    warning = {
                        'text': "There were %s records returned by your query, but this map can only handle 10,000 calls! "
                                "Only the calls falling between the dates listed in the DATE/TIME section are shown and the others are left off. "
                                "Please consider adjusting your filter parameters to fix this." % str(original_length),
                        'title': 'Too Many Calls',
                        'type': 'exceedsLimit',
                        'original_length': original_length}

                elif original_length > MAP_LIMIT:
                    warning = {
                        'text': "There were %s records returned by your query, but you set the number of calls limit to %s " \
                                "We Suggest you increase the number of calls allowed" % (
                                    str(original_length), str(MAP_LIMIT)),
                        'title': 'Too Many Calls',
                        'type': 'dotLimitTooLow',
                        'currentMapLimit': MAP_LIMIT,
                        'original_length': original_length}

        print('original length: ', original_length)
        # print(to_date.strftime("%Y-%m-%d %H:%M"))
        print('ordering')
        raw_data = raw_data.order_by('-re_tm')
        if MAP_LIMIT:
            if 'from_date' in parameters and 'to_date' not in parameters:
                raw_data = raw_data.order_by('re_tm')
            else:
                raw_data = raw_data.order_by('-re_tm')
            raw_data = raw_data[:MAP_LIMIT]
        else:
            raw_data = raw_data.order_by('-re_tm')
        print('aggregating')
        filter_params = raw_data.aggregate(
            max_ata=Max('ata'),
            max_pta=Max('pta'),
            max_ata_minus_pta=Max('ata_minus_pta'),
            min_ata=Min('ata'),
            min_pta=Min('pta'),
            min_ata_minus_pta=Min('ata_minus_pta'),
            max_date=Max('re_tm'),
            min_date=Min('re_tm'))
        print(filter_params)

        if parameters['mode'] == 'operations':
            serializer = MapsSerializer(raw_data, many=True)
        elif parameters['mode'] == 'surveys':
            serializer = MapSurveySerializer(raw_data, many=True)

        return {'map_data': serializer.data, 'children': children,
                'warning': warning, 'filter_params': filter_params,
                'limits': {'user_defined_limit': MAP_LIMIT, 'original_length': original_length}}

    def timeseries(self, parameters, queryset=None):

        if not queryset:
            queryset = self.queryset

        parameters['metrics'].append("sc_dt")
        if 'volume' in parameters['metrics']:
            print("no anomaly vol")
            # parameters['metrics'].append("anomaly_vol")

        querysets = {}
        output = []

        # time_type
        if 'time_type' in parameters:
            time_types = parameters['time_type']
            for time_type in time_types:
                if type(time_type) == list:
                    time_type = time_type[0]
                conv_t = self.time_type_conversions[time_type]
                querysets[time_type] = queryset.filter(time_type=conv_t)

        else:
            querysets["Day"] = queryset.filter(time_type="D")

        for time_type, queryset in querysets.items():
            # from_date
            if 'from' not in parameters:
                parameters['from'] = self.default_from_date
            if parameters['from'] is None:
                parameters['from'] = self.default_from_date
            if time_type == 'Month':
                from_date = dt.datetime.strptime(parameters['from'], "%Y-%m-%d").replace(day=1)
            elif time_type == 'Incentive':
                from_date = dt.datetime.strptime(parameters['from'], "%Y-%m-%d").replace(day=1)
            elif time_type == 'Year':
                from_date = dt.datetime.strptime(parameters['from'], "%Y-%m-%d").replace(day=1, month=1)
            elif time_type == 'Day':
                from_date = dt.datetime.strptime(parameters['from'], "%Y-%m-%d")
            elif time_type == 'Hour':
                from_date = dt.datetime.strptime(parameters['from'], "%Y-%m-%d")
            elif time_type == 'Week':
                from_date = dt.datetime.strptime(parameters['from'], "%Y-%m-%d")
            elif time_type == 'R12':
                from_date = (dt.datetime.strptime(parameters['from'], "%Y-%m-%d") - relativedelta.relativedelta(
                    years=1)).replace(day=1)

            elif time_type == 'Hour_of_Day':
                from_date = False
            elif time_type == 'Day_and_Hour_of_Week':
                from_date = False
            elif time_type == 'Day_of_Week':
                from_date = False


            else:
                raise Exception("No time type specified!, but from date is specified")
            if from_date:
                querysets[time_type] = querysets[time_type].filter(sc_dt__gte=from_date)

            # to_date
            if 'to' in parameters:
                if parameters["to"] is not None:
                    if time_type == 'Month' or time_type == 'R12':
                        to_date = dt.datetime.strptime(parameters['to'], "%Y-%m-%d").replace(day=1)
                    elif time_type == 'Incentive':
                        to_date = dt.datetime.strptime(parameters['to'], "%Y-%m-%d").replace(day=1)
                    elif time_type == 'Year':
                        to_date = dt.datetime.strptime(parameters['to'], "%Y-%m-%d").replace(day=1, month=1)
                    elif time_type == 'Day':
                        to_date = dt.datetime.strptime(parameters['to'], "%Y-%m-%d")
                    elif time_type == 'Hour':
                        to_date = dt.datetime.strptime(parameters['to'], "%Y-%m-%d")
                    elif time_type == 'Week':
                        to_date = dt.datetime.strptime(parameters['to'], "%Y-%m-%d")

                    elif time_type == 'Hour_of_Day':
                        to_date = False
                    elif time_type == 'Day_and_Hour_of_Week':
                        to_date = False
                    elif time_type == 'Day_of_Week':
                        to_date = False

                    else:
                        raise Exception("No time type specified!, but from date is specified")

                    if to_date:
                        querysets[time_type] = querysets[time_type].filter(sc_dt__lte=to_date)

            # print(querysets[time_type])

            # check = [(obj.sc_dt <= utc.localize(to_date), obj.sc_dt, to_date) for obj in querysets[time_type]]

            if time_type == 'Day' and 'week_day' in parameters:
                if parameters['week_day'] is None:
                    print('week_day is none')
                else:
                    querysets[time_type] = querysets[time_type].filter(week_day=parameters['week_day'])

            if time_type in ['Hour_of_Day', 'Day_and_Hour_of_Week', 'Day_of_Week']:
                label = 'sc_dt'
                modified_parameters = parameters['metrics']
                modified_parameters.append('week_day')
                d = querysets[time_type].values(*modified_parameters)

            else:
                label = 'sc_dt'
                d = querysets[time_type].values(*parameters['metrics'])
                print(d)

            formatted = self.format_output(d, parameters, label=label, time_type=time_type)
            if self.showConditionalFormatting:
                formatted = self.applyStdDev(formatted, time_type)
            formatted[0]['warning'] = self.warning
            output.append(formatted)

        #
        # integrity check on time types
        for group in range(len(output)):
            for subgroup in range(len(output[group])):
                output[group][subgroup]['error'] = False
                # if output[group][subgroup]['time_type'] not in self.eligible_months[self.metric_metadata[output[group][subgroup]['groupName']][0]]:
                #     output[group][subgroup]['data'] = []
                #     output[group][subgroup]['error'] = "Incorrect Time Type for This Metric"

        print(output)
        if 'pearsons' in parameters:
            self.rolling_pearsons(output, parameters['pearsons'], 10)
        return output

    def clean_custom_calendar_output(self, input, parameters):
        output = []
        for org in input:
            cleaned_output = {}
            if 'organization_id' in org:
                object = Organization.objects.get(id=org['organization_id'])
                cleaned_output['groupName'] = parameters['from'] + ' - ' + parameters['to']
                cleaned_output['name'] = object.name
                cleaned_output['type'] = object.type
                cleaned_output['id'] = [object.type, object.id, object.slug]
                cleaned_output['data'] = []
                for k, v in org.items():
                    k = k.replace('_agg', '')
                    if k == 'organization_id':
                        continue
                    else:
                        cleaned_output['data'].append({
                            'label': k,
                            'date': parameters['from'],
                            'value': round(v, 1) if v is not None else None,
                            'value_type': "number"  # TODO: do I need to change this?
                        })
                output.append(cleaned_output)
            elif 'employee_id' in org:
                object = Employee.objects.get(id=org['employee_id'])
                cleaned_output['groupName'] = parameters['from'] + ' - ' + parameters['to']
                cleaned_output['name'] = object.full_name
                cleaned_output['type'] = object.position_type
                cleaned_output['id'] = [object.position_type, object.id, object.slug]
                cleaned_output['data'] = []
                for k, v in org.items():
                    k = k.replace('_agg', '')
                    if k == 'employee_id':
                        continue
                    else:
                        cleaned_output['data'].append({
                            'label': k,
                            'date': parameters['from'],
                            'value': round(v, 1) if v is not None else None,
                            'value_type': "number"  # TODO: do I need to change this?
                        })
                output.append(cleaned_output)
        return output

    def calendar_custom(self, parameters):

        parameters = self.clean_parameters(parameters,
                                           ['time_sync_to', 'time_type', 'gt_rank', 'lt_rank', 'sc_dt', 'type',
                                            'relation', 'relation_type_only', 'anon', 'check_id_eligibility'])

        relation = parameters['relation']

        queryset = self.queryset

        default_child = self.get_index_type(
            self.object.type).lower() if self.model_reference == 'Organization' else None
        if relation == 'children':
            if self.model_reference == 'Employee':
                return []
            else:
                print(self.model_reference, "MODEL REFERENCE")
                default_child = self.default_children(self.object.type).lower()
                if self.object.type == 'Station':
                    queryset = DashboardAggregations.objects.filter(parent_id=self.object.parent.employees_under_id)
                elif self.object.type == 'Territory':
                    queryset = DashboardAggregations.objects.filter(
                        parent_id__in=self.object.children().values('id')).exclude(
                        parent_id=None)
                else:
                    queryset = DashboardAggregations.objects.filter(parent_id=self.object.id).exclude(parent_id=None)
                queryset = queryset.filter(index_type=default_child)
        elif relation == 'siblings':
            queryset = DashboardAggregations.objects.filter(parent_id=self.object.parent.id).exclude(parent_id=None)

        queryset = queryset.filter(time_type='D', sc_dt__gte=parameters['from'], sc_dt__lte=parameters['to'])

        print(queryset.query)

        annotation_dict = self.get_aggregations(parameters['metrics'])
        print(annotation_dict)

        if default_child == 'emp_driver_id' or default_child is None:
            return self.clean_custom_calendar_output(queryset.values('employee_id').annotate(**annotation_dict),
                                                     parameters)
        else:
            return self.clean_custom_calendar_output(queryset.values('organization_id').annotate(**annotation_dict),
                                                     parameters)
        # return queryset.values('organization_id').annotate(**annotation_dict)

    def calendar(self, parameters):

        class StdDev(Func):
            template = 'STD(%(expressions)s)'

        q = DashboardAggregations.objects

        parameters = self.clean_parameters(parameters,
                                           ['time_sync_to', 'time_type', 'gt_rank',
                                            'lt_rank', 'sc_dt', 'type', 'relation',
                                            'relation_type_only', 'anon', 'check_id_eligibility', 'child_type'])

        if (self.model_reference == 'Employee' or self.object_type == 'Grid') and parameters['relation'] in ['children',
                                                                                                             'siblings']:
            return []
        elif self.model_reference == 'Employee':
            self.object.facility_type = self.object.organization.facility_type

        if 'ranking' not in parameters and 'custom' not in parameters['time_type']:
            parameters['metrics'] = parameters['metrics'] + ['sc_dt', 'id_name_helper', 'index_type']
            # if parameters['relation'] == 'children' and parameters['time_type'][0] != 'TIMESERIES':
            #     parameters['metrics'].append('parent_id')
        else:
            for metric in parameters['metrics']:
                if metric.endswith('avg'):
                    parameters['metrics'].append(metric.replace('avg', 'count'))

        # filter down to appropriate index
        annotation_dict = {}
        parent_lookup_dict = {}

        def quick_converter(m):
            quick_converter_d = {
                'parent_id': 'Parent Geography',
                'id_name_helper': 'name',
                'index_type': 'type',
            }

            if m in quick_converter_d:
                return quick_converter_d[m]
            else:
                return m

        std_dict = {}
        avg_dict = {}
        for m in parameters['metrics']:
            converted_name = quick_converter(m)
            annotation_dict[converted_name] = F(m)
            if any(word in converted_name for word in ['freq', 'count', 'avg', 'median', 'volume']):
                std_dict[converted_name + '_std'] = StdDev(m)
                avg_dict[converted_name + '_avg'] = Avg(m)

        '''print(annotation_dict, "ANNOTATIONS")
        print(std_dict, "STD DICT")
        print(std_dict, "AVG DICT")'''

        if parameters['relation'] == 'siblings':
            self.object = self.object.parent

        # filter time type
        time_types = set()
        sc_dt_filters = set()
        today = dt.date.today()
        if today.day < 4:
            today = today - relativedelta.relativedelta(months=1)
            self.warning = "Its still too early to set THIS MONTH to the new calendar month. We will make the switch on the 4th."
        this_month = today.replace(day=1)
        this_week = today - relativedelta.relativedelta(days=today.weekday())
        this_year = today.replace(day=1)
        this_year = this_year.replace(month=1)
        for t in parameters['time_type']:
            conv_t = self.time_type_conversions[t]
            time_types.add(conv_t)
            if t == 'This_Month':
                sc_dt_filters.add((conv_t, this_month, t))

            elif t == 'Prev_Month':
                prev_month = this_month - relativedelta.relativedelta(months=1)
                sc_dt_filters.add((conv_t, prev_month, t))
            elif t == 'custom':
                return self.calendar_custom(parameters)
            elif t == 'Week':
                sc_dt_filters.add((conv_t, this_week, t))
            elif t == 'Prev_week':
                prev_week = this_week - relativedelta.relativedelta(weeks=1)
                sc_dt_filters.add((conv_t, prev_week, t))
            elif t == 'YTD':
                sc_dt_filters.add((conv_t, this_month.replace(month=1), t))
            elif t == 'Prev_Year':
                prev_year = this_year - relativedelta.relativedelta(years=1)
                sc_dt_filters.add((conv_t, prev_year, t))
            elif t == 'This_Incentive':
                today = dt.date.today()

                if self.object.facility_type == 'Fleet':
                    fac_type = 'fleet'
                else:
                    fac_type = 'csn'
                period = \
                    Std12ETierTimePeriods.objects.filter(start__lte=today, show_until__gt=today,
                                                         type=fac_type).order_by(
                        'start')[0]
                max_date = period.end
                min_incentive_date = period.start
                self.warning = period.name
                # max_date = DashboardAggregations.objects.filter(time_type='INCENTIVE').latest('sc_dt').sc_dt
                sc_dt_filters.add((conv_t, max_date, t))
            elif t == 'Last_Incentive':
                today = dt.date.today()

                if self.object.facility_type == 'Fleet':
                    fac_type = 'fleet'
                else:
                    fac_type = 'csn'
                period = \
                    Std12ETierTimePeriods.objects.filter(start__lte=today, show_until__lte=today,
                                                         type=fac_type).order_by(
                        '-start')[0]

                max_date = period.end
                min_incentive_date = period.start
                self.warning = period.name
                # max_date = DashboardAggregations.objects.filter(time_type='INCENTIVE').latest('sc_dt').sc_dt
                sc_dt_filters.add((conv_t, max_date, t))
            elif t == 'This_Quarter':

                max_date = DashboardAggregations.objects.filter(organization_id=7, time_type='Q').latest('sc_dt').sc_dt

                sc_dt_filters.add((conv_t, max_date, t))
            elif conv_t == 'HOUR_GROUP':
                if 'time_filter' in parameters:
                    if isinstance(parameters['time_filter'], list):
                        max_date = ()
                        for i in parameters['time_filter']:
                            max_date = max_date + (i,)
                    else:
                        max_date = parameters['time_filter']
                else:
                    max_date = ('8', '9', '10', '11', '12', '13', '14', '15', '16', '17')
                sc_dt_filters.add((conv_t, max_date, t))
            elif conv_t == 'WEEKDAY_GROUP':
                if 'time_filter' in parameters:
                    if isinstance(parameters['time_filter'], list):
                        max_date = ()
                        for i in parameters['time_filter']:
                            max_date = max_date + (i,)
                    else:
                        max_date = parameters['time_filter']
                else:
                    max_date = ('0', '1', '2', '3', '4', '5', '6')

                sc_dt_filters.add((conv_t, max_date, t))
            elif conv_t == 'WEEKDAY_HOUR_GROUP':
                if 'time_filter' in parameters:
                    if isinstance(parameters['time_filter'], list):
                        max_date = ()
                        for i in parameters['time_filter']:
                            max_date = max_date + (i,)
                    else:
                        max_date = parameters['time_filter']
                else:
                    max_date = ['0-12', '0-11']
                sc_dt_filters.add((conv_t, max_date, t))
            elif t == 'TIMESERIES':
                if 'time_type_filter' in parameters:
                    # get dates in range with time_type
                    time_types = self.time_type_conversions[parameters['time_type_filter']]
                    conv_t = time_types
                    if time_types == 'H':
                        parameters['from'] = parameters['from'][:10] + " 00:00:00"
                        parameters['to'] = parameters['to'][:10] + " 00:00:00"
                        # print(parameters['from'], parameters['to'])
                dates = tuple(
                    DashboardAggregations.objects.filter(organization_id=7, time_type=conv_t,
                                                         sc_dt__gte=parameters['from'],
                                                         sc_dt__lte=parameters['to']).values_list('sc_dt', flat=True))
                # print("THESE ARE DATES", dates)
                for date in dates:
                    # print(date)
                    sc_dt_filters.add((conv_t, date, t))

        if type(time_types) != set:
            tt = [time_types, ]
        else:
            tt = list(time_types)
        q = q.filter(time_type__in=tt)

        if 'filters' in parameters:
            print('not broken yet');
            filterQuery = {}
            for k, v in parameters['filters'].items():
                if v is not None:
                    print('k', k)
                    print('v', v)
                    filterQuery[k] = v
                print('These are filter queries', filterQuery);
            q = q.filter(**filterQuery)

            print('This is q', q)
        # deal with relations management
        child_type = False
        if not parameters['relation'] or parameters['relation'] == 'self':
            if self.model_reference == 'Employee':
                q = q.filter(employee_id=self.object.id)


            else:
                q = q.filter(organization_id=self.object.id)
        elif "org_list" in parameters['relation']:
            q = q.filter(organization_id__in=parameters['org_list'])
        else:
            child_type = parameters['child_type'] if parameters['child_type'] else self.get_index_type(
                self.default_children(
                    self.get_index_type(self.object.type, reverse=True)))

            if child_type in ['Club-Region', 'Market', 'Territory'] and 'Facility-Type' in self.object.type:
                child_type = child_type + '-Facility-Type'

            if child_type in ['Driver']:
                annotation_dict['name'] = F('employee__full_name')
                if self.object.type == 'Station':
                    min_date = min([x[1] if x[0] != 'INCENTIVE' else min_incentive_date for x in sc_dt_filters])
                    # print(min_date, "MIN DATE")
                    relevant_drivers = StationDriver.objects.filter(station_id=self.object.id,
                                                                    last_sc_dt__gte=min_date).values_list('driver_id',
                                                                                                          flat=True)
                    # print(len(relevant_drivers))
                    q = q.filter(index_type=self.get_index_type(child_type)).filter(
                        employee_id__in=relevant_drivers).exclude(employee_id=1).filter(
                        employee_id__in=self.object.parent.employees_under.employees())
                    # print(q, "WHAT IS HERE?")
                    self.warning = "NOTE: All drivers that have run calls for this station in the time period shown are listed below. " \
                                   "However, scores shown for each driver are for the entire station-business. " \
                                   "(This does not apply if you only have one station ID) "
                else:

                    q = q.filter(index_type="EMP_DRIVER_ID").filter(
                        employee_id__in=self.object.lineage("Driver"))

            else:
                if self.object.type == 'Club':
                    q = q.filter(index_type=self.get_index_type(child_type))
                else:
                    q = q.filter(index_type=self.get_index_type(child_type)).filter(
                        organization_id__in=self.object.lineage(child_type))
                # print(q)

                # this is much faster than a bunch of sql queries
            relevant_organizations = Organization.objects.filter(type=self.default_parent(child_type)).values(
                'name', 'id', 'employees_under_id', 'parent_name')
            for org in relevant_organizations:
                parent_lookup_dict[org['id']] = (org['name'], org['parent_name'])

        # print("LOOKUP DICT", parent_lookup_dict)

        def assign_value_in_data(m, out):
            if m == 'Parent Geography':
                if parameters['relation'] == 'self':
                    if hasattr(self.object, 'name'):
                        return self.object.name
                    else:
                        return self.object.full_name

                if out['type'] == 'Station':
                    if out[m] is not None:
                        try:
                            return parent_lookup_dict[out[m]][1]
                        except:
                            return None
                    else:
                        return None
                else:
                    try:
                        return parent_lookup_dict[out[m]][0]
                    except:
                        return None
            else:
                return self.convert_percentage(out[m], self.field_name_conversion(m))

        # clean up formatting so vue knows what to do with it
        final_out = []
        out = []
        # print(sorted(sc_dt_filters, key=lambda x: x[1]), "SC_DT_FILTERS")

        for time_type, sc_dt, display_time_type in sorted(sc_dt_filters, key=lambda x: x[1]):
            if time_type in ['HOUR_GROUP', 'WEEKDAY_GROUP', 'WEEKDAY_HOUR_GROUP']:
                if isinstance(sc_dt, tuple):

                    this_period = q.filter(week_day__in=list(sc_dt), time_type=time_type)
                else:
                    this_period = q.filter(week_day=sc_dt, time_type=time_type)
            else:
                # print(sc_dt)
                # print(time_type)
                # print(q)
                this_period = q.filter(sc_dt=sc_dt, time_type=time_type)
                # print(this_period)

            # print(this_period)

            if child_type in ['Driver', ]:
                model_type = 'employee'
            else:
                model_type = 'organization'
            if time_type in ['HOUR_GROUP', 'WEEKDAY_GROUP', 'WEEKDAY_HOUR_GROUP']:
                out = this_period.values('time_type', 'week_day', model_type + '__slug', model_type + '_id').annotate(
                    **annotation_dict)
            else:
                out = this_period.values('time_type', model_type + '__slug', model_type + '_id').annotate(
                    **annotation_dict)

            out = self.reduce_size(parameters, out)
            out_std = {}
            out_avg = {}
            if 'relation' in parameters and self.showConditionalFormatting:
                if parameters['relation'] != 'self':
                    try:
                        out_std = list(this_period.annotate(**std_dict).values())[0]
                        out_avg = list(this_period.annotate(**avg_dict).values())[0]
                    except:
                        print("std deviation went wrong")

            # print("OUT STD", out_std)
            def ranking_calculator(score_list):
                for_rankings = [-1 * score for score in score_list]
                # all_ranks = ss.rankdata(for_rankings, method='min')
                # return all_ranks

                #TODO: scipy really?
                return None

            if 'ranking' in parameters:

                if len(out) > 0:
                    if 'employee_id' in list(out[0].keys()):
                        rank_key = 'employee_id'
                    else:
                        rank_key = 'organization_id'

                    get_key = [x for x in list(out[0].keys()) if
                               x not in ['time_type', 'employee__slug', 'name', 'employee_id',
                                         'organization__slug', 'organization_id']]

                    if len(get_key) != 2:
                        return {"Need count to rank"}

                    final_rankings = {}
                    score_list = []
                    id_list = []
                    for o in range(len(out)):
                        if out[o][get_key[0]] is not None:
                            if int(out[o][get_key[1]]) < 5:
                                final_rankings[out[o][rank_key]] = 'N/A'
                            else:
                                id_list.append(out[o][rank_key])
                                score_list.append(float(out[o][get_key[0]]))
                        else:
                            final_rankings[out[o][rank_key]] = 'N/A'

                    ranked = ranking_calculator(score_list)
                    rankings_length = len(ranked)
                    for i, j in zip(id_list, ranked):
                        final_rankings[i] = j

                    if parameters['ranking'] == 'all':

                        for o in range(len(out)):
                            out[o]['data'] = []
                            out[o]['groupName'] = display_time_type
                            # out[o]['type'] = self.get_index_type(out[o]['type'], reverse=True)

                            for m in parameters['metrics']:
                                m = quick_converter(m)
                                if m not in ['type', 'name', 'sc_dt'] and 'count' not in m:
                                    out[o]['data'].append({
                                        # 'date': str(out[o]['sc_dt'])[:10],
                                        'label': m,
                                        'value': assign_value_in_data(m, out[o]),
                                        'value_type': self.field_name_conversion(m),
                                        'std_val': self.calculate_deviation(out_std, out_avg, m,
                                                                            assign_value_in_data(m, out[o]),
                                                                            self.field_name_conversion(m), sc_dt,
                                                                            time_type),
                                        'ranking': final_rankings[out[o][rank_key]],
                                        'total_rankings': rankings_length
                                    })
                                    del out[o][m]
                            out[o]['id'] = [model_type + '_id', out[o][model_type + '_id'],
                                            out[o][model_type + '__slug']]

                            del out[o][model_type + '_id']
                            del out[o][model_type + '__slug']

                        final_out = final_out + list(out)

                    else:
                        single_emp = {}
                        single_emp_list = []
                        single_emp['data'] = []
                        single_emp['groupName'] = display_time_type

                        for x in out:
                            if x[rank_key] == parameters['ranking']:
                                emp_info = x
                                break

                        m = quick_converter(parameters['metrics'][0])
                        single_emp['data'].append({
                            'label': m,
                            'value': assign_value_in_data(m, emp_info),
                            'value_type': self.field_name_conversion(m),
                            'std_val': self.calculate_deviation(out_std, out_avg, m, assign_value_in_data(m, emp_info),
                                                                self.field_name_conversion(m), sc_dt, time_type),
                            'ranking': final_rankings[emp_info[rank_key]],
                            'total_rankings': rankings_length
                        })

                        single_emp['id'] = [model_type + '_id', emp_info[model_type + '_id'],
                                            emp_info[model_type + '__slug']]

                        single_emp_list.append(single_emp)
                        final_out = final_out + single_emp_list

            else:

                for o in range(len(out)):

                    out[o]['data'] = []
                    out[o]['groupName'] = display_time_type
                    print(out[o])

                    # try:
                    out[o]['type'] = self.get_index_type(out[o]['type'], reverse=True)
                    # except:
                    #     out[o]['type'] = 'EMP_DRIVER_ID'
                    #     out[o]['type'] = self.get_index_type(out[o]['type'], reverse=True)

                    for m in parameters['metrics']:
                        m = quick_converter(m)
                        if m not in ['type', 'name', 'sc_dt']:
                            out[o]['data'].append({
                                'date': str(out[o]['sc_dt'])[:10],
                                'label': m,
                                'value': assign_value_in_data(m, out[o]),
                                'value_type': self.field_name_conversion(m),
                                'std_val': self.calculate_deviation(out_std, out_avg, m,
                                                                    assign_value_in_data(m, out[o]),
                                                                    self.field_name_conversion(m), sc_dt, time_type),
                                # 'std': out_std[m+"_std"] if m+"_std" in out_std else None,
                                # 'avg': out_std[m+"avg"] if m+"avg" in out_std else None
                            })
                            del out[o][m]
                    if self.model_reference == 'Employee':
                        out[o]['id'] = ['employee_id', self.object.id, self.object.slug]
                    else:
                        out[o]['id'] = [model_type + '_id', out[o][model_type + '_id'], out[o][model_type + '__slug']]

                    del out[o][model_type + '_id']
                    del out[o][model_type + '__slug']

                final_out = final_out + list(out)

        # if 'children' in final_out and len("children") == 0:
        #     final_out['children'] = [[]]
        return final_out

    def rankings(self, label, value, type, comparator, sc_dt, time_type):
        filter_kwargs = {'{0}__{1}'.format(label, comparator): value}
        filter_kwargs['index_type'] = self.get_index_type(type)
        filter_kwargs['sc_dt'] = sc_dt
        filter_kwargs['time_type'] = time_type
        try:
            output = DashboardAggregations.objects.filter(**filter_kwargs).count() + 1
        except ValueError:
            output = None
        return output

    def timeseries_predictor(self, params):
        ActionsLogger(self.request.user, 'TimeseriesPredictionsByHour', 'New Visit to Scheduler', 'Scheduler', details=[
            {'db_action_type': 'get_data',
             'db_model': 'TimeseriesPredictionsByHour',
             'db_model_id': self.object.id,
             'context': "getting forecast data by organization", }
        ])

        params = self.clean_parameters(params, ['date', 'scheduler_type'])
        if params['scheduler_type']:
            if params['scheduler_type'] == 'hourly':
                hourly_predictions = TimeseriesPredictionsByHourNew.objects.all()
            else:
                hourly_predictions = TimeseriesPredictionsByHourNew.objects.all()
        else:
            hourly_predictions = TimeseriesPredictionsByHourNew.objects.all()

        if params['date']:
            date = dt.datetime.strptime(params['date'], '%Y-%m-%d')
        else:
            date = dt.datetime.now(dt.timezone.utc)

        time_frame = hourly_predictions.filter(organization_id=self.object.id).first().time_type

        print('time_type is ', time_frame)

        timeDeltaLookup = {
            '1h': 31,
            '4h': 124,
            '1d': 230
        }


        hourly_predictions_dt = hourly_predictions.filter(sc_dt__range=[date, date + dt.timedelta(hours=timeDeltaLookup[time_frame])])

        hourly_predictions = hourly_predictions_dt.filter(organization_id=self.object.id).order_by('sc_dt')

        if params['children_filter'] == True:
            child = params['child_list']
            output = hourly_predictions_dt.filter(organization_id__in=child).values('sc_dt', 'code').annotate(
                    volume_pred=Sum('volume_pred'),
                    actual_volume=Sum('actual_volume'),
                    productivity=Avg('productivity'),
                    rollover_hour_minus_one=Sum('rollover_hour_minus_one'),
                    rollover_hour_minus_two=Sum('rollover_hour_minus_two'),
                    rollover_hour_minus_three=Sum('rollover_hour_minus_three'),
                    new_drivers_needed=Sum('new_drivers_needed'),
                    drivers_needed=Sum('drivers_needed'),
                    waiters=Sum('waiters'),
                    send_home=Sum('send_home'),
                    total_drivers=Sum('total_drivers'),
                    total_drivers_wait_15=Sum('total_drivers_wait_15')
                )
        else:
            print('using serializer')
            output = TimeseriesPredictionsByHourSerializer(hourly_predictions, many=True).data


        # hourly_predictions.annotate(rollover_drivers=F('rollover_hour_minus_one') + F('rollover_hour_minus_two') + F('rollover_hour_minus_three'))
        # print(hourly_predictions.values())
        avl_zones = []
        # if self.object.facility_type == 'Fleet':
        #     children = [{'id': child.id, 'name': child.name, 'slug': child.slug} for child in
        #                 Organization.objects.filter(id__in=self.object.lineage('Station'))]
        #
        # elif self.object.type == 'Territory' and self.object.facility_type != 'Fleet':
        #
        #     if params['children_filter'] == True:
        #         child = params['child_list']
        #     else:
        #         child = Organization.objects.filter(parent_id=self.object.id, type='Station-Business').values_list('id', flat=True)
        #
        #     print(child)
        #     stations_id = hourly_predictions_dt.filter(organization_id__in=child).values_list('organization_id',
        #                                                                               flat=True).distinct()
        #
        #     print(stations_id)
        #     children = [{'id': child.id, 'name': child.name, 'slug': child.slug} for child in
        #                 Organization.objects.filter(id__in=stations_id)]
        #
        #     avl_zones = [{'id': avl.id, 'name': avl.name, 'slug': avl.slug} for avl in
        #                  Organization.objects.filter(type='avl_zone', parent_id=self.object.parent.id)]
        # else:
        #     children = [{'name': child.name, 'slug': child.slug} for child in self.object.children()]
        if self.object.type == 'Station-State':
            children_list = self.object.children(emp_type=self.request.user.employee().position_type).values_list('id', flat=True)
            children_with_pred = TimeseriesPredictionsOrgsPredicted.objects.filter(organization__in=children_list).values_list('organization', flat=True)
            children = [{'id': o.id, 'name': o.name, 'slug': o.slug} for o in Organization.objects.filter(id__in=children_with_pred)]
        elif self.object.type in ['Facility-Rep', 'Hub']:
            children_list = Organization.objects.filter(parallel_parents__in=[self.object.id])
            children_with_pred = TimeseriesPredictionsOrgsPredicted.objects.filter(
                organization__in=children_list).values_list('organization', flat=True)
            children = [{'id': o.id, 'name': o.name, 'slug': o.slug} for o in
                        Organization.objects.filter(id__in=children_with_pred)]
        else:
            children = []
        if len(output) > 0:
            return {'hours': output, 'children': children, 'avl_zones': avl_zones}
        else:
            return {'message', 'no data available'}

    def get_skill_level(self, parameters):
        '''
        :example request
            {
                "purpose": "get_skill_level",
                "type": "Driver",
                "slug":"115-errol-sutherland",
                "parameters": {
                        "skill_name": "*",

                    "organization_id":[85],
                    "tenure":["2020-01-03", "2019-02-08"],
                    //"employee_id":[1234]
                    "filters"
                }
            }
        }
        :return: skill level, minimum/maximum values of given skill level, actual value
        {
            "employee_id": 37225,
            "skill_name": "truck_call_member_count",
            "level": 5,
            "min_level_value": 120.0,
            "max_level_value": 239.0,
            "emp_value": 198,
            "tenure_average": 63.55586206896552
        }
        '''

        try:
            """
            TODO: 
            station level filtering, 
            Territory/market aggregation.  only aggregating by station biz now
            """

            if parameters['skill_name'] == '*':
                all_skills = list(SkillLevels.objects.values_list('skill_name', flat=True).distinct())
            else:
                all_skills = parameters['skill_name']

            filtered_emps = SkillLevelsEmployee.objects.filter(skill_name__in=all_skills)

            if 'organization_id' in parameters:
                org_types = list(Organization.objects.filter(id__in=parameters['organization_id']).values_list('type'))
                org_list = []
                org_level_dict = {}
                for org, org_type in zip(parameters['organization_id'], org_types):
                    if org_type[0] == 'Station-Business':
                        org_list.append(org)
                    elif org_type[0] == 'Territory':
                        station_biz_ids = list(
                            Organization.objects.filter(parent_id=org, type='Station-Business').values_list('id'))
                        for id in station_biz_ids:
                            org_list.append(id[0])
                    elif org_type[0] == 'Market':
                        station_biz_ids = list(
                            Organization.objects.filter(grandparent_id=org, type='Station-Business').values_list('id'))
                        for id in station_biz_ids:
                            org_list.append(id[0])
                    elif org_type[0] == 'Club':
                        station_biz_ids = list(Organization.objects.filter(type='Station-Business').values_list('id'))
                        for id in station_biz_ids:
                            org_list.append(id[0])

                filtered_emps = filtered_emps.filter(organization_id__in=org_list)

            if 'employee_id' in parameters:
                filtered_emps = filtered_emps.filter(emp_driver_id__in=parameters['employee_id'])

            if 'tenure' in parameters:
                tenure_dates = []
                for date in parameters['tenure']:
                    tenure_dates.append(list(SkillLevelsTenureLevels.objects.filter(quarter_start_date__lte=date,
                                                                                    quarter_end_date__gte=date).values_list(
                        'quarter_start_date'))[0][0].strftime("%Y-%m-%d"))
                filtered_emps = filtered_emps.filter(tenure__in=tenure_dates)

            if 'skill_level' in parameters:
                filtered_emps = filtered_emps.filter(skill_level__in=parameters['skill_level'])

            emps_values = Employee.objects.filter(id__in=filtered_emps.values_list('employee_id')).values('id',
                                                                                                          'full_name')
            org_values = Organization.objects.filter(id__in=filtered_emps.values_list('organization_id')).values('id',
                                                                                                                 'name')

            output = []
            all_skill_stuff = filtered_emps.values_list('employee_id', 'organization_id', 'start_date',
                                                        'skill_name', 'value', 'tenure',
                                                        'tenure_average', 'skill_level', 'skill_level_min',
                                                        'skill_level_max', 'aggregated')

            all_skill_stuff = [list(item[1]) for item in itertools.groupby(sorted(all_skill_stuff), key=lambda x: x[0])]

            emps_values_dict = {}
            org_values_dict = {}
            # return emps_values
            for item in emps_values:
                emps_values_dict[item['id']] = item['full_name']
            for item in org_values:
                org_values_dict[item['id']] = item['name']

            for item in all_skill_stuff:
                try:
                    emp = {'employee_id': item[0][0],
                           'employee_name': emps_values_dict[item[0][0]],
                           'organization_id': item[0][1],
                           'org_name': org_values_dict[item[0][1]],
                           'start_date': item[0][2],
                           'tenure_group': item[0][5]}
                    emp['skills'] = []
                    for skill in item:
                        emp['skills'].append({'skill_name': skill[3], 'value': skill[4], 'tenure_average': skill[6],
                                              'skill_level': skill[7], 'skill_level_min': skill[8],
                                              'skill_level_max': skill[9], 'aggregated': skill[10]})
                    output.append(emp)
                except:
                    print('failed to parse')
            return output

        except ValueError:
            output = None

        return output

    def driverScheduler(self, params):
        params = self.clean_parameters(params, ['date' ])
        date = dt.datetime.strptime(params['date'], '%Y-%m-%d')
        schedule = TimeseriesScheduledDrivers.objects.filter(employee_id=self.object.id, start_date__gte=date, schedule__publish=True)
        output = TimeseriesScheduledDriversSerializer(schedule, many=True).data
        return output

    def scheduler_utils(self, params):
        # this is the direction we are heading with keeping the scheduler stuff at a different file
        # this will mainly be directed to cater to RDB2
        params = self.clean_parameters(params,
                                       ['action', 'date', 'drivers', 'filter', 'view_by', 'process', 'scheduler_type'])
        action = params['action']
        date = dt.datetime.strptime(params['date'], '%Y-%m-%d')
        action_url = '/dashboard/{0}?section=scheduler'.format(self.object.slug)
        utils_actions = {
            # SCHEDULE FOR THE DAY
            'save': save_schedule,
            'use_prev_day': use_prev_day,
            'user_profile_day': user_profile_day,
            # SCHEDULE FOR THE WEEK
            'schedule_with_profiler': schedule_with_profiler,
            # REPORTS
            'schedule': schedule,
            'weekly_schedule_split': weekly_schedule_split,
            'publish': publish,
            'summed_predictions': summed_predictions,
            'comparison': comparison,
            'compare_metrics': compare_metrics,
            'comparison_report': comparison_report,
            'new_expectations': new_expectations,
            'full_report': full_report,
            # TEMPLATE
            'get_templates': get_templates,
            'delete_template': delete_template,
            'generate_from_template': generate_from_template,
            # OTHER
            'placeholder_handler': placeholder_handler,
            'drivers': drivers,
            'get_overnight_drivers': get_overnight_drivers
        }
        if action == 'save':
            action_display = '{0} schedule saved for {1}'.format(date.strftime('%m/%d/%Y'), self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)
        elif action == 'use_prev_day':
            action_display = '{0} schedule using the previous\' day schedule for {1}'.format(date.strftime('%m/%d/%Y'),
                                                                                             self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)
        elif action == 'user_profile_day':
            action_display = '{0} schedule saved using profiler as template for {1}'.format(date.strftime('%m/%d/%Y'),
                                                                                            self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)
        elif action == 'generate_from_template':
            action_display = 'Used default schedule to create the schedule for the week of {0} for {1}'.format(
                date.strftime('%m/%d/%Y'), self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

        return utils_actions[action](date, params, self.object)

    def scheduler_navigate(self, params):
        org = self.object
        type = org.type
        output = {
            'Station-State': [],
            'Facility-Rep': [],
            'Hub': [],
            'Station-Business': []
        }
        predicted_stations = TimeseriesPredictionsOrgsPredicted.objects.all().order_by('time_type', 'org_name')
        # predicted_stations = [int(x) for x in list(set(predicted_stations))]
        # print(predicted_stations)
        orgs = Organization.objects.filter(id__in=predicted_stations.values_list('organization', flat=True))

        filter_sb = params.get('filter_sb', False)
        if filter_sb:
            get_all = params.get('get_all', False)
            if get_all:
                sb = orgs.filter(type='Station-Business').values('id', 'name', 'parent_id', 'parallel_parents', 'slug')

                return sb
            else:
                parallel_org = params.get('parallel_org', None)
                sb = orgs.filter(parallel_parents__in=[parallel_org]).values('id', 'name', 'parent_id',
                                                                             'parallel_parents', 'slug')
                return sb

        all_types = ['Station-State', 'Facility-Rep', 'Hub', 'Station-Business']
        parallel_parent_types = ['Facility-Rep', 'Hub']
        if type == 'Club':
            for a in all_types:
                print(a)
                out_q = orgs.filter(type=a)
                out_v = out_q.values('id', 'name', 'parent_id', 'slug')
                output[a] = out_v
        else:
            print('starting to filter the station-business', dt.datetime.now())
            if self.object.type in parallel_parent_types:
                unique_obj = []
                out = orgs.filter(parallel_parents__in=[self.object.id]).values('id', 'name', 'parent_id', 'parallel_parents', 'slug')
                # for o in sb:
                #     if o.id not in unique_obj:
                #         unique_obj.append(o.id)
                # out = org.filter(id__in=sb).values('id', 'name', 'parent_id', 'parallel_parents', 'slug')
            else:
                out = orgs.filter(id__in=org.lineage('Station-Business')).values('id', 'name', 'parent_id', 'parallel_parents', 'slug')
            out_list = out.values_list('id', flat=True)
            print('got organizations, filtering predicted orgs', dt.datetime.now())

            output_list = []
            def check_in_list(item):
                for o in output_list:
                    if o['id'] == item['id']:
                        return False
                return True

            time_type_order = {'1h': 0, '4h': 1, '1d': 2}
            for o in out:
                if check_in_list(o):
                    tt = predicted_stations.filter(organization=o['id'])[0].time_type
                    item = {
                        'id': o['id'],
                        'name': o['name'],
                        'parent_id': o['parent_id'],
                        'parallel_parents': o['parallel_parents'],
                        'slug': o['slug'],
                        'order': time_type_order[tt],
                        'time_type': tt
                    }
                    output_list.append(item)
            # [o.update({'order': predicted_orgs.index(o['id'])}) for o in output_list]

            output_list = list(output_list)
            output_list = sorted(output_list, key=lambda x: (x['order'], x['name']))
            print(output_list)
            output['Station-Business'] = output_list

        return output

    def scheduler(self, params):
        params = self.clean_parameters(params,
                                       ['action', 'date', 'drivers', 'filter', 'view_by', 'process', 'scheduler_type'])
        action = params['action']
        date = dt.datetime.strptime(params['date'], '%Y-%m-%d')
        action_url = '/dashboard/{0}?section=scheduler'.format(self.object.slug)
        all_parents = ['Station-State', 'Facility-Rep', 'Hub']
        parallel_parent_types = ['Facility-Rep', 'Hub']
        # creates or gets the schedule for specific date and organization.
        # If there are more than one schedule with the same date, then it will delete the excess schedules.
        try:
            schedule = TimeseriesSchedule.objects.get_or_create(organization_id=self.object.id, date=date)[0]
        except:
            schedules = TimeseriesSchedule.objects.filter(organization_id=self.object.id, date=date)
            schedule = schedules[0]
            for s in schedules:
                if s.id != schedule.id:
                    s.delete()
        ###### Scheduler: save DAILY schedule ######
        if action == 'save':
            # saves the scheduled drivers to the schedule.
            try:
                drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()
            except:
                pass

            new_drivers = params['drivers']
            print('new drivers to be saved', new_drivers)
            def get_proper_id(did, obj):
                if did is None:
                    return None
                else:
                    if obj == 'employee':
                        return Employee.objects.get(id=did)
                    else:
                        return PlaceholderDriver.objects.get(id=did)

            def get_end_date(date, duration):
                true_duration = duration / 4
                if true_duration < 0:
                    true_duration += 24
                start_date = dt.datetime.strptime(date, '%Y-%m-%d %H:%M')
                end_date = start_date + dt.timedelta(hours=true_duration)
                return end_date
            all_new_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                [TimeseriesScheduledDrivers(
                    employee=get_proper_id(d['employee'], 'employee'),
                    start_date=dt.datetime.strptime(d['start_date'], '%Y-%m-%d %H:%M'),
                    duration=d['duration'] / 4,
                    end_date=get_end_date(d['start_date'], d['duration']),
                    schedule_type=d['schedule_type'],
                    schedule=schedule,
                    placeholder=get_proper_id(d['placeholder'], 'placeholder')
                ) for d in new_drivers]
            )
            self.save_daily_schedule(date, all_new_drivers)
            schedule.publish = params['publish']
            schedule.save()

            action_display = '{0} schedule saved for {1}'.format(date.strftime('%m/%d/%Y'), self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

            return {'success': True}

        elif action == 'publish':
            pub_schedule = TimeseriesSchedule.objects.filter(id__in=params['publish'])
            for p in pub_schedule:
                p.publish = True
                p.save()

            return {'schedule_published': True}
        elif action == 'use_prev_day':
            yesterday = date - dt.timedelta(days=1)
            yesterday_schedule = TimeseriesSchedule.objects.get(date=yesterday, organization_id=self.object.id)
            scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=yesterday_schedule)
            try:
                schedule = TimeseriesSchedule.objects.get_or_create(organization_id=self.object.id, date=date)[0]
            except:
                schedules = TimeseriesSchedule.objects.filter(organization_id=self.object.id, date=date)
                schedule = schedules[0]

            del_drivers_shcedule = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()

            drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                [TimeseriesScheduledDrivers(
                    employee=d.employee,
                    start_date=d.start_date + dt.timedelta(days=1),
                    end_date=d.end_date + dt.timedelta(days=1),
                    duration=d.duration,
                    schedule_type=d.schedule_type,
                    schedule=schedule,
                    placeholder=d.placeholder
                ) for d in scheduled_drivers]
            )
            self.save_daily_schedule(date, drivers)
            drivers_s = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)

            action_display = '{0} schedule using the previous\' day schedule for {1}'.format(date.strftime('%m/%d/%Y'),
                                                                                             self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

            output = TimeseriesScheduledDiversTemplateSerializer(drivers_s).data
            return output
        elif action == 'placeholder_handler':
            handle = params['handle']
            if handle == 'create':
                ghost = params['ghost']
                ph = PlaceholderDriver.objects.create(
                    name=ghost['name'],
                    organization_id=self.object.id,
                    sun_start='00:00:00',
                    sun_end='00:00:00',
                    mon_start='00:00:00',
                    mon_end='00:00:00',
                    tue_start='00:00:00',
                    tue_end='00:00:00',
                    wed_start='00:00:00',
                    wed_end='00:00:00',
                    thu_start='00:00:00',
                    thu_end='00:00:00',
                    fri_start='00:00:00',
                    fri_end='00:00:00',
                    sat_start='00:00:00',
                    sat_end='00:00:00',
                    sun_available=True,
                    mon_available=True,
                    tue_available=True,
                    wed_available=True,
                    thu_available=True,
                    fri_available=True,
                    sat_available=True,
                )
                ph.save()
            elif handle == 'save_changes':
                ghosts = params['ghosts']
                for ghost in ghosts:
                    ph = PlaceholderDriver.objects.get(id=ghost['id'])
                    ph.name = ghost['name']
                    ph.service_type = ghost['service_type']
                    ph.sun_start = ghost['sun_start'] if ghost['sun_available'] else None
                    ph.sun_end = ghost['sun_end'] if ghost['sun_available'] else None
                    ph.mon_start = ghost['mon_start'] if ghost['mon_available'] else None
                    ph.mon_end = ghost['mon_end'] if ghost['mon_available'] else None
                    ph.tue_start = ghost['tue_start'] if ghost['tue_available'] else None
                    ph.tue_end = ghost['tue_end'] if ghost['tue_available'] else None
                    ph.wed_start = ghost['wed_start'] if ghost['wed_available'] else None
                    ph.wed_end = ghost['wed_end'] if ghost['wed_available'] else None
                    ph.thu_start = ghost['thu_start'] if ghost['thu_available'] else None
                    ph.thu_end = ghost['thu_end'] if ghost['thu_available'] else None
                    ph.fri_start = ghost['fri_start'] if ghost['fri_available'] else None
                    ph.fri_end = ghost['fri_end'] if ghost['fri_available'] else None
                    ph.sat_start = ghost['sat_start'] if ghost['sat_available'] else None
                    ph.sat_end = ghost['sat_end'] if ghost['sat_available'] else None
                    ph.sun_available = ghost['sun_available']
                    ph.mon_available = ghost['mon_available']
                    ph.tue_available = ghost['tue_available']
                    ph.wed_available = ghost['wed_available']
                    ph.thu_available = ghost['thu_available']
                    ph.fri_available = ghost['fri_available']
                    ph.sat_available = ghost['sat_available']
                    ph.save()
                return {'success': 'True'}
            elif handle == 'update':
                ghost = params['ghost']
                ph = PlaceholderDriver.objects.get(id=ghost['id'])
                ph.name = ghost['name']
                ph.service_type = ghost['service_type']
                ph.sun_start = ghost['sun_start']
                ph.sun_end = ghost['sun_end']
                ph.mon_start = ghost['mon_start']
                ph.mon_end = ghost['mon_end']
                ph.tue_start = ghost['tue_start']
                ph.tue_end = ghost['tue_end']
                ph.wed_start = ghost['wed_start']
                ph.wed_end = ghost['wed_end']
                ph.thu_start = ghost['thu_start']
                ph.thu_end = ghost['thu_end']
                ph.fri_start = ghost['fri_start']
                ph.fri_end = ghost['fri_end']
                ph.sat_start = ghost['sat_start']
                ph.sat_end = ghost['sat_end']
                ph.save()
            elif handle == 'delete':
                ph = PlaceholderDriver.objects.get(id=params['ghost_id'])
                ph.delete()
            else:
                holders = PlaceholderDriver.objects.filter(organization_id=self.object.id)
                if holders.count() > 0:
                    output = holders.values(
                        'id',
                        'name',
                        'service_type',
                        'sun_start',
                        'sun_end',
                        'mon_start',
                        'mon_end',
                        'tue_start',
                        'tue_end',
                        'wed_start',
                        'wed_end',
                        'thu_start',
                        'thu_end',
                        'fri_start',
                        'fri_end',
                        'sat_start',
                        'sat_end',
                        'sun_available',
                        'mon_available',
                        'tue_available',
                        'wed_available',
                        'thu_available',
                        'fri_available',
                        'sat_available'
                    )
                else:
                    output = []
                return output
        elif action == 'drivers':
            # Gets the scheduled drivers
            # drivers = schedule.get_scheduled_drivers()
            print('getting drivers for', schedule.date)
            drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).order_by('start_date')
            print('drivers', drivers)
            # prev_output = TimeseriesScheduledDriversSerializer(prev_drivers, many=True).data
            output = TimeseriesScheduledDriversSerializer(drivers, many=True)
            output_schedule = {'id': schedule.id, 'date': schedule.date, 'publish': schedule.publish}
            return {'drivers': output.data, 'schedule_info': output_schedule}

        elif action == 'user_profile_day':
            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday = weekdays[date.weekday()]
            service_types = ['Tow', 'Battery', 'Light Service']
            ls_as = params['ls_as']
            has_ghost = params['withGhost']
            if ls_as == 'Tow':
                service_types = ['Tow', 'Tow, Light Service', 'Light Service, Tow', 'Battery', 'Light Service']
            elif ls_as == 'Battery':
                service_types = ['Tow', 'Battery', 'Battery, Light Service', 'Light Service, Battery', 'Light Service']

            try:
                schedule = TimeseriesSchedule.objects.get_or_create(organization_id=self.object.id, date=date)[0]
            except:
                schedules = TimeseriesSchedule.objects.filter(organization_id=self.object.id, date=date)
                schedule = schedules[0]

            del_drivers_shcedule = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()

            if self.object.type == 'Territory':
                org_set = self.object.children()
                employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
            else:
                employees = Employee.objects.filter(organization=self.object.employees_under).exclude(
                    active=0).values_list('id', flat=True)

            profiles = EmployeeProfile.objects.filter(employee_id__in=employees)
            if ls_as != 'All':
                profiles = profiles.filter(trouble_code_type__in=service_types)
            # else:
            #     profiles = profiles.exclude(trouble_code_type__isnull=True)

            profiles = profiles.exclude(
                Q(active=0) | Q(active_not_available=1)).values_list('id', flat=True)
            entries = EmployeeProfileEntries.objects.filter(driver_profile__in=list(profiles),
                                                            day_of_week=weekday).exclude(start_time=None)
            entries = entries.exclude(end_time=None)
            entries = entries.exclude(type='is not available')
            schedule_date = date
            schedule = TimeseriesSchedule.objects.get_or_create(date=schedule_date, organization_id=self.object.id)[0]
            scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
            if scheduled_drivers.count() > 0:
                scheduled_drivers.delete()

            def get_duration(start, end):
                # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
                d_start = (start.hour + (start.minute / 60))
                d_end = (end.hour + (end.minute / 60))
                if d_start >= d_end:
                    duration = ((d_end + 24) - d_start)
                else:
                    duration = (d_end - d_start)
                print('duration', duration)
                return duration

            def get_end_date(start, end, date):
                if start.hour >= end.hour:
                    scheduled_date = date + dt.timedelta(days=1)

                else:
                    scheduled_date = date
                scheduled_date = scheduled_date.replace(hour=end.hour, minute=end.minute)
                print(end.hour, end.minute, scheduled_date)
                return scheduled_date

            def get_service_type(tc):
                if ls_as == 'All':
                    return 'Tow'
                print('trouble code', tc)
                if ls_as != 'Light Service':
                    if tc in ls_as and ', ' in tc:
                        return ls_as
                    else:
                        return tc
                else:
                    print('trouble code', tc)
                    return tc

            all_new_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                [TimeseriesScheduledDrivers(
                    employee=e.driver_profile.employee,
                    start_date=schedule_date.replace(hour=e.start_time.hour, minute=e.start_time.minute),
                    end_date=get_end_date(e.start_time, e.end_time, schedule_date),
                    duration=get_duration(e.start_time, e.end_time),
                    schedule_id=schedule.id,
                    schedule_type=get_service_type(e.driver_profile.trouble_code_type)
                ) for e in entries]
            )
            print('drivers saved', all_new_drivers)

            ghost_days = {
                'Sunday': {'start': 'sun_start', 'end': 'sun_end', 'av': 'sun_available'},
                'Monday': {'start': 'mon_start', 'end': 'mon_end', 'av': 'mon_available'},
                'Tuesday': {'start': 'tue_start', 'end': 'tue_end', 'av': 'tue_available'},
                'Wednesday': {'start': 'wed_start', 'end': 'wed_end', 'av': 'wed_available'},
                'Thursday': {'start': 'thu_start', 'end': 'thu_end', 'av': 'thu_available'},
                'Friday': {'start': 'fri_start', 'end': 'fri_end', 'av': 'fri_available'},
                'Saturday': {'start': 'sat_start', 'end': 'sat_end', 'av': 'sat_available'},
            }

            def get_start_date(g):
                if weekday == 'Sunday': return g.sun_start
                if weekday == 'Monday': return g.mon_start
                if weekday == 'Tuesday': return g.tue_start
                if weekday == 'Wednesday': return g.wed_start
                if weekday == 'Thursday': return g.thu_start
                if weekday == 'Friday': return g.fri_start
                if weekday == 'Saturday': return g.sat_start

            def get_ghost_end_date(g):
                if weekday == 'Sunday': return g.sun_end
                if weekday == 'Monday': return g.mon_end
                if weekday == 'Tuesday': return g.tue_end
                if weekday == 'Wednesday': return g.wed_end
                if weekday == 'Thursday': return g.thu_end
                if weekday == 'Friday': return g.fri_end
                if weekday == 'Saturday': return g.sat_end

            if has_ghost is True:
                print('ghost is true')
                all_placeholders = PlaceholderDriver.objects.filter(organization_id=self.object.id)
                q = {ghost_days[weekday]['av']: 1}
                all_placeholders = all_placeholders.filter(**q)
                ghost_date = date
                print(all_placeholders)
                all_ghost_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                    [TimeseriesScheduledDrivers(
                        placeholder=g,
                        start_date=ghost_date.replace(hour=get_start_date(g).hour, minute=get_start_date(g).minute),
                        end_date=get_end_date(get_start_date(g), get_ghost_end_date(g), ghost_date),
                        duration=get_duration(get_start_date(g), get_ghost_end_date(g)),
                        schedule_id=schedule.id,
                        schedule_type=get_service_type(g.service_type)
                    ) for g in all_placeholders]
                )
                for g in all_ghost_drivers:
                    all_new_drivers.append(g)
            self.save_daily_schedule(date, all_new_drivers)
            output = TimeseriesScheduledDriversSerializer(all_new_drivers, many=True)
            print(output)
            action_display = '{0} schedule saved using profiler as template for {1}'.format(date.strftime('%m/%d/%Y'),
                                                                                            self.object.name)
            ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

            return output.data
        elif action == 'set_schedule':
            add_days = 0
            if date.weekday() == 6:
                add_days = 0
            else:
                add_days = date.weekday() + 1
            monday = date - dt.timedelta(days=add_days)
            sunday = monday + dt.timedelta(days=6)
            if self.object.type == 'Territory':
                org_set = self.object.children()
                employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
            else:
                employees = Employee.objects.filter(organization=self.object.employees_under).exclude(
                    active=0).values_list('id', flat=True)

            employees = EmployeeProfile.objects.filter(employee_id__in=employees.values_list('id', flat=True)).exclude(
                Q(active=0) | Q(active_not_available=1))
            employees_list = employees.values_list('employee_id', flat=True)
            # delete scheduled drivers
            SchedulerReviewByDriver.objects.filter(date__range=[monday, sunday],
                                                   employee_id__in=employees_list).delete()

            # get the schedule
            week_schedule = TimeseriesSchedule.objects.filter(organization_id=self.object.id,
                                                              date__range=[monday, sunday]).order_by('date')
            week_list = week_schedule.values_list('id', flat=True).distinct()
            output_schedule = TimeseriesScheduleSerializer(week_schedule, many=True).data
            all_scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(
                schedule__id__in=list(week_list))
            print('all schedule', all_scheduled_drivers.count())
            # distinct_drivers = all_scheduled_drivers.order_by('employee').distinct('employee')
            # output_drivers = TimeseriesScheduledDriversSerializer(all_scheduled_drivers, many=True).data
            output_drivers = all_scheduled_drivers.annotate(full_name=F('employee__full_name')).values('employee',
                                                                                                       'start_date',
                                                                                                       'duration',
                                                                                                       'schedule',
                                                                                                       'full_name',
                                                                                                       'schedule_type')
            # output_distinct = TimeseriesScheduledDrivers.objects.filter(schedule__id__in=list(week_list)) \
            #     .annotate(full_name=F('employee__full_name')) \
            #     .values('employee', 'full_name') \
            #     .order_by('full_name') \
            #     .distinct()
            #
            # for d in output_distinct:
            #     for i in range(int(7)):
            #         date_assign = monday + dt.timedelta(days=i)
            #         SchedulerReviewByDriver.objects.update_or_create(
            #             employee_id=d.employee,
            #             date=date_assign,
            #             off=True
            #         )

            scheduled_drivers_review = SchedulerReviewByDriver.objects.bulk_create(
                [SchedulerReviewByDriver(
                    employee=d.employee,
                    date=d.start_date.date(),
                    starting_time=d.start_date,
                    ending_time=d.start_date + dt.timedelta(hours=d.duration),
                    duration=d.duration,
                    tcd=d.schedule_type,
                    off=False
                ) for d in all_scheduled_drivers]
            )

            output = SchedulerReviewByDriverSerializer(scheduled_drivers_review, many=True).data

            return output
        elif action == 'new_expectations':
            add_days = 0
            if date.weekday() == 6:
                add_days = 0
            else:
                add_days = date.weekday() + 1
            sunday = date - dt.timedelta(days=add_days)
            today = dt.datetime.now()
            today = today - dt.timedelta(hours=today.hour, minutes=today.minute, seconds=today.second)
            expectations = []
            for i in range(int(7)):
                expect_day = TimeseriesExpectations.objects.get_or_create(organization_id=self.object.id,
                                                                          date=sunday + dt.timedelta(days=i))[0]
                expectations.append(expect_day)
            try:
                output = TimeseriesExpectationsSerializer(expectations, many=True).data
            except Exception as e:
                print(e)
            return output

        elif action == 'expectations':
            add_days = 0
            if date.weekday() == 6:
                add_days = 0
            else:
                add_days = date.weekday() + 1
            monday = date - dt.timedelta(days=add_days)
            today = dt.datetime.now()
            today = today - dt.timedelta(hours=today.hour, minutes=today.minute, seconds=today.second)
            exp_filter = params['filter']
            scheduler_type = params['scheduler_type']
            calc = []

            if self.object.type == 'Station-Business' or (
                    self.object.type == 'Territory' and self.object.facility_type == 'Fleet'):
                print('expectations it worked!!! ====')
                for i in range(int(7)):
                    feat_date = monday + dt.timedelta(days=i)
                    try:
                        schedule = TimeseriesSchedule.objects.get(organization_id=self.object.id, date=feat_date)
                        if scheduler_type == 'hourly':
                            hour_range = 24
                        else:
                            hour_range = 6
                        for j in range(hour_range):
                            if scheduler_type == 'hourly':
                                hour_steps = j
                            else:
                                hour_steps = j * 4
                            look_date = (feat_date - dt.timedelta(hours=feat_date.hour,
                                                                  minutes=feat_date.minute)) + dt.timedelta(
                                hours=hour_steps)
                            try:
                                drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule,
                                                                                    start_date__lte=look_date,
                                                                                    end_date__gt=look_date).count()
                                if scheduler_type == 'hourly':
                                    predictions = TimeseriesPredictionsByHourNew.objects.filter(
                                        organization_id=self.object.id,
                                        sc_dt=look_date)
                                elif scheduler_type == 'four_hour':
                                    predictions = TimeseriesPredictionsHourly.objects.filter(
                                        organization_id=self.object.id,
                                        sc_dt=look_date)
                                else:
                                    predictions = TimeseriesPredictionsByHourNew.objects.filter(
                                        organization_id=self.object.id,
                                        sc_dt=look_date)

                                if exp_filter != 'all':
                                    predictions = predictions.filter(code=exp_filter)

                                predictions = predictions.aggregate(volume_sum=Sum('volume_pred'))
                                try:
                                    calls = round(round(predictions['volume_sum']) / drivers)
                                except:
                                    calls = 'No Drivers Scheduled'
                                calc.append({
                                    'date': look_date,
                                    'calls': calls,
                                    'expected': round(predictions['volume_sum']),
                                    'drivers': drivers
                                })
                            except:
                                calc.append(
                                    {'date': look_date, 'calls': 'No Data Available', 'expected': 0, 'drivers': 0})
                    except:
                        continue
            else:
                children = self.object.children()

                def get_expectations(org):
                    # print('getting expectation for:', org.type)
                    if org.type == 'Station-Business':
                        print('inside station business')
                        schedules = TimeseriesSchedule.objects.filter(
                            date__range=[monday, monday + dt.timedelta(days=6)], organization_id=org.id) \
                            .prefetch_related('scheduled_drivers') \
                            .order_by('date')
                        for s in schedules:
                            all_drivers = s.scheduled_drivers.count()
                            if scheduler_type == 'hourly':
                                all_predictions = TimeseriesPredictionsByHourNew.objects.filter(sc_dt__contains=s.date,
                                                                                                organization_id=s.organization_id)
                                if all_predictions.count() > 0:
                                    all_predictions = all_predictions.aggregate(sum_volume=Sum('volume_pred'))
                            else:
                                all_predictions = TimeseriesPredictionsHourly.objects.filter(sc_dt__contains=s.date,
                                                                                             organization_id=s.organization_id)
                                if all_predictions.count() > 0:
                                    all_predictions = all_predictions.aggregate(sum_volume=Sum('volume_pred'))

                            try:
                                expected = round(all_predictions['sum_volume'] / all_drivers)
                            except:
                                expected = 0
                            calc.append(
                                {
                                    'date': s.date,
                                    'calls': expected,
                                    'expected': round(all_predictions['sum_volume']),
                                    'drivers': all_drivers,
                                    'org': '{0} ({1})'.format(org.name, org.parent_name),
                                    'slug': org.slug
                                })
                    elif org.type == 'Station':
                        pass
                    else:
                        for o in org.children():
                            if o.type in ['Station-Business', 'Territory', 'Market', 'Club-Region', 'Club']:
                                get_expectations(o)
                            else:
                                continue

                for c in children:
                    if c.type in ['Territory', 'Market', 'Club-Region', 'Club']:
                        get_expectations(c)
                    else:
                        continue
                return calc
            return calc
        elif action == 'compare_metrics':
            start_date = dt.datetime.strptime(params.get('start_date', date - dt.timedelta(days=15)), '%Y-%m-%d')
            end_date = dt.datetime.strptime(params.get('end_date', date), '%Y-%m-%d')
            employees = Employee.objects.filter(organization=self.object.employees_under).exclude(
                active=0).values_list('id', flat=True)
            osat = DashboardAggregations.objects.filter(organization_id=self.object.id, sc_dt__range=[dt.datetime.combine(start_date, dt.datetime.min.time()),
                                                                                                             dt.datetime.combine(end_date, dt.datetime.min.time())])
            historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=self.object.id, sc_dt__range=[start_date, end_date]).order_by('sc_dt')
            annot_d = {
                'total_volume': Sum('volume_pred'),
                'total_actual_volume': Sum('actual_volume'),
                'driver_target': Sum('total_drivers')
            }
            historical = historical.values('sc_dt').annotate(
                **annot_d).order_by()

            scheduled_drivers = SchedulerReviewByDriver.objects\
                .filter(employee__in=employees,
                       starting_time__range=[start_date, end_date],
                       ending_time__range=[start_date, end_date]).values()
                # .values('date')\
                # .annotate(scheduled_drivers=Count('date')).values('date', 'scheduled_drivers')
            metrics = {'osat': [], 'total_volume': [], 'total_actual_volume': [], 'driver_scheduled': [], 'driver_target': []}
            annot_vals = ['total_volume', 'total_actual_volume', 'driver_target']
            all_hours = []
            for i, event in enumerate(historical):
                try:
                    label = event['sc_dt'].strftime('%Y-%m-%dT%H:00:00Z')
                except AttributeError:
                    hour = event['sc_dt'][event['sc_dt'].find(' ')+1:]
                    if len(hour) == 1:
                        hour = '0' + hour
                    label = event['sc_dt'][0:event['sc_dt'].find(' ')] + 'T' + hour + ':00:00Z'
                if label not in all_hours:
                    all_hours.append(label)
                for a in annot_vals:
                    if a in metrics:
                        metrics[a].append({
                            'label': label,
                            'value': event[a],
                            'time_type': 'Day_of_Week'
                        })
                    else:
                        metrics[a] = [{
                            'label': label,
                            'value': event[a],
                            'time_type': 'Day_of_Week'
                        }]
            print('this is the osat', osat)
            for o in osat.values('sc_dt', 'aaa_mgmt_any_overall_sat_avg'):
                try:
                    label = o['date'].strftime('%Y-%m-%dT%H:00:00Z')
                except AttributeError:
                    hour = o['date'][o['date'].find(' ')+1:]
                    if len(hour) == 1:
                        hour = '0' + hour
                    label = o['date'][0:o['date'].find(' ')] + 'T' + hour + ':00:00Z'
                metrics['osat'].append({
                    'label': label,
                    'value': round(o['aaa_mgmt_any_overall_sat_avg'], 2) * 100,
                    'time_type': 'Day_of_Week'
                })
            for hour in all_hours:
                drivers_scheduled_count = 0
                d_hour = dt.datetime.strptime(hour, '%Y-%m-%dT%H:00:00Z')
                for d in scheduled_drivers:
                    if d['starting_time'].replace(tzinfo=None) <= d_hour and d['ending_time'].replace(tzinfo=None) >= d_hour:
                        drivers_scheduled_count = drivers_scheduled_count + 1
                metrics['driver_scheduled'].append({
                    'label': hour,
                    'value': drivers_scheduled_count,
                    'time_type': 'Day_of_Week'
                })
            # for d in scheduled_drivers:
            #     try:
            #         label = d['date'].strftime('%Y-%m-%dT%H:00:00Z')
            #     except AttributeError:
            #         hour = d['date'][d['date'].find(' ') + 1:]
            #         if len(hour) == 1:
            #             hour = '0' + hour
            #         label = d['date'][0:d['date'].find(' ')] + 'T' + hour + ':00:00Z'
            #     metrics['driver_scheduled'].append({
            #         'label': label,
            #         'value': d['scheduled_drivers'],
            #         'time_type': 'Day_of_Week'
            #     })
            final_out = []
            for tcd, d in metrics.items():
                final_out.append({
                    'groupName': tcd,
                    'data': d
                })
                # print(tcd, d)
                # for metric, out in d.items():
                #     final_out.append(metrics[tcd][metric])
            return final_out
        elif action == 'comparison':
            start_date = date - dt.timedelta(days=15)
            end_date = date + dt.timedelta(days=10)

            annot_d = {}
            metrics = {}
            for tcd in ['all', 'Tow', 'Battery', 'Other']:
                metrics[tcd] = {}
                for m in ['volume_pred', 'actual_volume', 'holiday_impacts', 'weather_impacts']:
                    annot_d[f'{m}_{tcd}'] = Sum(m) if tcd == 'all' else Sum(m, filter=Q(code=tcd.capitalize()))
                    metrics[tcd][m] = {'groupName': f"{tcd.capitalize()} {m.upper().replace('_', ' ')}", 'data': []}
                metrics[tcd]['diff'] = {'groupName': f'{tcd.capitalize()} Difference', 'data': []}
            print(metrics)

            view_by = params['view_by']

            historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=self.object.id,
                                                                           sc_dt__range=[start_date,
                                                                                         end_date]).order_by('sc_dt')

            class FourHourSplit(Func):
                template = """Floor(HOUR(%(expressions)s)/4)* 4"""

            view_by_grouping = {
                'day': TruncDate('sc_dt'),
                'four_hour': Concat(TruncDate('sc_dt') , V(' '), FourHourSplit('sc_dt'), output_field=CharField()),
                'hour': F('sc_dt')
            }
            print(view_by_grouping[view_by])
            historical = historical.annotate(date=view_by_grouping[view_by]).values('date').annotate(**annot_d).order_by()
            print(historical[0:3])
            print(annot_d)
            weather_holiday_baseline = round(historical.aggregate(Avg('volume_pred_all'))['volume_pred_all__avg'])

            final_out = []
            for i, event in enumerate(historical):
                try:
                    label = event['date'].strftime('%Y-%m-%dT%H:00:00Z')
                except AttributeError:
                    hour = event['date'][event['date'].find(' ')+1:]
                    if len(hour) == 1:
                        hour = '0' + hour
                    label = event['date'][0:event['date'].find(' ')] + 'T' + hour + ':00:00Z'
                    # label = event['date']
                for tcd, d in metrics.items():
                    for metric, out in d.items():
                        value = event.get(f'{metric}_{tcd}')
                        time_type = 'Day_and_Hour_of_Week' if view_by != 'day' else 'Day_of_Week'
                        if value is not None:
                            value = round(value) + weather_holiday_baseline if 'weather' in metric or 'holiday' in metric else round(value)
                        if metric != 'diff':
                            metrics[tcd][metric]['data'].append({
                                'label': label,
                                'value': value,
                                'time_type': time_type
                            })
                    # print(metrics[tcd]['volume_pred']['data'][i]['value'] - metrics[tcd]['actual_volume']['data'][i]['value'])
                    try:
                        diff = abs(metrics[tcd]['volume_pred']['data'][i]['value'] - metrics[tcd]['actual_volume']['data'][i]['value'])
                    except TypeError:
                        diff = None
                    metrics[tcd]['diff']['data'].append({
                        'label': label,
                        'value': diff
                    })

            for tcd, d in metrics.items():
                for metric, out in d.items():
                    final_out.append(metrics[tcd][metric])
            return final_out
        elif action == 'comparison_report':
            start_date = date - dt.timedelta(days=15)
            end_date = date + dt.timedelta(days=10)
            view_by = params['view_by']
            # if view_by == 'four_hour':
            #     historical = TimeseriesPredictionsByFourHourNew.objects.filter(organization_id=self.object.id,
            #                                                                    sc_dt__range=[start_date,
            #                                                                                  end_date]).order_by(
            #         'sc_dt')
            # else:
            #     historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=self.object.id,
            #                                                                sc_dt__range=[start_date,
            #                                                                              end_date]).order_by(
            #         'sc_dt')

            annot_d = {
                'total_volume': Sum('volume_pred'),
                'total_actual_volume': Sum('actual_volume'),
                'driver_target': Sum('total_drivers')
            }

            if params.get('fleetAvl', False):
                obj_id = params.get('fleetAvlId', object.id)

            historical = TimeseriesPredictionsByHourNew.objects.filter(organization_id=self.object.id,
                                                                       sc_dt__range=[start_date,
                                                                                     end_date]).order_by('sc_dt')

            class FourHourSplit(Func):
                template = """Floor(HOUR(%(expressions)s)/4)* 4"""

            view_by_grouping = {
                'day': TruncDate('sc_dt'),
                'four_hour': Concat(TruncDate('sc_dt'), V(' '), FourHourSplit('sc_dt'), output_field=CharField()),
                'hour': F('sc_dt')
            }
            historical = historical.annotate(date=view_by_grouping[view_by]).values('date').annotate(**annot_d).values(
                'date', 'code', 'total_volume', 'total_actual_volume', 'driver_target').order_by()

            def convert_date(d):
                if view_by == 'four_hour':
                    return d.split(' ')[0]
                if view_by == 'hour':
                    return d.date()
                if view_by == 'day':
                    return d

            def convert_time(tm):
                if view_by == 'hour':
                    return tm.time()
                if view_by == 'day':
                    return 'Day'
                time = int(tm.split(' ')[1])
                if time == 0:
                    return '12AM'
                if time == 12:
                    return '12PM'
                if time > 12:
                    return f'{time - 12}PM'
                else:
                    return f'{time}AM'

            overall_list = {}
            tow_list = []
            bat_list = []
            other_list = []
            for h in historical:
                h_date = convert_date(h['date'])
                h_time = convert_time(h['date'])
                h_data = {
                    'date': h_date,
                    'time': h_time,
                    'service_type': h['code'] if h['code'] != 'Other' else 'Light Service',
                    'prediction': round(h['total_volume']),
                    'actual': round(h['total_actual_volume']),
                    'predictions-actual': round(h['total_volume']) - round(h['total_actual_volume']),
                    'variance': abs(round(h['total_volume']) - round(h['total_actual_volume']))
                }
                if h['code'] == 'Tow':
                    print(h_data)
                    tow_list.append(h_data)
                elif h['code'] == 'Battery':
                    bat_list.append(h_data)
                else:
                    other_list.append(h_data)

                if h['date'] in overall_list:
                    overall_list[h['date']]['prediction'] = overall_list[h['date']]['prediction'] + round(
                        h['total_volume'])
                    overall_list[h['date']]['actual'] = overall_list[h['date']]['actual'] + round(
                        h['total_actual_volume'])
                    overall_list[h['date']]['predictions-actual'] = overall_list[h['date']]['prediction'] - \
                                                                    overall_list[h['date']]['actual']
                    overall_list[h['date']]['variance'] = abs(
                        overall_list[h['date']]['prediction'] - overall_list[h['date']]['actual'])
                else:
                    overall_list[h['date']] = {
                        'date': h_date,
                        'time': h_time,
                        'service_type': 'All',
                        'prediction': round(h['total_volume']),
                        'actual': round(h['total_actual_volume']),
                        'predictions-actual': round(h['total_volume']) - round(h['total_actual_volume']),
                        'variance': abs(round(h['total_volume']) - round(h['total_actual_volume']))
                    }
            overall_list = list(overall_list.values())
            output = [overall_list, tow_list, bat_list, other_list]
            return output
        elif action == 'summed_predictions':
            view_type = params['view_by']
            start_date = date
            end_date = date + dt.timedelta(days=9, hours=23, minutes=59)
            tc = params['trouble_code']
            metric = params['metric']  # volume_pred or total_drivers

            if self.object.type == 'Station-State':
                data_for = [child.id for child in self.object.children()]
                for p in self.object.parallel_parents.all():
                    p_org = Organization.objects.get(id=p)
                    for c in p_org.children():
                        if c not in data_for:
                            data_for.append(c.id)
                data_for = list(data_for)
                data_for.insert(0, self.object.id)
            elif self.object.type == 'Facility-Rep':
                pp_org = Organization.objects.filter(parallel_parents__in=[self.object.id])
                data_for = pp_org.values_list('id', flat=True)
                data_for = list(data_for)
                data_for.insert(0, self.object.id)
                # for o in pp_org:
                #     print('parrallel parent', o)
                #     [data_for.append(child.id) for child in o.children() if child.id not in data_for]
            else:
                data_for = self.object.id

            print('getting summed predictions for', data_for)

            try:
                predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id__in=data_for)
            except:
                predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id=data_for)

            # for territory level that is not fleet
            if self.object.type == 'Station-State' or self.object.type == 'Facility-Rep':
                output = {}
                if tc == 'all':
                    if metric == 'volume_pred':
                        total_pred = predictions.filter(sc_dt__range=[start_date, end_date]) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date') \
                            .annotate(total=Sum(metric)) \
                            .order_by('date')

                        predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'organization_id') \
                            .annotate(total_predictions=Sum(metric)) \
                            .order_by('organization_id')
                    else:
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'organization_id') \
                            .annotate(max_tow=Coalesce(Max(metric, filter=Q(code='Tow')), 0),
                                      max_bat=Coalesce(Max(metric, filter=Q(code='Battery')), 0),
                                      max_ls=Coalesce(Max(metric, filter=Q(code='Other')), 0)) \
                            .annotate(total_predictions=F('max_tow') + F('max_bat') + F('max_ls')) \
                            .order_by('organization_id')

                else:
                    print('list of code', tc)
                    if tc == 'tow_light_service':
                        code = ['Tow', 'Other']
                    elif tc == 'battery_light_service':
                        code = ['Battery', 'Other']
                    elif tc == 'Light Service':
                        code = ['Other']
                    else:
                        code = [tc]

                    if metric == 'volume_pred':
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'organization_id') \
                            .annotate(total_predictions=Sum(metric)) \
                            .order_by('organization_id')
                    else:
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'organization_id')
                        if tc == 'tow_light_service':
                            predictions = predictions \
                                .annotate(max_tow=Max(metric, filter=Q(code='Tow')),
                                          max_ls=Max(metric, filter=Q(code='Other'))) \
                                .annotate(total_predictions=F('max_tow') + F('max_ls')) \
                                .order_by('organization_id')

                        elif tc == 'battery_light_service':
                            predictions = predictions \
                                .annotate(max_bat=Max(metric, filter=Q(code='Battery')),
                                          max_ls=Max(metric, filter=Q(code='Other'))) \
                                .annotate(total_predictions=F('max_bat') + F('max_ls')) \
                                .order_by('organization_id')
                        elif tc == 'Light Service':
                            predictions = predictions \
                                .annotate(total_predictions=Max(metric, filter=Q(code='Other'))) \
                                .order_by('organization_id')
                        else:
                            predictions = predictions \
                                .annotate(total_predictions=Max(metric, filter=Q(code=tc))) \
                                .order_by('organization_id')
                        print(predictions)
                total_summed = {}
                for p in predictions:
                    if p['organization_id'] in output:
                        output[p['organization_id']]['data'].append(
                            {'value': p['total_predictions'], 'label': p['date']})
                        if str(p['date'].strftime('%Y-%m-%d')) in total_summed:
                            total_summed[str(p['date'].strftime('%Y-%m-%d'))]['value'] += p['total_predictions']
                        else:
                            total_summed[str(p['date'].strftime('%Y-%m-%d'))] = {'label': p['date'],
                                                                                 'value': p['total_predictions']}
                    else:
                        organization = Organization.objects.get(id=p['organization_id'])
                        output[p['organization_id']] = {
                            'rowLink': '/dashboard/{0}?section=scheduler'.format(organization.slug),
                            'data': [
                                {'label': 'Station-Business', 'value': organization.name},
                                {'label': p['date'], 'value': p['total_predictions']}
                            ]
                        }
                        if str(p['date'].strftime('%Y-%m-%d')) in total_summed:
                            total_summed[str(p['date'].strftime('%Y-%m-%d'))]['value'] += p['total_predictions']
                        else:
                            total_summed[str(p['date'].strftime('%Y-%m-%d'))] = {'label': p['date'],
                                                                                 'value': p['total_predictions']}
                # total_value = list([{'value': t['value'], 'label': t['label']} for t in total_summed])
                # total_value = list(total_summed.values())
                #
                # output['9999999'] = {
                #     'rowLink': '#',
                #     'data': [
                #         {'label': 'Station-Business', 'value': 'Total'},
                #         *total_value
                #     ]
                # }
                return list(output.values())

            else:
                output = {}
                if tc == 'all':
                    if metric == 'volume_pred':
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'sc_dt', 'organization_id') \
                            .annotate(total_predictions=Sum(metric)) \
                            .order_by('sc_dt')
                    else:
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date]) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'sc_dt', 'organization_id') \
                            .annotate(max_tow=Coalesce(Max(metric, filter=Q(code='Tow')), 0),
                                      max_bat=Coalesce(Max(metric, filter=Q(code='Battery')), 0),
                                      max_ls=Coalesce(Max(metric, filter=Q(code='Other')), 0)) \
                            .annotate(total_predictions=F('max_tow') + F('max_bat') + F('max_ls'))\
                            .order_by('sc_dt')
                            # .annotate(total_predictions=(((0, F('max_tow'))[isinstance(F('max_tow'), int)]) +
                            #                              ((0, F('max_bat'))[isinstance(F('max_bat'), int)])))\

                            # .annotate(total_predictions=(0 if F('max_tow') is None else F('max_tow')) +
                            #                             (0 if F('max_bat') is None else F('max_bat')) +
                            #                             (0 if F('max_ls') is None else F('max_ls'))) \

                else:
                    if tc == 'tow_light_service':
                        code = ['Tow', 'Other']
                    elif tc == 'battery_light_service':
                        code = ['Battery', 'Other']
                    elif tc == 'Light Service':
                        code = ['Other']
                    else:
                        code = [tc]

                    print('trouble code', tc)

                    if metric == 'volume_pred':
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'sc_dt', 'organization_id') \
                            .annotate(total_predictions=Sum(metric)) \
                            .order_by('sc_dt')
                    else:
                        predictions = predictions.filter(sc_dt__range=[start_date, end_date], code__in=code) \
                            .annotate(date=Cast('sc_dt', DateField())) \
                            .values('date', 'sc_dt', 'organization_id')

                        if tc == 'tow_light_service':
                            predictions = predictions \
                                .annotate(max_tow=Max(metric, filter=Q(code='Tow')),
                                          max_ls=Max(metric, filter=Q(code='Other'))) \
                                .annotate(total_predictions=F('max_tow') + F('max_ls')) \
                                .order_by('sc_dt')

                        elif tc == 'battery_light_service':
                            predictions = predictions \
                                .annotate(max_bat=Max(metric, filter=Q(code='Battery')),
                                          max_ls=Max(metric, filter=Q(code='Other'))) \
                                .annotate(total_predictions=F('max_bat') + F('max_ls')) \
                                .order_by('sc_dt')
                        elif tc == 'Light Service':
                            predictions = predictions \
                                .annotate(total_predictions=Max(metric, filter=Q(code='Other'))) \
                                .order_by('sc_dt')
                        else:
                            predictions = predictions \
                                .annotate(total_predictions=Max(metric, filter=Q(code=tc))) \
                                .order_by('sc_dt')
                print(predictions)
                for p in predictions:
                    if str(p['sc_dt'].strftime('%I%p')) in output:
                        if p['total_predictions'] is None:
                            total_pred = 0
                        elif p['total_predictions'] < 0:
                            total_pred = 0
                        else:
                            total_pred = p['total_predictions']
                        output[str(p['sc_dt'].strftime('%I%p'))]['data'].append({
                            'value': total_pred,
                            'label': p['date']
                        })
                    else:
                        output[str(p['sc_dt'].strftime('%I%p'))] = {
                            'rowLink': '#',
                            'data': [
                                {'label': 'Time', 'value': p['sc_dt'].strftime('%I%p')},
                                {'label': p['date'], 'value': p['total_predictions']}
                            ]
                        }
                return list(output.values())
        elif action == 'schedule_with_profiler':

            weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            if date.weekday() == 6:
                add_days = 0
            else:
                add_days = date.weekday() + 1
            sunday = date - dt.timedelta(days=add_days)
            saturday = sunday + dt.timedelta(days=6)
            service_types = ['Tow', 'Battery', 'Light Service']
            ls_as = params['ls_as']
            has_ghost = params['withGhost']
            if ls_as == 'Tow':
                service_types = ['Tow', 'Tow, Light Service', 'Light Service, Tow', 'Battery', 'Light Service']
            elif ls_as == 'Battery':
                service_types = ['Tow', 'Battery', 'Battery, Light Service', 'Light Service, Battery', 'Light Service']
            if self.object.type == 'Territory':
                org_set = self.object.children()
                employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
            else:
                employees = Employee.objects.filter(organization=self.object.employees_under).exclude(
                    active=0).values_list('id', flat=True)


            profiles = EmployeeProfile.objects.filter(employee_id__in=employees)

            if ls_as != 'All':
                profiles = profiles.filter(trouble_code_type__in=service_types)
            # else:
            #     profiles = profiles.exclude(trouble_code_type__isnull=True)

            profiles = profiles.exclude(Q(active=0) | Q(active_not_available=1)).values('id', 'employee_id')
            unique_profile = {}
            for p in profiles:
                if p['id'] not in unique_profile:
                    unique_profile[p['id']] = p['employee_id']

            profiles = unique_profile
            ghost_days = {
                'Sunday': {'start': 'sun_start', 'end': 'sun_end', 'av': 'sun_available'},
                'Monday': {'start': 'mon_start', 'end': 'mon_end', 'av': 'mon_available'},
                'Tuesday': {'start': 'tue_start', 'end': 'tue_end', 'av': 'tue_available'},
                'Wednesday': {'start': 'wed_start', 'end': 'wed_end', 'av': 'wed_available'},
                'Thursday': {'start': 'thu_start', 'end': 'thu_end', 'av': 'thu_available'},
                'Friday': {'start': 'fri_start', 'end': 'fri_end', 'av': 'fri_available'},
                'Saturday': {'start': 'sat_start', 'end': 'sat_end', 'av': 'sat_available'},
            }
            for i in range(len(weekdays)):
                print('day', weekdays[i])
                entries = EmployeeProfileEntries.objects.filter(driver_profile__in=list(profiles),
                                                                day_of_week=weekdays[i]).exclude(start_time=None)
                schedule_date = sunday + dt.timedelta(days=i)
                pto_entries = EmployeeProfileEntries.objects.filter(pto_end__gte=schedule_date,
                                                                    pto_start__lte=schedule_date,
                                                                    driver_profile__in=list(profiles)).values_list(
                    'driver_profile__employee_id', flat=True)
                entries = entries.exclude(end_time=None)
                entries = entries.exclude(type='is not available')

                schedule = TimeseriesSchedule.objects.get_or_create(date=schedule_date, organization_id=self.object.id)[
                    0]
                scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
                print('drivers to delete', scheduled_drivers.count())
                scheduled_drivers.delete()

                def get_duration(start, end):
                    # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
                    d_start = (start.hour + (start.minute / 60))
                    d_end = (end.hour + (end.minute / 60))
                    if d_start > d_end:
                        duration = ((d_end + 24) - d_start)
                    else:
                        duration = (d_end - d_start)
                    return duration

                def get_end_date(start, end, date):
                    if start.hour >= end.hour:
                        schedule_date = date + dt.timedelta(days=1)
                    else:
                        schedule_date = date
                    schedule_date = schedule_date.replace(hour=end.hour, minute=end.minute)
                    print(end.hour, end.minute, schedule_date)
                    return schedule_date

                def get_service_type(tc):
                    if ls_as == 'All':
                        return 'Tow'
                    if ls_as != 'Light Service':
                        if tc in ls_as and ', ' in tc:
                            return ls_as
                        else:
                            return tc
                    else:
                        return tc

                all_new_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                    [TimeseriesScheduledDrivers(
                        employee=e.driver_profile.employee,
                        start_date=schedule_date.replace(hour=e.start_time.hour, minute=e.start_time.minute),
                        end_date=get_end_date(e.start_time, e.end_time, schedule_date),
                        duration=get_duration(e.start_time, e.end_time),
                        schedule_id=schedule.id,
                        schedule_type=get_service_type(e.driver_profile.trouble_code_type)
                    ) for e in entries if e.driver_profile.employee.id not in pto_entries]
                )

                # def available_ghost(g):
                #     return g[ghost_days[weekdays[i]]['av']]
                def get_start_date(g):
                    if weekdays[i] == 'Sunday': return g.sun_start
                    if weekdays[i] == 'Monday': return g.mon_start
                    if weekdays[i] == 'Tuesday': return g.tue_start
                    if weekdays[i] == 'Wednesday': return g.wed_start
                    if weekdays[i] == 'Thursday': return g.thu_start
                    if weekdays[i] == 'Friday': return g.fri_start
                    if weekdays[i] == 'Saturday': return g.sat_start

                def get_ghost_end_date(g):
                    if weekdays[i] == 'Sunday': return g.sun_end
                    if weekdays[i] == 'Monday': return g.mon_end
                    if weekdays[i] == 'Tuesday': return g.tue_end
                    if weekdays[i] == 'Wednesday': return g.wed_end
                    if weekdays[i] == 'Thursday': return g.thu_end
                    if weekdays[i] == 'Friday': return g.fri_end
                    if weekdays[i] == 'Saturday': return g.sat_end

                if has_ghost == True:
                    print('ghost is true')
                    all_placeholders = PlaceholderDriver.objects.filter(organization_id=self.object.id)
                    q = {ghost_days[weekdays[i]]['av']: 1}
                    all_placeholders = all_placeholders.filter(**q)
                    print(all_placeholders)
                    ghost_date = date
                    all_ghost_drivers = TimeseriesScheduledDrivers.objects.bulk_create(
                        [TimeseriesScheduledDrivers(
                            placeholder=g,
                            start_date=ghost_date.replace(hour=get_start_date(g).hour,
                                                             minute=get_start_date(g).minute),
                            end_date=get_end_date(get_start_date(g), get_ghost_end_date(g), ghost_date),
                            duration=get_duration(get_start_date(g), get_ghost_end_date(g)),
                            schedule_id=schedule.id,
                            schedule_type=get_service_type(g.service_type)
                        ) for g in all_placeholders]
                    )
                    for g in all_ghost_drivers:
                        all_new_drivers.append(g)

                print('drivers saved', len(all_new_drivers))
                print(date)

                action_display = 'Created schedule using Driver Profiler for the week of {0} for {1}'.format(
                    sunday.strftime('%m/%d/%Y'), self.object.name)
                ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

                self.save_daily_schedule(schedule_date, all_new_drivers)
        elif action == 'get_overnight_drivers':
            prev_day = date - dt.timedelta(days=1)
            print(prev_day)
            # try:
            prev_day_schedule = TimeseriesSchedule.objects.get(date=prev_day, organization_id=self.object.id)
            print(prev_day_schedule)
            date_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            def get_duration(end):
                duration = end.hour + (end.minute / 60)
                return duration

            overnight_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=prev_day_schedule, end_date__gte=date_time)\
                .exclude(end_date=date_time) \
                .annotate(text=F('employee__full_name'))\
                .values('id', 'end_date', 'schedule', 'schedule_type', 'placeholder', 'text')
            [o.update({'start_date': date_time, 'duration': get_duration(o['end_date']), 'overnight': True}) for o in overnight_drivers]
            return {'overnight_drivers': overnight_drivers}
            # except:
            #     return {'overnight_drivers': []}
        elif action == 'get_templates':
            template_id = params['template_id']
            if template_id:
                templates = TimeseriesScheduleTemplate.objects.filter(organization_id=self.object.id)
                template = TimeseriesScheduleTemplate.objects.get(id=template_id)
            else:
                templates = TimeseriesScheduleTemplate.objects.filter(organization_id=self.object.id)
                if templates.count() > 1:
                    template = templates[0]
                elif templates.count() == 0:
                    template = TimeseriesScheduleTemplate.objects.create(organization_id=self.object.id, name='Default')
                else:
                    template = templates[0]
                    templates = templates.exclude(id=template.id)

            output = {
                'current_template': TimeseriesScheduleTemplateSerializer(template).data,
                'all_templates': templates.values('id', 'template_name')
            }
            return output
        elif action == 'delete_template':
            template = TimeseriesScheduleTemplate.objects.get(id=params['template_id']).delete()
            all_templates = TimeseriesScheduleTemplate.objects.filter(organization_id=self.object.id)
            if all_templates.count() > 0:
                template = TimeseriesScheduleTemplateSerializer(all_templates[0]).data
            else:
                template = None

            return {'all_templates': all_templates.values('id', 'template_name'), 'template': template}
        elif action == 'generate_from_template':
            process = params['process']
            if process == 'save_template':
                weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                [sunday, saturday] = self.get_sun_sat(date)
                employees_list = self.get_employee_list()
                is_create = params['create']
                week_schedule = SchedulerReviewByDriver.objects.filter(employee_id__in=employees_list,
                                                                       date__range=[sunday.date(), saturday.date()]) \
                    .exclude(off=True)
                if is_create:
                    schedule_temp = TimeseriesScheduleTemplate.objects.create(
                        organization_id=self.object.id,
                        template_name=params['template_name']
                    )
                else:
                    schedule_temp = TimeseriesScheduleTemplate.objects.get(id=params['temp_id'])
                # schedule_temp = TimeseriesScheduleTemplate.objects.get_or_create(organization_id=self.object.id)[0]
                old_drivers_temp = TimeseriesScheduledDiversTemplate.objects.filter(template=schedule_temp).delete()
                new_drivers_temp = TimeseriesScheduledDiversTemplate.objects.bulk_create(
                    [TimeseriesScheduledDiversTemplate(
                        template=schedule_temp,
                        day_of_week=weekdays[d.date.weekday()],
                        start_time=d.starting_time,
                        end_time=d.ending_time,
                        duration=d.duration,
                        schedule_type=d.tcd,
                        employee=Employee.objects.get(id=d.employee_id),
                    ) for d in week_schedule]
                )
                serializers_temp = TimeseriesScheduleTemplateSerializer(schedule_temp)

                action_display = 'Saved schedule of {0} as a default schedule for {1}'.format(
                    sunday.strftime('%m/%d/%Y'), self.object.name)
                ActionsLogger(self.request.user, 'TimeseriesScheduledDriversTemplate', action_display, 'Scheduler',
                              action_url)

                all_temps = TimeseriesScheduleTemplate.objects.filter(organization_id=self.object.id).values('id', 'template_name')
                return {'template': serializers_temp.data, 'all_templates': all_temps}
            else:
                [sunday, saturday] = self.get_sun_sat(date)
                # sunday = sunday.replace(hour=0, minute=0)
                weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                temp_id = params['template_id']
                template = TimeseriesScheduleTemplate.objects.get(id=temp_id)
                if self.object.type == 'Territory':
                    org_set = self.object.children()
                    employees = Employee.objects.filter(organization__in=org_set).exclude(active=0)
                else:
                    employees = Employee.objects.filter(organization=self.object.employees_under).exclude(
                        active=0).values_list('id', flat=True)

                profiles = EmployeeProfile.objects.filter(employee_id__in=employees).exclude(
                    Q(active=0) | Q(active_not_available=1)).values('id', 'employee_id')

                def get_duration(start, end):
                    # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
                    d_start = (start.hour + (start.minute / 60))
                    d_end = (end.hour + (end.minute / 60))
                    if d_start > d_end:
                        duration = ((d_end + 24) - d_start)
                    else:
                        duration = (d_end - d_start)
                    return duration

                def get_end_date(start, end, date):
                    if start.hour >= end.hour:
                        schedule_date = date + dt.timedelta(days=1)
                    else:
                        schedule_date = date
                    schedule_date = schedule_date.replace(hour=end.hour, minute=end.minute)
                    print(end.hour, end.minute, schedule_date)
                    return schedule_date

                unique_profile = {}
                for p in profiles:
                    if p['id'] not in unique_profile:
                        unique_profile[p['id']] = p['employee_id']

                profiles = unique_profile
                for i in range(len(weekdays)):
                    new_date = sunday + dt.timedelta(days=i)
                    temp_drivers = TimeseriesScheduledDiversTemplate.objects.filter(template=template,
                                                                                    day_of_week=weekdays[i]) \
                        .values('employee',
                                'start_time',
                                'end_time',
                                'duration',
                                'schedule_type')
                    schedule = TimeseriesSchedule.objects.get_or_create(organization_id=self.object.id, date=new_date)[
                        0]
                    pto_entries = EmployeeProfileEntries.objects.filter(pto_end__gte=new_date,
                                                                        pto_start__lte=new_date,
                                                                        driver_profile__in=list(profiles)).values_list(
                        'driver_profile__employee_id', flat=True)
                    prev_schedule_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule).delete()
                    scheduled_drivers = TimeseriesScheduledDrivers.objects.bulk_create([
                        TimeseriesScheduledDrivers(
                            schedule=schedule,
                            employee=Employee.objects.get(id=t['employee']),
                            start_date=new_date + dt.timedelta(hours=t['start_time'].hour,
                                                               minutes=t['start_time'].minute),
                            end_date=get_end_date(t['start_time'], t['end_time'], new_date),
                            duration=get_duration(t['start_time'], t['end_time']),
                            schedule_type=t['schedule_type']
                        ) for t in temp_drivers if t['employee'] not in pto_entries
                    ])
                    self.save_daily_schedule(new_date, scheduled_drivers)

                employees_list = self.get_employee_list()
                week_schedule = SchedulerReviewByDriver.objects.filter(date__range=[sunday.date(), saturday.date()],
                                                                       employee_id__in=employees_list)
                output = []
                output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
                    total_hours=Sum('duration'),
                    full_name=F('employee__full_name'))
                                       .values('date', 'starting_time',
                                               'ending_time', 'duration',
                                               'tcd', 'full_name', 'total_hours').order_by('full_name'))
                from itertools import groupby
                dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
                for k, v in groupby(output_schedule, key=lambda x: x['full_name']):
                    sorted_schedule = list(v)
                    for s in sorted_schedule:
                        try:
                            s.update(
                                {'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
                                    '%H:%M')
                                            + '-\n' + s['ending_time'].strftime('%H:%M')
                                            + '\n(' + s['tcd'] + ')'})
                        except:
                            s.update(
                                {'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
                                    '%H:%M')
                                            + '-\n' + s['ending_time'].strftime('%H:%M')})

                    missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off', 'duration': 0}
                                     for d in dates if d not in
                                     [d['date'] for d in sorted_schedule]]

                    sorted_schedule = sorted_schedule + missing_dates
                    sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

                    output.append({'schedule': sorted_schedule[0],
                                   'total_hours': sum([x['duration'] for x in sorted_schedule[0]])})
                try:
                    template_schedule = TimeseriesScheduleTemplate.objects.get(organization_id=self.object.id)
                    output_template = TimeseriesScheduleTemplateSerializer(template_schedule).data
                except:
                    output_template = None

                action_display = 'Used default schedule to create the schedule for the week of {0} for {1}'.format(
                    sunday.strftime('%m/%d/%Y'), self.object.name)
                ActionsLogger(self.request.user, 'TimeseriesScheduledDrivers', action_display, 'Scheduler', action_url)

                return {'schedule': output, 'template_schedule': output_template, 'schedule_dates': dates}
        elif action == 'weekly_schedule_split':
            [sunday, saturday] = self.get_sun_sat(date)
            employees_list = self.get_employee_list()
            ghost_drivers = PlaceholderDriver.objects.filter(organization_id=self.object.id).values_list('id',
                                                                                                         flat=True)
            week_schedule = SchedulerReviewByDriver.objects.filter(Q(date__range=[sunday.date(), saturday.date()]),
                                                                   Q(employee_id__in=employees_list) | Q(
                                                                       placeholder_id__in=ghost_drivers))
            output = []
            output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
                total_hours=Sum('duration'),
                alt_name=F('placeholder__name'),
                full_name=F('employee__full_name'))
                                   .values('date', 'starting_time',
                                           'ending_time', 'duration',
                                           'tcd', 'full_name', 'total_hours', 'alt_name').order_by('full_name',
                                                                                                   'alt_name'))
            from itertools import groupby
            dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
            week_split = {}
            for i in range(len(dates)):
                day_schedule = SchedulerReviewByDriver.objects.filter(Q(date=dates[i]),
                                                                      Q(employee_id__in=employees_list) | Q(placeholder_id__in=ghost_drivers))

                overnight_start_time = dt.datetime.combine(dates[i], dt.datetime.min.time())
                overnight = SchedulerReviewByDriver.objects.filter(Q(date=dates[i] - dt.timedelta(days=1)) & Q(ending_time__gt=overnight_start_time),
                                                                   Q(employee_id__in=employees_list) | Q(placeholder_id__in=ghost_drivers))
                overnight_schedule = list(overnight.values('employee_id', 'date').annotate(
                    total_hours=Sum('duration'),
                    alt_name=F('placeholder__name'),
                    full_name=F('employee__full_name'))
                                    .values('date', 'starting_time',
                                            'ending_time', 'duration',
                                            'tcd', 'full_name', 'total_hours', 'alt_name').order_by('-ending_time',
                                                                                                    'tcd', 'full_name',
                                                                                                    'alt_name'))
                day_schedule = list(day_schedule.values('employee_id', 'date').annotate(
                total_hours=Sum('duration'),
                alt_name=F('placeholder__name'),
                full_name=F('employee__full_name'))
                                   .values('date', 'starting_time',
                                           'ending_time', 'duration',
                                           'tcd', 'full_name', 'total_hours', 'alt_name').order_by('starting_time', 'tcd','full_name',
                                                                                                   'alt_name'))
                print('overnight scheduler', overnight_schedule)
                if overnight_schedule:
                    [day_schedule.insert(0, x) for x in overnight_schedule]
                    # day_schedule = overnight_schedule.extend(day_schedule)

                week_split[dates[i].strftime('%Y-%m-%d')] = day_schedule
            for k, v in groupby(output_schedule,
                                key=lambda x: x['full_name'] if (x['full_name'] is not None) else x['alt_name']):
                sorted_schedule = list(v)
                for s in sorted_schedule:
                    try:
                        s.update({'display': s['starting_time'].strftime('%H:%M')
                                             + '-' + s['ending_time'].strftime('%H:%M')
                                             + ' (' + s['tcd'] + ')'})
                    except:
                        s.update({'display': s['starting_time'].strftime('%H:%M')
                                             + '-' + s['ending_time'].strftime('%H:%M')})

                missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off', 'duration': 0}
                                 for d in dates if d not in
                                 [d['date'] for d in sorted_schedule]]

                sorted_schedule = sorted_schedule + missing_dates
                sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

                output.append({'schedule': sorted_schedule[0],
                               'total_hours': sum([x['duration'] for x in sorted_schedule[0]])})

            return {'full_schedule': output, 'split_schedule': week_split}
        elif action == 'full_report':
            [sunday, saturday] = self.get_sun_sat(date)
            print("monday", sunday, 'sunday', saturday)
            employees_list = self.get_employee_list()
            ghost_drivers = PlaceholderDriver.objects.filter(organization_id=self.object.id).values_list('id',
                                                                                                         flat=True)
            week_schedule = SchedulerReviewByDriver.objects.filter(Q(date__range=[sunday.date(), saturday.date()]),
                                                                   Q(organization_id=self.object.id),
                                                                   Q(employee_id__in=employees_list) | Q(
                                                                       placeholder_id__in=ghost_drivers))
            ls_as = params['ls_as']
            output = []
            output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
                total_hours=Sum('duration'),
                alt_name=F('placeholder__name'),
                driver_number=F('employee__raw_data_driver_id'),
                full_name=F('employee__full_name'))
                                   .values('date', 'starting_time',
                                           'ending_time', 'duration',
                                           'tcd', 'full_name', 'total_hours', 'alt_name').order_by('full_name',
                                                                                                   'alt_name'))
            from itertools import groupby
            dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
            for k, v in groupby(output_schedule,
                                key=lambda x: x['full_name'] if (x['full_name'] is not None) else x['alt_name']):
                sorted_schedule = list(v)
                for s in sorted_schedule:
                    try:
                        s.update({'display': s['starting_time'].strftime('%H:%M')
                                             + '-' + s['ending_time'].strftime('%H:%M')
                                             + '(' + s['tcd'] + ')'})
                    except:
                        s.update({'display': s['starting_time'].strftime('%H:%M')
                                             + '-' + s['ending_time'].strftime('%H:%M')})

                missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off', 'duration': 0}
                                 for d in dates if d not in
                                 [d['date'] for d in sorted_schedule]]

                sorted_schedule = sorted_schedule + missing_dates
                sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

                output.append({'schedule': sorted_schedule[0],
                               'total_hours': sum([x['duration'] for x in sorted_schedule[0]])})
            if params['scheduler_type']:
                if params['scheduler_type'] == 'hourly':
                    predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id=self.object.id)
                else:
                    predictions = TimeseriesPredictionsHourly.objects.filter(organization_id=self.object.id)
            else:
                predictions = TimeseriesPredictionsByHourNew.objects.filter(organization_id=self.object.id)
            saturday = saturday + dt.timedelta(hours=23)
            predictions = predictions.filter(sc_dt__range=[sunday.date(), saturday])
            if ls_as == 'All':
                tow_prediction = predictions\
                    .values('sc_dt')\
                    .annotate(total_vol=Sum('volume_pred'),
                              total_actual=Sum('actual_volume'),
                              all_drivers_15=Sum('total_drivers_wait_15'),
                              all_drivers=Sum('total_drivers'))\
                    .values('sc_dt', 'total_vol', 'total_actual', 'all_drivers_15', 'all_drivers').order_by('sc_dt')
                bat_prediction = []
                ls_prediction = []
            else:
                if ls_as == 'Tow':
                    tow_prediction = predictions.exclude(code='Battery')\
                        .values('sc_dt')\
                        .annotate(total_vol=Sum('volume_pred'),
                                  total_actual=Sum('actual_volume'),
                                  all_drivers_15=Sum('total_drivers_wait_15'),
                                  all_drivers=Sum('total_drivers'))\
                        .values('sc_dt', 'total_vol', 'total_actual', 'all_drivers', 'all_drivers_15').order_by('sc_dt')
                else:
                    tow_prediction = predictions.filter(code='Tow')\
                        .values('sc_dt', 'code', 'volume_pred', 'actual_volume', 'total_drivers', 'total_drivers_wait_15').order_by('sc_dt')
                if ls_as == 'Battery':
                    bat_prediction = predictions.exclude(code='Tow') \
                        .values('sc_dt') \
                        .annotate(total_vol=Sum('volume_pred'),
                                  total_actual=Sum('actual_volume'),
                                  all_drivers_15=Sum('total_drivers_wait_15'),
                                  all_drivers=Sum('total_drivers')) \
                        .values('sc_dt', 'total_vol', 'total_actual', 'all_drivers', 'all_drivers_15').order_by('sc_dt')
                else:
                    bat_prediction = predictions.filter(code='Battery')\
                        .values('sc_dt', 'code', 'volume_pred', 'actual_volume', 'total_drivers', 'total_drivers_wait_15')
                if ls_as == 'Light Service':
                    ls_prediction = predictions.filter(code='Other')\
                        .values('sc_dt', 'code', 'volume_pred', 'actual_volume', 'total_drivers', 'total_drivers_wait_15').order_by('sc_dt')
                else:
                    ls_prediction = []

            tow_drivers = []
            bat_drivers = []
            ls_drivers = []
            date_times = []
            for p in predictions:
                if p.sc_dt not in list(date_times):
                    date_times.append(p.sc_dt)
                    sched = week_schedule.filter(Q(starting_time__lte=p.sc_dt) & Q(ending_time__gt=p.sc_dt))
                    if ls_as == 'All':
                        tow_count_d = sched.count()
                        tow_drivers.append({'sc_dt': p.sc_dt, 'driver_count': tow_count_d})
                    else:
                        if ls_as == 'Tow':
                            tow_count_d = sched.exclude(tcd='Battery').count()
                        else:
                            tow_count_d = sched.filter(tcd='Tow').count()
                        if ls_as == 'Battery':
                            bat_count_d = sched.exclude(tcd='Tow').count()
                        else:
                            bat_count_d = sched.filter(tcd='Battery').count()
                        if ls_as == 'Light Service':
                            ls_count_d = sched.filter(tcd='Light Service').count()
                        else:
                            ls_count_d = 0
                        tow_drivers.append({'sc_dt': p.sc_dt, 'driver_count': tow_count_d})
                        bat_drivers.append({'sc_dt': p.sc_dt, 'driver_count': bat_count_d})
                        ls_drivers.append({'sc_dt': p.sc_dt, 'driver_count': ls_count_d})

            return {
                'full_schedule': output,
                'tow_pred': tow_prediction,
                'bat_pred': bat_prediction,
                'ls_pred': ls_prediction,
                'tow_driver_count': tow_drivers,
                'bat_driver_count': bat_drivers,
                'ls_driver_count': ls_drivers
            }

        else:
            [sunday, saturday] = self.get_sun_sat(date)
            print("monday", sunday, 'sunday', saturday)
            employees_list = self.get_employee_list()
            ghost_drivers = PlaceholderDriver.objects.filter(organization_id=self.object.id).values_list('id',
                                                                                                         flat=True)
            week_schedule = SchedulerReviewByDriver.objects.filter(Q(date__range=[sunday.date(), saturday.date()]),
                                                                   Q(employee_id__in=employees_list) | Q(
                                                                       placeholder_id__in=ghost_drivers))
            unpublished = TimeseriesSchedule.objects.filter(organization_id=self.object.id, date__range=[sunday.date(), saturday.date()], publish=False)
            output_unpub = unpublished.values('id', 'date', 'publish')
            output = []
            output_schedule = list(week_schedule.values('employee_id', 'date').annotate(
                total_hours=Sum('duration'),
                alt_name=F('placeholder__name'),
                full_name=F('employee__full_name'))
                                   .values('date', 'starting_time',
                                           'ending_time', 'duration',
                                           'tcd', 'full_name', 'total_hours', 'alt_name').order_by('full_name',
                                                                                                   'alt_name'))
            from itertools import groupby
            dates = [(sunday + dt.timedelta(days=i)).date() for i in range(int(7))]
            for k, v in groupby(output_schedule,
                                key=lambda x: x['full_name'] if (x['full_name'] is not None) else x['alt_name']):
                sorted_schedule = list(v)
                for s in sorted_schedule:
                    try:
                        s.update({'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
                            '%H:%M')
                                             + ' -\n' + s['ending_time'].strftime('%H:%M')
                                             + '\n(' + s['tcd'] + ')'})
                    except:
                        s.update({'display': '@@%s@@' % s['starting_time'].strftime('%H') + s['starting_time'].strftime(
                            '%H:%M')
                                             + ' -\n' + s['ending_time'].strftime('%H:%M')})

                missing_dates = [{'date': d, 'total_hours': 0, 'full_name': k, 'display': 'Off', 'duration': 0}
                                 for d in dates if d not in
                                 [d['date'] for d in sorted_schedule]]

                sorted_schedule = sorted_schedule + missing_dates
                sorted_schedule = sorted(sorted_schedule, key=lambda x: x['date']),

                output.append({'schedule': sorted_schedule[0],
                               'total_hours': sum([x['duration'] for x in sorted_schedule[0]])})
            try:
                template_schedule = TimeseriesScheduleTemplate.objects.filter(organization_id=self.object.id)[0]
                output_template = TimeseriesScheduleTemplateSerializer(template_schedule).data
            except:
                output_template = None

            template_list = TimeseriesScheduleTemplate.objects.filter(organization_id=self.object.id).values('id', 'template_name')
            return {'schedule': output, 'schedule_dates': dates, 'unpublished': output_unpub, 'template_schedule': output_template, 'all_templates': template_list}

        return {'message': 'No data available'}

    ## scheduler single functions
    def get_sun_sat(self, date):
        if date.weekday() == 6:
            add_days = 0
        else:
            add_days = date.weekday() + 1
        sunday = date - dt.timedelta(days=add_days)
        saturday = sunday + dt.timedelta(days=6)
        return [sunday, saturday]

    def get_employee_list(self):
        if self.object.type == 'Territory':
            org_set = self.object.children()
            employees = list(Employee.objects.filter(organization__in=org_set).exclude(active=0).values_list('id', flat=True))
        else:
            employees = list(Employee.objects.filter(organization=self.object.employees_under).exclude(
                active=0).values_list('id', flat=True))
        parallel_employees = Employee.objects.filter(parallel_organizations__in=[self.object.id]).exclude(active=0, id__in=employees).values_list('id', flat=True)
        [employees.append(x) for x in parallel_employees]
        employees = EmployeeProfile.objects.filter(employee_id__in=employees).exclude(
            active=0)
        employees_list = employees.values_list('employee_id', flat=True)
        return employees_list

    def save_daily_schedule(self, date, drivers):
        print(drivers)
        employees_list = self.get_employee_list()
        ghost_list = PlaceholderDriver.objects.filter(organization_id=self.object.id).values_list('id', flat=True)
        print(date)
        SchedulerReviewByDriver.objects.filter(
            Q(date=date) & (Q(employee_id__in=employees_list) | Q(placeholder_id__in=ghost_list))).delete()

        def get_duration(start, end):
            # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
            d_start = (start.hour + (start.minute / 60))
            d_end = (end.hour + (end.minute / 60))
            if d_start > d_end:
                duration = ((d_end + 24) - d_start)
            else:
                duration = (d_end - d_start)
            return duration

        scheduled_drivers_review = SchedulerReviewByDriver.objects.bulk_create(
            [SchedulerReviewByDriver(
                employee=d.employee,
                date=d.start_date.date(),
                starting_time=d.start_date,
                ending_time=d.end_date,
                duration=get_duration(d.start_date, d.end_date),
                tcd=d.schedule_type,
                off=False,
                placeholder=d.placeholder
            ) for d in drivers]
        )
        print('saved Daily Schedule', scheduled_drivers_review)

    def save_weekly_schedule(self, date, drivers):
        [sunday, saturday] = self.get_sun_sat(date)
        employees_list = self.get_employee_list()
        # delete scheduled drivers
        SchedulerReviewByDriver.objects.filter(date__range=[sunday, saturday], employee_id__in=employees_list).delete()

        scheduled_drivers_review = SchedulerReviewByDriver.objects.bulk_create(
            [SchedulerReviewByDriver(
                employee=d.employee,
                date=d.start_date.date(),
                starting_time=d.start_date,
                ending_time=d.end_date,
                duration=d.duration,
                tcd=d.schedule_type,
                off=False,
                placeholder=d.placeholder
            ) for d in drivers]
        )
        print('all drivers saved for the week')

    def testing(self):
        from django.db.models.functions import Extract
        grouping_field = Extract('date', time_type)
        UserActions.objects.annotate(time_group=grouping_field).values('time_group', 'user_id', 'type')\
            .aggregate(count(url))



    def get_xlsx_schedule_template(self, params):
        params = self.clean_parameters(params,
                                       ['action', 'date', 'drivers', 'filter', 'view_by', 'process', 'scheduler_type', 'is_week'])
        action = params['action']
        date = dt.datetime.strptime(params['date'], '%Y-%m-%d')
        action_url = '/dashboard/{0}?section=scheduler'.format(self.object.slug)
        is_week = params['is_week']
        employees = Employee.objects.filter(id__in=self.get_employee_list()).order_by('full_name')
        return employees.values('id', 'full_name')

    def upload_xlsx_schedule(self, params):
        print(params.data['file'])
        file = params.data['file']
        if file:
            filename = params.data['filename']
            save_path = 'schedule_temp/' + filename
            default_storage.save(save_path, file)
            return {'success': True, 'message': 'File uploaded successfully'}
        else:
            return {'success': False, 'message': 'No file found'}

    def save_upload_schedule(self, params):
        date = dt.datetime.strptime(params['date'], '%Y-%m-%d')
        action_url = '/dashboard/{0}?section=scheduler'.format(self.object.slug)
        [sunday, saturday] = self.get_sun_sat(date)
        weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        drivers = params['drivers']

        def get_duration(start, end):
            # start_t = schedule_date.replace(hour=start.hour, minute=start.minute)
            d_start = (int(start.split(':')[0]) + (int(start.split(':')[1]) / 60))
            d_end = (int(end.split(':')[0]) + (int(end.split(':')[1]) / 60))
            if d_start > d_end:
                duration = ((d_end + 24) - d_start)
            else:
                duration = (d_end - d_start)
            return duration

        def get_end_date(start, end, date):
            if int(start.split(':')[0]) >= int(end.split(':')[0]):
                schedule_date = date + dt.timedelta(days=1)
            else:
                schedule_date = date
            schedule_date = schedule_date.replace(hour=int(end.split(':')[0]), minute=int(end.split(':')[1]))
            return schedule_date

        for i in range(len(weekdays)):
            schedule_date = sunday + dt.timedelta(days=i)
            schedule = TimeseriesSchedule.objects.get_or_create(date=schedule_date, organization_id=self.object.id)[0]
            scheduled_drivers = TimeseriesScheduledDrivers.objects.filter(schedule=schedule)
            scheduled_drivers.delete()

            scheduled_drivers = TimeseriesScheduledDrivers.objects.bulk_create([
                TimeseriesScheduledDrivers(
                    schedule=schedule,
                    employee=Employee.objects.get(id=d['id']),
                    start_date=schedule_date + dt.timedelta(hours=int(d[f'{weekdays[i]} Start'].split(':')[0]),
                                                       minutes=int(d[f'{weekdays[i]} Start'].split(':')[1])),
                    end_date=get_end_date(d[f'{weekdays[i]} Start'], d[f'{weekdays[i]} End'], schedule_date),
                    duration=get_duration(d[f'{weekdays[i]} Start'], d[f'{weekdays[i]} End']),
                    schedule_type=d['Service Type']
                ) for d in drivers if d[f'{weekdays[i]} Start'] is not None and d[f'{weekdays[i]} End']
            ])
            self.save_daily_schedule(schedule_date, scheduled_drivers)
        return {'success': True}
            # for d in drivers:
            #     employee = Employe.objects.get(id=d['id'])
