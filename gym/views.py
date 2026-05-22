import cv2
import json
import time
import mediapipe as mp
import numpy as np
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.templatetags.static import static
import os
from django.conf import settings

from .models import UserProfile, WorkoutSession, EXERCISE_CHOICES
from .forms import RegisterForm, UserProfileForm
from .gym_logic import EXERCISE_META, EXERCISE_LOGIC_MAP, get_initial_state, run_exercise_logic

mp_pose_module = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# ─────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, f'Welcome to AuraFit Pro, {user.first_name}! 🎉')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'gym/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'gym/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    sessions = WorkoutSession.objects.filter(user=user)

    stats = {
        'total_sessions': sessions.count(),
        'total_reps': sessions.aggregate(Sum('total_reps'))['total_reps__sum'] or 0,
        'total_duration': sessions.aggregate(Sum('duration_seconds'))['duration_seconds__sum'] or 0,
        'avg_efficiency': round(sessions.aggregate(Avg('efficiency_percent'))['efficiency_percent__avg'] or 0),
    }
    stats['total_duration_min'] = stats['total_duration'] // 60

    recent_sessions = sessions[:6]
    exercise_breakdown = {}
    for key, label in EXERCISE_CHOICES:
        count = sessions.filter(exercise=key).count()
        if count > 0:
            exercise_breakdown[label] = count

    exercises = [
        {'key': k, **v} for k, v in EXERCISE_META.items()
    ]

    return render(request, 'gym/dashboard.html', {
        'stats': stats,
        'recent_sessions': recent_sessions,
        'exercise_breakdown': json.dumps(exercise_breakdown),
        'exercises': exercises,
    })


# ─────────────────────────────────────────────
# WORKOUT SESSION PAGE
# ─────────────────────────────────────────────

@login_required
def workout(request, exercise_key):
    if exercise_key not in EXERCISE_META:
        return redirect('dashboard')
    meta = EXERCISE_META[exercise_key]
    demo_files = {
        'squats': 'squats_demo.mp4',
        'lunges': 'lunges_demo.mp4',
        'pushups': 'pushups_demo.mp4',
        'jumping_jacks': 'jumping_jacks_demo.mp4',
    }
    demo_video_map = {}
    for k, fname in demo_files.items():
        url = static(f'demo_videos/{fname}')
        try:
            file_path = settings.BASE_DIR / 'demo_videos' / fname
            if file_path.exists():
                mtime = int(file_path.stat().st_mtime)
                url = f"{url}?v={mtime}"
        except Exception:
            pass
        demo_video_map[k] = url
    return render(request, 'gym/workout.html', {
        'exercise_key': exercise_key,
        'meta': meta,
        'exercise_choices': EXERCISE_CHOICES,
        'demo_video_url': demo_video_map.get(exercise_key, ''),
    })


# ─────────────────────────────────────────────
# LIVE CAMERA STREAM (MJPEG)
# ─────────────────────────────────────────────

def camera_stream(request, exercise_key):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if exercise_key not in EXERCISE_LOGIC_MAP:
        return JsonResponse({'error': 'Unknown exercise'}, status=400)

    def generate_frames():
        pose = mp_pose_module.Pose(min_detection_confidence=0.8, min_tracking_confidence=0.8)
        cap = cv2.VideoCapture(0)

        meta = EXERCISE_META[exercise_key]
        state = get_initial_state()
        state['stage'] = meta['initial_stage']

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                if results.pose_landmarks:
                    run_exercise_logic(exercise_key, results.pose_landmarks.landmark, state)
                    mp_drawing.draw_landmarks(
                        frame, results.pose_landmarks, mp_pose_module.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=2),
                        mp_drawing.DrawingSpec(color=state['clr'], thickness=2)
                    )

                # Overlay HUD on frame
                h, w, _ = frame.shape
                cv2.rectangle(frame, (0, 0), (w, 70), (10, 10, 20), -1)
                clr = state['clr']
                cv2.putText(frame, f"REPS: {state['reps']}", (20, 30),
                            cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
                cv2.putText(frame, state['msg'], (20, 58),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, clr, 2)

                # Efficiency bar
                if state['total_frames'] > 0:
                    eff = int((state['correct_frames'] / state['total_frames']) * 100)
                    eff = min(eff, 100)
                    bar_w = int((w - 40) * eff / 100)
                    cv2.rectangle(frame, (20, h - 20), (w - 20, h - 8), (50, 50, 50), -1)
                    bar_clr = (0, 255, 100) if eff >= 80 else (0, 200, 255) if eff >= 50 else (0, 80, 255)
                    cv2.rectangle(frame, (20, h - 20), (20 + bar_w, h - 8), bar_clr, -1)
                    cv2.putText(frame, f"Efficiency: {eff}%", (20, h - 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        finally:
            cap.release()
            pose.close()

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# ─────────────────────────────────────────────
# SAVE WORKOUT
# ─────────────────────────────────────────────

@login_required
@csrf_exempt
@require_POST
def save_workout(request):
    try:
        data = json.loads(request.body)
        session = WorkoutSession.objects.create(
            user=request.user,
            exercise=data.get('exercise', ''),
            sets_completed=data.get('sets_completed', 0),
            total_reps=data.get('total_reps', 0),
            target_sets=data.get('target_sets', 3),
            target_reps=data.get('target_reps', 10),
            duration_seconds=data.get('duration_seconds', 0),
            efficiency_percent=min(data.get('efficiency_percent', 0), 100),
            target_met=data.get('target_met', False),
            notes=data.get('notes', ''),
        )
        return JsonResponse({'status': 'saved', 'session_id': session.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

@login_required
def history(request):
    exercise_filter = request.GET.get('exercise', '')
    sessions = WorkoutSession.objects.filter(user=request.user)
    if exercise_filter:
        sessions = sessions.filter(exercise=exercise_filter)

    stats = {
        'total': sessions.count(),
        'total_reps': sessions.aggregate(Sum('total_reps'))['total_reps__sum'] or 0,
        'avg_efficiency': round(sessions.aggregate(Avg('efficiency_percent'))['efficiency_percent__avg'] or 0),
        'targets_met': sessions.filter(target_met=True).count(),
    }

    return render(request, 'gym/history.html', {
        'sessions': sessions[:50],
        'stats': stats,
        'exercise_choices': EXERCISE_CHOICES,
        'selected_exercise': exercise_filter,
    })


# ─────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────

@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile_obj)
    return render(request, 'gym/profile.html', {'form': form, 'profile': profile_obj})


# ─────────────────────────────────────────────
# DELETE SESSION
# ─────────────────────────────────────────────

@login_required
def delete_session(request, session_id):
    session = get_object_or_404(WorkoutSession, id=session_id, user=request.user)
    session.delete()
    messages.success(request, 'Session deleted.')
    return redirect('history')
