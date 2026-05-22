from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.login_view,      name='home'),
    path('register/',                     views.register_view,   name='register'),
    path('login/',                        views.login_view,      name='login'),
    path('logout/',                       views.logout_view,     name='logout'),
    path('dashboard/',                    views.dashboard,       name='dashboard'),
    path('workout/<str:exercise_key>/',   views.workout,         name='workout'),
    path('stream/<str:exercise_key>/',    views.camera_stream,   name='camera_stream'),
    path('save-workout/',                 views.save_workout,    name='save_workout'),
    path('history/',                      views.history,         name='history'),
    path('profile/',                      views.profile,         name='profile'),
    path('delete/<int:session_id>/',      views.delete_session,  name='delete_session'),
]
