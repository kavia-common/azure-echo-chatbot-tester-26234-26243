from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Use full Python path to prevent ambiguity in some environments
    name = 'api'
