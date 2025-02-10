from django.urls import path
from . import views
from . import chats
app_name = 'messaging'

urlpatterns = [
    # Your URLs...
    path('', views.Messaging.as_view(), name='messaging'),
    # path('update-email-table/', views.update_email_table_lambda_data),
    path('update-email/', views.update_email_data),
    path('get-email/', views.get_email),
    path('trigger-emails/', views.trigger_emails),
    # path('chat/', chats.Chat.as_view(), name='chat'),
    path('notification-response/', chats.record_notification_response, name='chat_settings'),
    path('alert-data-processing/', chats.alert_data_processing, name='alert_data_processing'),
    path('verify-token/', chats.verify_token, name='verify-token')
]
