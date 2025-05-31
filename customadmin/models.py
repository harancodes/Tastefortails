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


from django.db import models
from django.utils.timezone import now
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

def validate_discount_percentage(value):
    """Ensure the discount percentage is between 0 and 100."""
    if value <= 0 or value > 100:
        raise ValidationError("Discount percentage must be between 0 and 100.")

def validate_min_cart_value(value):
    """Ensure the minimum cart value is a positive number."""
    if value < 0:
        raise ValidationError("Minimum cart value cannot be negative.")

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,  
        validators=[validate_discount_percentage]
    )

    min_cart_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[validate_min_cart_value]  
    )
    start_date = models.DateField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def is_expired(self):
        """Check if the coupon has expired."""
        return self.expiry_date and self.expiry_date <= timezone.now()

    def is_valid(self):
        """Check if the coupon is active and not expired."""
        return self.is_active and not self.is_expired()

    def calculate_discount(self, cart_total):
        """Calculate the discount amount based on the cart total."""
        
        from decimal import Decimal
        
        if isinstance(cart_total, float):
            cart_total = Decimal(str(cart_total))
            
        if cart_total < self.min_cart_value:
            return Decimal('0')  

        discount_amount = (self.discount_percentage / Decimal('100')) * cart_total
        return round(discount_amount, 2)  

    def clean(self):
        """Extra validation before saving."""
        if self.expiry_date and self.expiry_date < timezone.now():
            self.is_active = False  # Automatically deactivate expired coupon
            raise ValidationError("Expiry date cannot be in the past.")


    def __str__(self):
        return f"{self.code} - {self.discount_percentage}%"

class UsedCoupon(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'coupon')  # Ensures a user can use a coupon only once

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code}"
