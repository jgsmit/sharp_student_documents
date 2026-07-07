# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from .forms import CustomUserCreationForm, CustomUserChangeForm, CustomAuthenticationForm
from notifications.utils import send_new_user_notification


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send notification to admin about new user registration
            try:
                send_new_user_notification(user)
            except Exception as e:
                # Don't fail registration if email fails
                print(f"Failed to send new user notification: {e}")
            
            login(request, user)
            return redirect("documents:dashboard")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next") or "documents:dashboard"
            return redirect(next_url)
        else:
            return render(request, "accounts/login.html", {"form": form})
    else:
        form = CustomAuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def password_redirect(request):
    """
    Redirect to appropriate password page based on authentication status
    """
    if request.user.is_authenticated:
        # Logged in users can change their password
        return redirect("password_change")
    else:
        # Logged out users need to reset their password
        return redirect("password_reset")


@login_required
def profile_view(request):
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})
