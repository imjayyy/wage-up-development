# chat/routing.py
# from django.conf.urls import url
from django.urls import path, include

from . import consumers

websocket_urlpatterns = [
    path('ws/', consumers.generalConsumer),
]
