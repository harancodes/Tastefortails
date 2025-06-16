from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, full_name=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, full_name=None, **extra_fields):
        """
        Creates and returns a superuser with the given email, password, and optional full name.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, password, full_name, **extra_fields)


import uuid
import random
from django.utils.crypto import get_random_string

class CustomUser(AbstractUser):
    username = models.CharField(max_length=200 , unique=True , null=True)  
    email = models.EmailField(unique=True)
    password = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(8)]  
    )
    is_blocked = models.BooleanField(default=False)
    profile_complete = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(
        max_length=15, 
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', _('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'))]
    )
    alternate_phone_number = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    # profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    profile_image = CloudinaryField('image', blank=True, null=True)

    referral_code = models.UUIDField(default=uuid.uuid4, null=True, blank=True)

    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = []  

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.referral_code:
            # You can use uuid or generate a friendly code
            self.referral_code = get_random_string(10).upper()
        super().save(*args, **kwargs)



class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="addresses")
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(
        max_length=15,
        null=True,
        validators=[RegexValidator(
            r'^\+?1?\d{9,15}$',
            _('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'))
        ]
    )
    address_line = models.CharField(max_length=255)
    address_type = models.CharField(max_length=50, choices=(('home', 'Home'), ('work', 'Work')), default='home')
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
