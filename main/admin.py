from django.contrib import admin
from .models import Equipment

class EquipmentAdmin(admin.ModelAdmin):
    list_display=('nane','category','usage')

admin.site.register(Equipment)
