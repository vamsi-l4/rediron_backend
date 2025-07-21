from django.contrib import admin
from .models import Equipment
from .models import ContactMessage

class EquipmentAdmin(admin.ModelAdmin):
    list_display=('name','category','usage')

class ContactMessageAdmin(admin.ModelAdmin):
    list_display=('name','email','subject','created_at')
    search_fields=('name','email','subject','message')

admin.site.register(ContactMessage,ContactMessageAdmin)        

admin.site.register(Equipment)
