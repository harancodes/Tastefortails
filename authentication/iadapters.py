from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        return reverse('home')  # Or any view name

    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email')

        if not email:
            messages.error(request, "No email received from Google.")
            raise ImmediateHttpResponse(redirect(reverse('user_login')))

        try:
            user = User.objects.get(email=email)

            # BLOCK: If the user is flagged as inactive or blocked
            if not user.is_active or getattr(user, 'is_blocked', False):
                messages.error(request, "Your account is blocked.")
                raise ImmediateHttpResponse(redirect(reverse('user_login')))

            # EXISTING USER (email registered without social account)
            if not sociallogin.is_existing and not user.socialaccount_set.filter(provider='google').exists():
                messages.error(
                    request,
                    "This email is already registered using a password. "
                    "Please log in with your email and password, then connect your Google account from your profile settings."
                )
                raise ImmediateHttpResponse(redirect(reverse('user_login')))

        except User.DoesNotExist:
            # Allow signup if you want; block if not
            pass
