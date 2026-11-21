from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm
from .models import User
from dashboard.services.report_service import log_audit

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            log_audit(user, 'USER_REGISTER', 'User', user.id, f"Registered new account: {user.email}")
            messages.success(request, f"Welcome to EventHub, {user.full_name}! Your account has been created.")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        if request.user.has_admin_access:
            return redirect('dashboard:home')
        return redirect('home')

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']

            # Check if user locked
            try:
                user_obj = User.objects.get(email=email)
                if user_obj.locked_until and user_obj.locked_until > timezone.now():
                    messages.error(request, "Account temporarily locked due to repeated failed logins. Please try again later.")
                    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})
            except User.DoesNotExist:
                user_obj = None

            user = authenticate(request, username=email, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, "This account has been deactivated. Please contact support.")
                    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})

                # Reset failed login count
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save(update_fields=['failed_login_attempts', 'locked_until'])

                login(request, user)
                log_audit(user, 'USER_LOGIN', 'User', user.id, f"User logged in: {user.email}")
                messages.success(request, f"Welcome back, {user.full_name or user.username}!")

                if next_url:
                    return redirect(next_url)
                if user.has_admin_access:
                    return redirect('dashboard:home')
                return redirect('home')
            else:
                if user_obj:
                    user_obj.failed_login_attempts += 1
                    if user_obj.failed_login_attempts >= 5:
                        user_obj.locked_until = timezone.now() + timezone.timedelta(minutes=15)
                    user_obj.save(update_fields=['failed_login_attempts', 'locked_until'])
                messages.error(request, "Invalid email or password.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})

def logout_view(request):
    if request.user.is_authenticated:
        log_audit(request.user, 'USER_LOGOUT', 'User', request.user.id, "Logged out")
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            log_audit(user, 'USER_UPDATE_PROFILE', 'User', user.id, "Updated profile")
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)

    bookings_count = user.bookings.filter(status='confirmed').count()
    return render(request, 'accounts/profile.html', {
        'form': form,
        'user': user,
        'bookings_count': bookings_count
    })
