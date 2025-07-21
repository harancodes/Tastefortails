from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login , logout, get_user_model
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
from django.db.models import Min
from customadmin.models import Banner
from cart.models import Wallet




def block_superuser_navigation(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect(reverse('customadmin:admin_dashboard'))  
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    decorator = user_passes_test(lambda u: u.is_authenticated and u.is_staff)
    return decorator(view_func)




User = get_user_model()


@never_cache
@block_superuser_navigation
def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    login_error = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not email or not password:
            login_error = "Email and password are required."
        else:
            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                login_error = "No user found with this email."
            else:
                if getattr(user_obj, 'is_blocked', False):
                    login_error = "This account is blocked. Please contact support."
                elif not user_obj.check_password(password):
                    login_error = "Incorrect password. Please try again."
                else:
                    
                    user_obj.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user_obj)
                    return redirect('home')

    return render(request, 'user_auth/login.html', {'login_error': login_error})
import re
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import CustomUser
from .utils import (
    send_otp,
    is_strong_password,
    is_valid_full_name,
    is_valid_phone_number,
)


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
        referral_code = request.POST.get('referral_code', '').strip().upper()

        # Full name validation
        name_error = is_valid_full_name(full_name)
        if name_error:
            messages.error(request, name_error)
            return redirect('user_signup')

        # Email validation
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('user_signup')

        # Phone number validation
        phone_error = is_valid_phone_number(phone_number)
        if phone_error:
            messages.error(request, phone_error)
            return redirect('user_signup')

        # Password validation
        password_error = is_strong_password(password)
        if password_error:
            messages.error(request, password_error)
            return redirect('user_signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_signup')

        # Uniqueness checks
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('user_signup')

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "An account with this phone number already exists.")
            return redirect('user_signup')

        # Referral code check
        referrer = None
        if referral_code:
            try:
                referrer = CustomUser.objects.get(referral_code=referral_code)
            except CustomUser.DoesNotExist:
                messages.error(request, "Invalid referral code.")
                return redirect('user_signup')

        # Flush session and send OTP
        request.session.flush()
        otp = send_otp(email)

        # Store temporary data in session
        request.session['user_data'] = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number,
            'otp': otp,
            'otp_created_at': timezone.now().isoformat(),
            'password': make_password(password),
            'referrer_id': referrer.id if referrer else None,
        }

        return redirect('verify_otp')

    return render(request, 'user_auth/signup.html')


from cart.models import Transaction

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
            try:
                with transaction.atomic():
                    
                    referred_by_id = user_data.get('referrer_id')  

                    user = CustomUser(
                        full_name=user_data['full_name'],
                        email=user_data['email'],
                        phone_number=user_data['phone_number'],
                        referred_by_id=referred_by_id,
                        referral_code=CustomUser.generate_unique_referral_code(),  
                    )
                    user.set_password(user_data['password'])
                    user.save()


                    new_user_wallet, _ = Wallet.objects.get_or_create(user=user)
                    new_user_credit = 100 if referred_by_id else 50
                    new_user_wallet.balance += new_user_credit
                    new_user_wallet.save()

                    Transaction.objects.create(
                        wallet=new_user_wallet,
                        amount=new_user_credit,
                        transaction_type="CREDIT",
                        reason="Signup bonus via referral" if referred_by_id else "Signup bonus"
                    )

                    # ✅ Referrer gets ₹50
                    if referred_by_id:
                        referrer = CustomUser.objects.get(id=referred_by_id)
                        referrer_wallet, _ = Wallet.objects.get_or_create(user=referrer)
                        referrer_wallet.balance += 50
                        referrer_wallet.save()

                        Transaction.objects.create(
                            wallet=referrer_wallet,
                            amount=50,
                            transaction_type="CREDIT",
                            reason=f"Referral bonus for inviting {user.full_name}"
                        )

                    request.session.flush()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, f"Account created successfully! ₹{new_user_credit} has been added to your wallet.")
                    return redirect('user_login')

            except Exception as e:
                messages.error(request, f"Something went wrong: {str(e)}")
                return redirect('user_signup')
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

@never_cache
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

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils import timezone
from .models import CustomUser
from .utils import is_strong_password

@never_cache
def reset_password(request):
    reset_data = request.session.get('reset_data')

    if not reset_data or not reset_data.get('is_password_reset'):
        messages.error(request, "Your reset session has expired. Please try again.")
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')

        if not is_strong_password(new_password):
            messages.error(request, "Password must be strong: min 8 characters, include uppercase, lowercase, number, special character, and avoid sequences like 123 or 000.")
            return redirect('reset_password')

        try:
            user = CustomUser.objects.get(email=reset_data['email'])
            user.set_password(new_password)
            user.save()

            del request.session['reset_data']
            messages.success(request, "Password reset successful. Please log in.")
            return redirect('user_login')
        except CustomUser.DoesNotExist:
            messages.error(request, "No account found for this email.")
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
    
    # if not request.user.is_authenticated:
    #     print("User is not authenticated, redirecting to login.")
    #     return redirect('user_login') 
    
 
    
    print("User is authenticated, rendering home.")
    

    new_products = Products.objects.filter(is_active=True,
        brand__is_active=True,
        brand__is_listed=True,
        category__is_active=True,
        category__is_listed=True,
                                           )[:8]  
    lowest_price_products = Products.objects.filter(is_active=True , 
        brand__is_active=True,
        brand__is_listed=True,
        category__is_active=True,
        category__is_listed=True,) \
        .annotate(min_price=Min('variants__variant_price')) \
        .order_by('min_price') 
    categories = Category.objects.filter(is_active=True)  
    banners = Banner.objects.filter(is_active=True, is_listed=True).order_by('-created_at')
    

    context = {
        'user': request.user,
        'new_products': new_products [:4],
        'categories': categories,
        'lowest_price_products' : lowest_price_products[:5],
        'banners': banners
    }

    return render(request, 'user_auth/home.html', context)


@never_cache
@block_superuser_navigation
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



from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Optional: Save to DB or send email
        send_mail(
            subject=f'Contact Form - {name}',
            message=message,
            from_email=email,
            recipient_list=['hrihrnofficial@gmail.com'],  
            fail_silently=False,
        )

        messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        return redirect('home')  # or 'contact' if you have a dedicated page

    return render(request, 'home.html')  # Optional if you want separate contact page
