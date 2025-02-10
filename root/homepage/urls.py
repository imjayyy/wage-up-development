from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from . import views

app_name= 'homepage'

urlpatterns = [
    path('', views.Homepage.as_view(), name='homepage_widgets'),
    path('carousel-upload/', views.CarouselPictureUploadView.as_view(), name='carousel-upload'),
    path('file-upload/', views.FileUploadView.as_view(), name='homepage-file-upload'),
    path('modal-file-upload/', views.ModalFileUpload.as_view(), name='modal-file-upload'),
    path('user-file-upload/', views.UserFileUploadView.as_view(), name='user-file-upload'),
]