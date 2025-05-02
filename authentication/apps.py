# # authentication/signals.py

# from django.contrib.sites.models import Site
# from allauth.socialaccount.models import SocialApp
# from django.conf import settings
# from decouple import config  # Assuming you're using python-decouple

# def create_social_app(sender, **kwargs):
#     try:
#         # Ensure the site is loaded before working with it
#         site = Site.objects.get(id=settings.SITE_ID)

#         # Check if the Google SocialApp already exists
#         if not SocialApp.objects.filter(provider='google').exists():
#             app = SocialApp.objects.create(
#                 provider='google',
#                 name='Google',
#                 client_id=config("GOOGLE_CLIENT_ID"),  # Use config to load from .env
#                 secret=config("GOOGLE_CLIENT_SECRET"),  # Use config to load from .env
#             )
#             app.sites.add(site)
#     except Exception as e:
#         print(f"Error creating Google SocialApp: {e}")


from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    name = 'authentication'
