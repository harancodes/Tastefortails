# from django.db.models.signals import post_migrate
# from django.dispatch import receiver
# from django.conf import settings
# from allauth.socialaccount.models import SocialApp
# from django.contrib.sites.models import Site
# from decouple import config

# @receiver(post_migrate)
# def create_social_app(sender, **kwargs):
#     try:
#         site = Site.objects.get(id=settings.SITE_ID)

#         if not SocialApp.objects.filter(provider='google').exists():
#             app = SocialApp.objects.create(
#                 provider='google',
#                 name='Google',
#                 client_id=config("GOOGLE_CLIENT_ID"),
#                 secret=config("GOOGLE_CLIENT_SECRET"),
#             )
#             app.sites.add(site)
#     except Exception as e:
#         print(f"Error creating Google SocialApp: {e}")

from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(pre_social_login)
def debug_google_login(sender, request, sociallogin, **kwargs):
    logger.info("==== Google OAuth Response ====")
    logger.info(sociallogin.account.extra_data)

