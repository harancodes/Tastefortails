from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import reverse

class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.is_blocked and not request.user.is_superuser:  # ✅ Check is_blocked
                logout(request)
                return redirect(reverse('authentication:login'))  # Or use your custom blocked page

        response = self.get_response(request)
        return response
