from django.test import TestCase

# @never_cache
# def verify_otp(request):
#     if request.method == 'POST':
#         entered_otp = request.POST.get('otp')
#         user_data = request.session.get('user_data')

#         if not user_data:
#             messages.error(request, "Session expired. Please sign up again.")
#             return redirect('user_signup')

#         otp = user_data.get('otp')
#         otp_created_at = datetime.fromisoformat(user_data.get('otp_created_at'))

#         # OTP Expiry
#         if timezone.now() > otp_created_at + timedelta(minutes=2):
#             messages.error(request, "OTP has expired. Please request a new one.")
#             return redirect('resend_otp')

#         if entered_otp == otp:
#             user = CustomUser.objects.create_user(
#                 full_name=user_data['full_name'],
#                 email=user_data['email'],
#                 password=user_data['password'],
#                 phone_number=user_data['phone_number']
#             )
#             request.session.flush()
#             login(request, user, backend='django.contrib.auth.backends.ModelBackend')
#             messages.success(request, "Account created successfully! You are now logged in.")
#             return redirect('home')
#         else:
#             messages.error(request, "Invalid OTP. Please try again.")

#     user_data = request.session.get('user_data')
#     return render(request, 'verify_otp.html', {'user_data': user_data})

