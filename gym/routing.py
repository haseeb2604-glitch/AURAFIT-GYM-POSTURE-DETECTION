from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/workout/(?P<exercise_key>\w+)/$', consumers.WorkoutConsumer.as_asgi()),
]
