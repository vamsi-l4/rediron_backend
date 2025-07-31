
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.custom_login, name='custom_login'),
    path('refresh/', views.refresh_token, name='refresh_token'),
    path('profile/', views.user_profile, name='user-profile'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),  
]
