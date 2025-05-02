import random
import string
from django.core.mail import send_mail
from django.conf import settings

def send_otp(email):
    otp = ''.join(random.choices(string.digits, k=6))  # Generate a 6-digit OTP

    # Email content
    subject = 'Taste for Tails- Your OTP Code'
    message = f"This is your OTP code from Taste for tails: {otp}. It is valid for 2 minutes."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    # Send email
    send_mail(subject, message, from_email, recipient_list)

    # Return the OTP for session storage
    return otp
