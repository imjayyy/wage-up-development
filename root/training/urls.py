from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from . import views
from . import campaigns

app_name = 'training'

urlpatterns = [
    # Your URLs...
    path('', views.Training.as_view(), name='training'),
    path('user', views.get_user_employee, name='get_user_info'),
    path('campaign_list/', views.campaign_user_list, name='register_list'),
    path('questions/', views.get_campaign_module, name='get_questions'),
    path('join/', views.user_campaign_completion, name='join_campaign'),
    path('stats/', views.get_hh5_stats, name='get_stats'),
    path('campaigns/', campaigns.Campaining.as_view(), name='campaigns')
]
