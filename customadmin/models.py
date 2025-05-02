# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from authentication.models import CustomUser
# from product.models import  Products,ProductImage, Category, Brand

# @admin.register(CustomUser)
# class CustomUserAdmin(UserAdmin):
#     model = CustomUser

#     list_display = ('email', 'full_name', 'is_staff', 'is_superuser', 'is_blocked', 'profile_complete')
#     search_fields = ('email', 'full_name')
#     ordering = ('email',)
#     fieldsets = (
#         (None, {'fields': ('email', 'password')}),
#         ('Personal info', {'fields': ('full_name', 'phone_number', 'alternate_phone_number', 'dob', 'profile_image')}),
#         ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_blocked', 'groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login', 'date_joined')}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser')}
#         ),
#     )

from django.db import models
from django.utils.safestring import mark_safe
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField

class Banner(models.Model):

    name = models.CharField(max_length=200 ,unique=True, null=False )
    created_at = models.DateTimeField(auto_now_add=True)
    image = CloudinaryField('image')
    updateed_at = models.DateTimeField(auto_now = True)
    is_active = models.BooleanField(default=True)
    is_listed = models.BooleanField(default = True)




    class Meta:
        ordering = ['-created_at']

