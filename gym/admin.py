from django.contrib import admin
from .models import UserProfile, WorkoutSession


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'age', 'weight_kg', 'height_cm', 'fitness_goal']
    search_fields = ['user__username', 'user__email']


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'exercise', 'total_reps', 'sets_completed',
                    'efficiency_percent', 'target_met', 'created_at']
    list_filter = ['exercise', 'target_met', 'created_at']
    search_fields = ['user__username']
    ordering = ['-created_at']
