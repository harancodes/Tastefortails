# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django import forms
# from .models import CustomUser


# # Custom Forms for Admin
# class CustomUserCreationForm(UserCreationForm):
#     class Meta:
#         model = CustomUser
#         fields = ('email', 'full_name')


# class CustomUserChangeForm(UserChangeForm):
#     class Meta:
#         model = CustomUser
#         fields = ('email', 'full_name', 'is_active', 'is_staff', 'is_superuser')


# # Custom Admin
# class CustomUserAdmin(BaseUserAdmin):
#     add_form = CustomUserCreationForm
#     form = CustomUserChangeForm
#     model = CustomUser

#     list_display = ('email', 'full_name', 'is_staff', 'is_active')
#     list_filter = ('is_staff', 'is_active', 'is_superuser')

#     fieldsets = (
#         (None, {'fields': ('email', 'password')}),
#         ('Personal info', {'fields': ('full_name', 'phone_number', 'dob', 'profile_image')}),
#         ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login',)}),
#     )

#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'full_name', 'password1', 'password2', 'is_staff', 'is_active')}
#         ),
#     )

#     search_fields = ('email', 'full_name')
#     ordering = ('email',)


# admin.site.register(CustomUser, CustomUserAdmin)



# lass CustomUserAdmin(UserAdmin):
#     model = CustomUser
#     list_display = ['email', 'full_name', 'is_staff', 'is_active']
#     search_fields = ['email', 'full_name']
#     ordering = ['email']
    
#     fieldsets = UserAdmin.fieldsets + (
#         (None, {'fields': ('email', 'full_name', 'phone_number', 'dob', 'profile_image')}),
#     )
#     add_fieldsets = UserAdmin.add_fieldsets + (
#         (None, {'fields': ('email', 'full_name', 'phone_number', 'dob', 'profile_image')}),
#     )

# admin.site.register(CustomUser, CustomUserAdmin)



from django.contrib import admin


