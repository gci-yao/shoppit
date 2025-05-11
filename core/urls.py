# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register_user/', views.register_user, name='register_user'),
    path("send_welcome_email/", views.send_welcome_email, name="send_welcome_email")

]
