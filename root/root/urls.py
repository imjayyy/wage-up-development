"""root URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
# from .settings import MEDIA_ROOT, MEDIA_URL
# from django.conf.urls.static import static

from django.conf import settings
from django.conf.urls.static import static
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

admin.site.site_header = "WageUp AAA NE Admin"
admin.site.site_title = "WageUp AAA NE Admin"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('search/', include('search.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('training/', include('training.urls')),
    path('arena/', include('arena.urls')),
    path('performance/', include('performance_points.urls')),
    path('onboarding/', include('onboarding.urls')),
    path('messaging/', include('messaging.urls')),
    path('observations/', include('observations.urls')),
    path('register-notif-token/',FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
    path('homepage/', include('homepage.urls')),
    path('health/', include('health_check.urls')),
    path('payments/', include('payments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
