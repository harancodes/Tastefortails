import random
import string
from django.core.mail import send_mail
from django.conf import settings

def send_otp(email):
    otp = ''.join(random.choices(string.digits, k=6))  

    # Email content
    subject = 'Taste for Tails- Your OTP Code'
    message = f"This is your OTP code from Taste for tails: {otp}. It is valid for 2 minutes."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    
    send_mail(subject, message, from_email, recipient_list)

    
    return otp

import re
from django.contrib.auth.password_validation import CommonPasswordValidator


def is_strong_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return "Password must include at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must include at least one lowercase letter."
    if not re.search(r'\d', password):
        return "Password must include at least one digit."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/]', password):
        return "Password must include at least one special character."
    if re.search(r'(\d)\1{2,}', password):
        return "Password cannot contain repeated numbers like 000 or 111."
    if re.search(r'(012|123|234|345|456|567|678|789)', password):
        return "Password cannot contain sequential digits like 123456."
    validator = CommonPasswordValidator()
    try:
        validator.validate(password)
    except Exception as e:
        return str(e)
    return None

import re

def is_valid_full_name(name):
    name = name.strip()
    

    if len(name) < 3:
        return "Name must be at least 3 characters long."

    
    if not re.fullmatch(r'[A-Za-z]+(?: [A-Za-z]+)*', name):
        return "Name must contain only letters and spaces (e.g., Hari or Hari Haran)."

    return None




def is_valid_phone_number(number):
    
    if not re.fullmatch(r'\d{10,15}', number):
        return "Enter a valid phone number with 10 to 15 digits."

    if len(set(number)) == 1:
        return "Phone number cannot have all identical digits."


    if number in ['1234567890', '9876543210']:
        return "Enter a valid phone number."

    return None

