from django.urls import path
from .views import custom_login,signup

urlpatterns = [
    path('login/', custom_login, name='custom_login'),
    path('signup/',signup,name='signup'),
]
