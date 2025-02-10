from django.urls import path
from . import views
from .wingSpanPayment import WingSpanPayments

app_name = 'payments'

urlpatterns = [
    # Your URLs...
    path('', views.Payments.as_view(), name='payments'),
    path('wingspan/', WingSpanPayments.as_view(), name='wingspan'),
    path('send-payment-email/', views.PaymentsEmailSend.as_view(), name='payment_email')
]
