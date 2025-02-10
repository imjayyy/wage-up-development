from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from . import views
from django.conf.urls import include
from . reset_password_views import *

app_name= 'accounts'

urlpatterns = [
    # Your URLs...
    path('login/', views.Login.as_view(), name='token_obtain_pair'),
    path('refresh/', views.RefreshToken.as_view(), name='token_refresh'),
    path('health-check/', views.HealthCheck.as_view(), name='hello'),
    path('create-user/', views.CreateUser.as_view(), name='create-user'),
    path('verify/<slug:uidb64>/<slug:token>/', views.CreateUser.receive_verified_email, name='verify'),
    path('reset-password/', reset_password_request_token, name="reset-password-request"),
    path('reset-password/confirm/', reset_password_confirm, name="reset-password-confirm"),
    path('undo-actions/', views.ActionsMgmt.as_view(), name="undo-actions"),

    ### serializers ##
    path('invites/', views.ModelQueries.Invite.List.as_view(), name='employee-list'),
    path('invite/', views.ModelQueries.Invite.Detail.as_view(), name='employee-detail'),
    path('get-invite/', views.ModelQueries.Invite.Detail_GET.as_view(), name='employee-detail-get'),
    path('employees/', views.ModelQueries.Employee.List.as_view(), name='employee-list'),
    path('employee/', views.ModelQueries.Employee.Detail.as_view(), name='employee-detail'),
    path('update-employee/', views.EmployeeUpdate.as_view(), name='employee-update'),
    path('organizations/', views.ModelQueries.Organization.List.as_view(), name='organization-list'),
    path('organization/', views.ModelQueries.Organization.Detail.as_view(), name='organization-detail'),
    path('profiles/', views.ModelQueries.Profile.List.as_view(), name='profile-list'),
    path('profile/', views.ModelQueries.Profile.Detail.as_view(), name='profile-detail'),
    # path('appeals/', views.ModelQueries.Appeals.List.as_view(), name='appeals-list'),
    # path('appeal/', views.ModelQueries.Appeals.Detail.as_view(), name='appeals-detail'),
    path('profile-picture/', views.ProfilePictureUploadView.as_view(), name='profile-picture'),
    path('profile-banner/', views.ProfileBannerUploadView.as_view(), name='profile-banner'),
    path('permissions/', views.ModelQueries.Permission.List.as_view(), name='premission-list'),
    path('permission/', views.ModelQueries.Permission.Detail.as_view(), name='premission-detail'),
    path('bookmark/', views.ModelQueries.Bookmark.Detail.as_view(), name='bookmark-detail'),
    path('driver-requests/', views.ModelQueries.SchedulerDriver.List.as_view(), name='scheduler-driver-requests'),
    path('driver-request/', views.ModelQueries.SchedulerDriver.Detail.as_view(), name='scheduler-driver-request'),
    path('survey/', views.SurveyView.as_view(), name='survey'),

]
