from django.urls import path
from .views import health, messages

urlpatterns = [
    path('health/', health, name='Health'),
    path('messages', messages, name='bot-messages'),
]
