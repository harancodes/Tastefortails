# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from allauth.exceptions import ImmediateHttpResponse
# from django.shortcuts import resolve_url
# from django.contrib.auth import get_user_model
# from django.shortcuts import redirect
# from django.contrib import messages

# User = get_user_model()

# class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
#     def get_login_redirect_url(self, request):
#         return resolve_url('/')  

#     def is_open_for_signup(self, request, sociallogin):
#         if sociallogin.account.provider == 'google':
#             email = sociallogin.account.extra_data.get('email')
#             return email is not None
#         return super().is_open_for_signup(request, sociallogin)

#     def pre_social_login(self, request, sociallogin):
#         email = sociallogin.account.extra_data.get('email')
#         if email:
#             try:
#                 user = User.objects.get(email=email)
#                 if user.is_blocked:
#                     messages.error(request, "This account is blocked. Please contact the team.")
#                     raise ImmediateHttpResponse(redirect('account_login'))
#                 sociallogin.connect(request, user)
#             except User.DoesNotExist:
#                 pass  

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import resolve_url
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        return resolve_url('/')  # Default redirect URL after successful login

    def is_open_for_signup(self, request, sociallogin):
        if sociallogin.account.provider == 'google':
            email = sociallogin.account.extra_data.get('email')
            return email is not None
        return super().is_open_for_signup(request, sociallogin)

    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                if user.is_blocked:
                    # Blocked account: Show message and prevent login
                    messages.error(request, "This account is blocked. Please contact the team.")
                    # Raise ImmediateHttpResponse to stop the flow and redirect to login
                    raise ImmediateHttpResponse(redirect('account_login'))  # Redirect to login page
                # If the account is not blocked, continue the login process
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass  # Continue with the normal signup flow if the user doesn't exist


