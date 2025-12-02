from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.product.models import Product
from .models import Config, User, Wishlist


def index(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:6]
    new_arrivals = Product.objects.filter(is_active=True, is_new_arrival=True).order_by('-created_at')[:4]
    on_sale_products = Product.objects.filter(is_active=True, on_sale=True)[:4]
    config = Config.objects.first()

    context = {
        "featured_products": featured_products,
        "new_arrivals": new_arrivals,
        "on_sale_products": on_sale_products,
        "config": config
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

    return render(request, 'register.html')


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

    return render(request, 'login.html')


@login_required
def logout_view(request):
    """User logout view"""
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')


def forgot_password(request):
    """Forgot password view"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Please provide your email address.')
            return render(request, 'forgotten-password.html')

        # Check if user with this email exists
        try:
            user = User.objects.get(email=email)
            # TODO: Implement password reset email sending
            messages.success(request, f'Password reset instructions have been sent to {email}. Please check your inbox.')
            return redirect('login')
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request, f'If an account exists with {email}, you will receive password reset instructions.')
            return redirect('login')

    return render(request, 'forgotten-password.html')


@require_POST
def toggle_wishlist(request):
    """Toggle product in user's wishlist (add or remove)"""
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    product_id = request.POST.get('product_id')

    if not product_id:
        return JsonResponse({'success': False, 'error': 'Product ID is required'}, status=400)

    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
    except:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)

    # Check if product is already in wishlist
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()

    if wishlist_item:
        # Remove from wishlist
        wishlist_item.delete()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True,
            'action': 'removed',
            'added': False,
            'message': f'{product.name} removed from wishlist',
            'wishlist_count': wishlist_count
        })
    else:
        # Add to wishlist
        Wishlist.objects.create(user=request.user, product=product)
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True,
            'action': 'added',
            'added': True,
            'message': f'{product.name} added to wishlist',
            'wishlist_count': wishlist_count
        })


@login_required
def wishlist_view(request):
    """View user's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'main/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def get_wishlist_count(request):
    """Get the count of items in user's wishlist"""
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})