from django.urls import path,include
from .views import equipment_list_api, contact_message_api

urlpatterns = [
    path('api/equipment/', equipment_list_api),
    path('api/contact/', contact_message_api),
]
