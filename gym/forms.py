from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['age', 'weight_kg', 'height_cm', 'fitness_goal', 'profile_pic']
        widgets = {
            'fitness_goal': forms.TextInput(attrs={'placeholder': 'e.g. Lose weight, Build muscle'}),
            'age': forms.NumberInput(attrs={'min': 10, 'max': 100}),
            'weight_kg': forms.NumberInput(attrs={'min': 20, 'max': 300, 'step': '0.1'}),
            'height_cm': forms.NumberInput(attrs={'min': 100, 'max': 250, 'step': '0.1'}),
        }
