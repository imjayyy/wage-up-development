from django.urls import path

from . import views

urlpatterns = [
    path('', views.Comments_.as_view(), name='comments'),
]