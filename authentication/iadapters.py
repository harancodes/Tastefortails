from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import resolve_url

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        return resolve_url('/')  # or whatever path you want

    def is_open_for_signup(self, request, sociallogin):
        # Only allow auto-signup if email is provided
        if sociallogin.account.provider == 'google':
            email = sociallogin.account.extra_data.get('email')
            return email is not None
        return super().is_open_for_signup(request, sociallogin)
