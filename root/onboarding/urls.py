from django.urls import path
from . import views, usage
from . import tracking

app_name = 'onboarding'

urlpatterns = [
    # Your URLs...
    path('', views.Onboarding.as_view(), name='onboarding'),
    path('feedback/', views.Feedback.as_view(), name='feedback'),
    path('ga/', views.GoogleAnalytics.as_view(), name='googleAnalytics'),
    path('documentation/', views.DocumentationView.as_view(), name='documentation'),
    path('enhancements/', views.EnhancementsView.as_view(), name='enhancements'),
    path('product-usage/', views.ProductUsage.as_view(), name='product-usage'),
    path('usage/', usage.Usage.as_view(), name='usage')
]
