from django.urls import path, re_path
from django.urls import path
from .views import *



urlpatterns = [
    # url(r'^$', WageupSearchView.as_view(), name='search_view'),
    path('', ajaxsearch),
    path('employees', ajaxsearch_employee),
    path('organizations', ajaxsearch_organizations),
    path('employee-email', ajaxsearch_employee_email),
    path('sat-app-emp-search', ajaxsearch_sat_app),
]
