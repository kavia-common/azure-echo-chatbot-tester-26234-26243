from django.urls import path
# Import only simple callables to avoid heavy logic at import-time.
from .views import health, messages  # Both are lightweight view callables

# PUBLIC_INTERFACE
# urlpatterns is the URL configuration for the 'api' application.
# It must be importable without side effects for Django to load URLConf successfully.
urlpatterns = [
    path('health/', health, name='Health'),
    path('messages/', messages, name='bot-messages'),
]
