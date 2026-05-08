# apps.py

from django.apps import AppConfig

class RedironShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rediron_shop'
    verbose_name = "Rediron Shop"  # Optional: This name will appear in Django admin
