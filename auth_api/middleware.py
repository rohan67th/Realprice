"""
auth_api/middleware.py

JWTAuthMiddleware — runs on every request.

Reads the 'access_token' cookie, validates it with SimpleJWT, and attaches:
  - request.jwt_role      → 'buyer' | 'seller' | 'admin' | None
  - request.jwt_user_id   → int or None
  - request.current_buyer → Buyer instance (only when role == 'buyer') or None

This allows template-based views to work without touching request.user
(Django session auth for sellers/admins continues to work unchanged).
"""

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialise safe defaults
        request.jwt_role = None
        request.jwt_user_id = None
        request.current_buyer = None

        token = request.COOKIES.get('access_token')

        if token:
            try:
                access = AccessToken(token)  # validates signature + expiry
                request.jwt_role = access.get('role')
                request.jwt_user_id = access.get('user_id')

                # Only load buyer from DB (sellers use request.user via Django auth)
                if request.jwt_role == 'buyer' and request.jwt_user_id:
                    from buyer.models import Buyer
                    try:
                        request.current_buyer = Buyer.objects.get(id=request.jwt_user_id)
                    except Buyer.DoesNotExist:
                        request.current_buyer = None

            except (TokenError, InvalidToken, Exception):
                # Expired / tampered token — silently reset; views/decorators handle redirect
                request.jwt_role = None
                request.jwt_user_id = None
                request.current_buyer = None

        response = self.get_response(request)
        return response
