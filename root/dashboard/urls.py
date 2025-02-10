from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from . import views
from . import myDashboardView
from . import dashboard_data

app_name= 'dashboard'

urlpatterns = [
    # Your URLs...
    path('my-dashboard/', myDashboardView.EmployeeDashboardApi.as_view(), name='custom_dashboard'),
    path('dashboard-data/<slug:section>/<slug:subsection>/',
         dashboard_data.DashboardData.as_view(),
         name='dashboard_data'),
    path('dashboard-data/', dashboard_data.DashboardData.as_view(), name='dashboard_data'),
    path('', views.DashboardRouter.as_view(), name='dashboard'),
]
