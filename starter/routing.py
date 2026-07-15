"""WebSocket URL routing"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('api/tts', consumers.TtsConsumer.as_asgi()),
]
