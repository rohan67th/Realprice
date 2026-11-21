"""
auth_api/tokens.py

Utilities for generating JWT tokens for both Sellers (Django CustomUser)
and Buyers (custom Buyer model not in Django auth). Also provides helpers
for setting / clearing JWT cookies on HttpResponse objects.
"""

from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_seller(user):
    """
    Generate JWT access + refresh tokens for a Seller or Admin (CustomUser).
    The role is 'admin' if user.is_staff, otherwise 'seller'.
    """
    refresh = RefreshToken()

    role = 'admin' if user.is_staff else 'seller'

    # Embed custom claims into the refresh token
    refresh['user_id'] = user.id
    refresh['role'] = role
    refresh['username'] = user.username

    # Build a linked access token and clone the custom claims
    access = refresh.access_token
    access['user_id'] = user.id
    access['role'] = role
    access['username'] = user.username

    return {
        'refresh': str(refresh),
        'access': str(access),
        'role': role,
        'user_id': user.id,
        'username': user.username,
    }


def get_tokens_for_buyer(buyer):
    """
    Generate JWT access + refresh tokens for a Buyer.
    Buyer does NOT extend Django's AbstractBaseUser, so we build tokens manually.
    """
    refresh = RefreshToken()

    refresh['user_id'] = buyer.id
    refresh['role'] = 'buyer'
    refresh['name'] = buyer.name
    refresh['email'] = buyer.email

    access = refresh.access_token
    access['user_id'] = buyer.id
    access['role'] = 'buyer'
    access['name'] = buyer.name
    access['email'] = buyer.email

    return {
        'refresh': str(refresh),
        'access': str(access),
        'role': 'buyer',
        'user_id': buyer.id,
        'name': buyer.name,
    }


# ──────────────────────────────────────────────
# Cookie helpers
# ──────────────────────────────────────────────

ACCESS_COOKIE_MAX_AGE  = 60 * 60          # 1 hour  (matches ACCESS_TOKEN_LIFETIME)
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60 # 7 days  (matches REFRESH_TOKEN_LIFETIME)


def set_jwt_cookies(response, tokens: dict) -> None:
    """
    Attach JWT tokens as httpOnly cookies to *response*.
    Call this on the response object BEFORE returning it from a view.
    """
    response.set_cookie(
        'access_token',
        tokens['access'],
        max_age=ACCESS_COOKIE_MAX_AGE,
        httponly=True,
        samesite='Lax',
        secure=False,   # ← set True in production (HTTPS)
    )
    response.set_cookie(
        'refresh_token',
        tokens['refresh'],
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        samesite='Lax',
        secure=False,
    )


def clear_jwt_cookies(response) -> None:
    """Remove JWT cookies from *response* (used on logout)."""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
