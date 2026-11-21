"""
auth_api/decorators.py

View decorators that enforce JWT-based role access on Django template views.

Usage:
    @buyer_jwt_required
    def my_buyer_view(request, ...):
        buyer = request.current_buyer   # guaranteed to be set

    @seller_jwt_required
    def my_seller_view(request, ...):
        ...  # request.user is set by Django session auth

    @admin_jwt_required
    def my_admin_view(request, ...):
        ...
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


# ──────────────────────────────────────────────
# Buyer
# ──────────────────────────────────────────────

def buyer_jwt_required(view_func):
    """
    Ensures the request carries a valid buyer JWT.
    On failure, clears stale cookies and redirects to login.
    On success, request.current_buyer is guaranteed to be a Buyer instance.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.jwt_role != 'buyer' or not request.current_buyer:
            messages.error(request, 'Please log in as a buyer to continue.')
            response = redirect('login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response
        return view_func(request, *args, **kwargs)
    return _wrapped


# ──────────────────────────────────────────────
# Seller
# ──────────────────────────────────────────────

def seller_jwt_required(view_func):
    """
    Ensures the request carries a valid seller (or admin) JWT AND that
    Django's session-based request.user is authenticated.
    (Both are set simultaneously during seller_login.)
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        is_jwt_seller   = request.jwt_role in ('seller', 'admin')
        is_django_authed = request.user.is_authenticated

        if not (is_jwt_seller and is_django_authed):
            messages.error(request, 'Please log in as a seller to continue.')
            response = redirect('login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response
        return view_func(request, *args, **kwargs)
    return _wrapped


# ──────────────────────────────────────────────
# Seller (with ownership check)
# ──────────────────────────────────────────────

def seller_required(view_func):
    """
    Ensures the request carries a valid seller (or admin) JWT AND that
    Django's session-based request.user is authenticated.

    For views with ``user_id`` or ``seller_id`` kwargs, also verifies
    the logged-in user owns that resource (prevents horizontal access).
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        is_jwt_seller = request.jwt_role in ('seller', 'admin')
        is_django_authed = request.user.is_authenticated

        if not (is_jwt_seller and is_django_authed):
            messages.error(request, 'Please log in as a seller to continue.')
            response = redirect('login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response

        # Ownership: if the view receives a user_id or seller_id,
        # the logged-in seller must match (prevents horizontal access).
        owner_id = kwargs.get('user_id') or kwargs.get('seller_id')
        if owner_id is not None and request.user.id != int(owner_id):
            from django.http import Http404
            raise Http404

        return view_func(request, *args, **kwargs)
    return _wrapped


# ──────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────

def admin_jwt_required(view_func):
    """
    Ensures the request carries an admin JWT AND that request.user.is_staff is True.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        is_jwt_admin     = request.jwt_role == 'admin'
        is_django_staff  = request.user.is_authenticated and request.user.is_staff

        if not (is_jwt_admin and is_django_staff):
            messages.error(request, 'Admin access required. Please log in.')
            response = redirect('login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response
        return view_func(request, *args, **kwargs)
    return _wrapped
