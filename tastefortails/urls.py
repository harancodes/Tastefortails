"""
URL configuration for tastefortails project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from customadmin.views import admin_login  

urlpatterns = [
    # path('admin/', admin.site.urls), 
    path('', include('authentication.urls')),
    # path('auth/', include('social_django.urls', namespace='social')), 
    path('customadmin/', include('customadmin.urls')),
    path('accounts/', include('allauth.urls')),
    path('products/', include('product.urls', namespace='product')),
    path('admin-login/', admin_login, name='admin_login'), 
    path('cart/', include('cart.urls', namespace='cart')) ,
    path('wishlist/', include('wishlist.urls'), name='wishlist'),
    path('user_profile/', include('user_profile.urls'), name='user_profile')




] 
