from django.urls import path
from . import views

app_name = 'performance_points'

urlpatterns = [
    # Your URLs...
    path('', views.PerformancePoints.as_view(), name='performance_points'),
]
