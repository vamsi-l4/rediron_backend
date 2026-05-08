from django.urls import path, include
from django.shortcuts import redirect
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/admin/', lambda request: redirect('/admin/', permanent=False)),
    path('', lambda request: redirect('api-root', permanent=False)),
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('main.urls')),
    path('api/', include('rediron_shop.urls')),
]

# ✅ Serve media files when DEBUG=True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files in production
from django.conf import settings
from django.urls import re_path
from django.views.static import serve

if not settings.DEBUG:
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]

