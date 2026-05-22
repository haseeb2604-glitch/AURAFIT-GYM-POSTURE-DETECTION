from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.IntegerField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    fitness_goal = models.CharField(max_length=200, default="General Fitness")
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def bmi(self):
        if self.weight_kg and self.height_cm:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None


EXERCISE_CHOICES = [
    ('jumping_jacks', 'Jumping Jacks'),
    ('lunges', 'Lunges'),
    ('pushups', 'Push Ups'),
    ('squats', 'Squats'),
]


class WorkoutSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    exercise = models.CharField(max_length=50, choices=EXERCISE_CHOICES)
    sets_completed = models.IntegerField(default=0)
    total_reps = models.IntegerField(default=0)
    target_sets = models.IntegerField(default=3)
    target_reps = models.IntegerField(default=10)
    duration_seconds = models.IntegerField(default=0)
    efficiency_percent = models.IntegerField(default=0)
    target_met = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_exercise_display()} - {self.created_at.strftime('%d %b %Y')}"

    def duration_display(self):
        h = self.duration_seconds // 3600
        m = (self.duration_seconds % 3600) // 60
        s = self.duration_seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def efficiency_color(self):
        if self.efficiency_percent >= 80:
            return 'success'
        elif self.efficiency_percent >= 50:
            return 'warning'
        return 'danger'
