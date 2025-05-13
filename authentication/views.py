from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login , logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache
import re
from django.contrib.auth import login
from .utils import send_otp
from datetime import datetime, timedelta
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import timedelta
from django.db import transaction
from django.urls import reverse
from decimal import Decimal
from django.http import HttpResponse
from django.views import View
from django.db.models import Q
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from urllib.parse import urlencode
import requests
from django.http import HttpResponse
from django.contrib.auth import login
from authentication.models import CustomUser  
from product.models import Brand, ProductImage,Products,Category





def block_superuser_navigation(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect(reverse('customadmin:admin_dashboard'))  
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    decorator = user_passes_test(lambda u: u.is_authenticated and u.is_staff)
    return decorator(view_func)



@never_cache
@block_superuser_navigation
def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    login_error = None

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_blocked:
                login_error = "This account is inactive. Please contact support."
            elif user.is_blocked:
                login_error = "This account is blocked. Please contact support."
            else:
                login(request, user)
                return redirect('home')
        else:
            login_error = "Invalid email or password. Please try again."

    return render(request, 'user_auth/login.html', {'login_error': login_error})





@never_cache
@block_superuser_navigation
def user_signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
    
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

    
        if len(full_name) < 3:
            messages.error(request, "Full name must be at least 3 characters long.")
            return redirect('user_signup')

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('user_signup')

        if not re.match(r'^\+?1?\d{9,15}$', phone_number):
            messages.error(request, "Please enter a valid phone number (up to 15 digits).")
            return redirect('user_signup')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('user_signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_signup')

        if CustomUser .objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('user_signup')

        if CustomUser .objects.filter(phone_number=phone_number).exists():
            messages.error(request, "An account with this phone number already exists.")
            return redirect('user_signup')

        request.session.flush()

        otp = send_otp(email)

        user_data = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number,
            'otp': otp,
            'otp_created_at': timezone.now().isoformat(), 
            'password': make_password(password), 
        }
        request.session['user_data'] = user_data

        return redirect('verify_otp')

    return render(request, 'user_auth/signup.html')




@never_cache
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        user_data = request.session.get('user_data')

        if not user_data:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect('user_signup')

        otp = user_data.get('otp')
        otp_created_at = datetime.fromisoformat(user_data.get('otp_created_at'))

    
        if timezone.now() > otp_created_at + timedelta(minutes=1):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect('resend_otp')

        if entered_otp == otp:
    
            user = CustomUser (
                full_name=user_data['full_name'],
                email=user_data['email'],
                phone_number=user_data['phone_number'],
                password=user_data['password']
            )
            user.save()

            request.session.flush()

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, "Account created successfully! You are now logged in.")
            return redirect('user_login')  
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    user_data = request.session.get('user_data')
    return render(request, 'user_auth/verify_otp.html', {'user_data': user_data})


@never_cache
def resend_otp(request):
    user_data = request.session.get('user_data')

    if not user_data:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('user_signup')

    otp = send_otp(user_data['email'])

    user_data['otp'] = otp
    user_data['otp_created_at'] = timezone.now().isoformat()  
    request.session['user_data'] = user_data

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_otp')


@never_cache
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)

            otp = send_otp(email)
            
            reset_data = {
                'email': email,
                'otp': otp,
                'otp_created_at': timezone.now().isoformat(),
                'is_password_reset': True
            }
            request.session['reset_data'] = reset_data
            
            messages.success(request, 'OTP has been sent to your email.')
            return redirect('verify_reset_otp')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    return render(request, 'user_auth/password/forgot_password.html')


def verify_reset_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        reset_data = request.session.get('reset_data')

        if not reset_data:
            messages.error(request, "Session expired. Please try again.")
            return redirect('forgot_password')

        otp = reset_data.get('otp')
        try:
            otp_created_at = datetime.fromisoformat(reset_data.get('otp_created_at'))
        except (TypeError, ValueError):
            messages.error(request, "Invalid OTP data. Please request a new one.")
            return redirect('forgot_password')

        if timezone.now() > otp_created_at + timedelta(minutes=2):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect('resend_reset_otp')

        if entered_otp == otp:
            reset_data['otp_verified'] = True
            request.session['reset_data'] = reset_data
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    reset_data = request.session.get('reset_data')
    return render(request, 'user_auth/password/verify_reset_otp.html', {'reset_data': reset_data})


@never_cache
def resend_reset_otp(request):
    reset_data = request.session.get('reset_data')

    if not reset_data:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')

    email = reset_data['email']
    otp = send_otp(email)

    reset_data['otp'] = otp
    reset_data['otp_created_at'] = timezone.now().isoformat()
    request.session['reset_data'] = reset_data

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_reset_otp')


@never_cache
def reset_password(request):
    reset_data = request.session.get('reset_data')
    
    if not reset_data or not reset_data.get('otp_verified'):
        messages.error(request, "Please verify your OTP first")
        return redirect('forgot_password')
        
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'user_auth/password/reset_password.html')
            
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'user_auth/password/reset_password.html')
            
        try:
            user = CustomUser.objects.get(email=reset_data['email'])
            user.set_password(new_password)
            user.save()
            
            request.session.flush()
            
            messages.success(request, 'Password has been reset successfully')
            return redirect('user_login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Something went wrong. Please try again.')
            return redirect('forgot_password')
            
    return render(request, 'user_auth/password/reset_password.html')



@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)  
            return redirect('admin_dashboard')  
        else:
            messages.error(request, "Invalid username or password")  
            return redirect('admin_login')  

    return render(request, 'admin_login.html')  


@block_superuser_navigation

def home(request):
    
    if not request.user.is_authenticated:
        print("User is not authenticated, redirecting to login.")
        return redirect('user_login')  
    
    print("User is authenticated, rendering home.")
    

    new_products = Products.objects.filter(is_active=True)[:8]   
    categories = Category.objects.filter(is_active=True)  
    

    context = {
        'user': request.user,
        'new_products': new_products,
        'categories': categories,
    }

    return render(request, 'user_auth/home.html', context)



def user_logout(request):
    logout(request)
    print("User logged out:", request.user.is_authenticated)  
    return redirect('home')


# def product(request):
#     products = Products.objects.all()
#     brands = Brand.objects.all()
#     categories = Category.objects.all()

#     context = {
#         'products': products,
#         'brands': brands,
#         'categories': categories,
#         'search_query': request.GET.get('search', ''),
#         'brand_filter': request.GET.get('brand', ''),
#         'category_filter': request.GET.get('category', ''),
#         'price_filter': request.GET.get('price', ''),
#         'sort_by': request.GET.get('sort', ''),
#     }

#     return render(request, 'user_auth/products.html', context)



