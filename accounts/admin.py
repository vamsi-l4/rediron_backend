from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import OTP, RefreshToken, UserActivityData

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_staff', 'is_active')
    search_fields = ('email', 'name')

admin.site.register(OTP)
admin.site.register(RefreshToken)
admin.site.register(UserActivityData)
