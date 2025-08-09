from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('api/', include('accounts.urls')),
    path('health/', health_check),  # For Render health checks
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
