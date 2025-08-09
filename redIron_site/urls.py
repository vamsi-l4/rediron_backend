# redIron_site/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

def health_view(request):
    """Simple health / root endpoint so visiting / won't return 404."""
    return JsonResponse({
        "status": "ok",
        "service": "redIron backend",
        "message": "Backend is up. Use /api/ for API endpoints."
    })

urlpatterns = [
    path("", health_view, name="health"),            # <-- root health check
    path("admin/", admin.site.urls),
    path("", include("main.urls")),                   # your main app routes
    path("api/", include("accounts.urls")),           # accounts APIs e.g. signup, login etc.
]

# serve media during development / Render static show
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
