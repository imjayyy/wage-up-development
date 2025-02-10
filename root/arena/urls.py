from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from . import views

app_name = 'arena'

urlpatterns = [
    # Your URLs...
    path('', views.Arena.as_view(), name='arena'),
]
