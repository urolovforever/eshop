from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from apps.product.models import Product
from .models import Config, User


def index(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True)
    context = {
        "featured_products": featured_products
    }
    return render(request, 'index.html', context)

def about(request):
    about_page = Config.objects.first().about_page
    return render(request, 'main/about.html', {"about_page": about_page})

def contact(request):
    return render(request, 'main/contact.html')


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        phone = request.POST.get('phone', '').strip()

        # Validation
        if not all([username, email, password, password_confirm]):
            messages.error(request, 'All fields are required.')
            return render(request, 'auth/register.html')

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'auth/register.html')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/register.html')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'auth/register.html')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,  # Django automatically hashes the password
                phone=phone
            )

            # Log the user in
            auth_login(request, user)
            messages.success(request, 'Registration successful! Welcome to our store.')
            return redirect('index')

        except IntegrityError:
            messages.error(request, 'An error occurred. Please try again.')
            return render(request, 'auth/register.html')

    return render(request, 'auth/register.html')


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'auth/login.html')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                auth_login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')

                # Redirect to next parameter or index
                next_url = request.GET.get('next', 'index')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account has been disabled.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    """User logout view"""
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')