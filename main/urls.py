from django .urls import path
from .views import equipment_list_api
urlpatterns = [
    path('api/equipment/', equipment_list_api),
]