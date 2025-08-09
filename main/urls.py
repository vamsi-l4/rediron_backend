# main/urls.py
from django.urls import path
from .views import equipment_list_api, contact_message_api

urlpatterns = [
    path("api/equipment/", equipment_list_api, name="equipment-list"),
    path("api/contact/", contact_message_api, name="contact-message"),
]
