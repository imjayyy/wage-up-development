"""Hello Analytics Reporting API V4."""

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
import os

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
# SCOPES = ['https://analyticsreporting.googleapis.com/v4/userActivity:search']
path_to_gaKey = os.path.join(settings.BASE_DIR,'gaKey.json')

KEY_FILE_LOCATION = path_to_gaKey
VIEW_ID = '211792955'


def initialize_analyticsreporting():
  """Initializes an Analytics Reporting API V4 service object.

  Returns:
    An authorized Analytics Reporting API V4 service object.
  """
  credentials = ServiceAccountCredentials.from_json_keyfile_name(
      KEY_FILE_LOCATION, SCOPES)

  # Build the service object.
  analytics = build('analyticsreporting', 'v4', credentials=credentials)

  return analytics


def get_report(analytics):
  """Queries the Analytics Reporting API V4.

  Args:
    analytics: An authorized Analytics Reporting API V4 service object.
  Returns:
    The Analytics Reporting API V4 response.
  """
  return analytics.reports().batchGet(
    body={
      "viewId": VIEW_ID,
      "user": {
        "type": "CLIENT_ID",
        "userId": "dgonier"
      },
      "dateRange": {
        "startDate": "2020-01-01",
        "endDate": "2020-12-31",
      }
    }
  ).execute()




def session_counts_by_date(response):
  sessions = response['sessions']
  session_counts = {}
  for session in sessions:
    date = session['sessionDate']
    if date in session_counts:
      session_counts[date]+=1
    else:
      session_counts[date] = 0
  return session_counts

def generate_request(user_id):
  return {
    "viewId": VIEW_ID,
    "user": {
      "type": "USER_ID",
      "userId": user_id
    },
    "dateRange": {
      "startDate": "2020-01-01",
      "endDate": "2020-12-31",
    }
  }

def get_user_session_counts(user_id):
  ga = initialize_analyticsreporting()
  return session_counts_by_date(ga.userActivity().search(body=generate_request(user_id)).execute())

def get_user_list_session_counts(employee_queryset):
  out = []
  for emp in employee_queryset:
    if not emp['user_id']:
      out.append({"user": emp, "data": "no data"})
    try:
      out.append({"user": emp, "data": get_user_session_counts(str(emp['user_id']))})
    except:
      out.append({"user": emp, "data": "no data"})
  return out

def get_user_data(user_id):
  ga = initialize_analyticsreporting()
  return ga.userActivity().search(body=generate_request(user_id)).execute()

def get_metric(metric):
  ga = initialize_analyticsreporting()
  response = ga.reports().batchGet(
    body={
      "reportRequests": [
        {
          "viewId": VIEW_ID,
          "metrics": [
            {
              "expression": metric,
              "alias": ""
            }
          ]}
      ]
    }).execute()
  return response

# def print_response(response):
#   """Parses and prints the Analytics Reporting API V4 response.
#
#   Args:
#     response: An Analytics Reporting API V4 response.
#   """
#   for report in response.get('reports', []):
#     columnHeader = report.get('columnHeader', {})
#     dimensionHeaders = columnHeader.get('dimensions', [])
#     metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
#
#     for row in report.get('data', {}).get('rows', []):
#       dimensions = row.get('dimensions', [])
#       dateRangeValues = row.get('metrics', [])
#
#       for header, dimension in zip(dimensionHeaders, dimensions):
#         print(header + ': ' + dimension)
#
#       for i, values in enumerate(dateRangeValues):
#         print('Date range: ' + str(i))
#         for metricHeader, value in zip(metricHeaders, values.get('values')):
#           print(metricHeader.get('name') + ': ' + value)
#
#
# def main():
#   analytics = initialize_analyticsreporting()
#   response = get_report(analytics)
#   print(response)
#   # print_response(response)
#
# if __name__ == '__main__':
#   main()
