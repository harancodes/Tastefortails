from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from authentication.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = ('email', 'full_name', 'is_staff', 'is_superuser', 'is_blocked', 'profile_complete')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone_number', 'alternate_phone_number', 'dob', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_blocked', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser')}
        ),
    )
from product.models import Category, Brand, Products, Variant, ProductImage, Review

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'category_image')
    search_fields = ('name',)
    list_filter = ('is_active',)
    actions = ['soft_delete_categories']
    
    def soft_delete_categories(self, request, queryset):
        queryset.update(deleted_at=timezone.now())
    soft_delete_categories.short_description = "Soft delete selected categories"

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'is_active', 'created_at')
    search_fields = ('name', 'category__name', 'brand__name')
    list_filter = ('category', 'brand', 'is_active')
    actions = ['soft_delete_products']
    
    def soft_delete_products(self, request, queryset):
        queryset.update(deleted_at=timezone.now())
    soft_delete_products.short_description = "Soft delete selected products"

class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary',)

admin.site.register(Category, CategoryAdmin)
admin.site.register(Brand)
admin.site.register(Products, ProductAdmin)
admin.site.register(Variant)
admin.site.register(ProductImage, ProductImageAdmin)
admin.site.register(Review)


