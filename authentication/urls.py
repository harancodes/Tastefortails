from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView 
# from . import context_processors
# from .views import ProductAPI

urlpatterns = [
    path('login/', views.user_login, name='user_login'),
    path('register/', views.user_signup, name='user_signup'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-password/password/verify-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('forgot-password/resend-otp/', views.resend_reset_otp, name='resend_reset_otp'),
    path('forgot-password/reset/', views.reset_password, name='reset_password'),
    path('admin/', views.admin_login, name='admin_login'),
    path('', views.home, name='home'),
    path('logout/', views.user_logout, name="user_logout"),

    # path('product', views.product, name='product')
    # path('product/<int:id>/', views.product_detail_view, name='product_detail_view'),
   

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
