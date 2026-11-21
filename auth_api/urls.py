"""
auth_api/urls.py  —  All JWT auth API endpoints are mounted here.
Include this in the root urls.py as: path('auth/', include('auth_api.urls'))
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Seller ──────────────────────────────────────────
    path('seller/login/',    views.SellerLoginAPIView.as_view(),    name='api_seller_login'),
    path('seller/register/', views.SellerRegisterAPIView.as_view(), name='api_seller_register'),

    # ── Buyer ────────────────────────────────────────────
    path('buyer/login/',    views.BuyerLoginAPIView.as_view(),    name='api_buyer_login'),
    path('buyer/register/', views.BuyerRegisterAPIView.as_view(), name='api_buyer_register'),

    # ── Admin ────────────────────────────────────────────
    path('admin/login/', views.AdminLoginAPIView.as_view(), name='api_admin_login'),

    # ── Token management ─────────────────────────────────
    path('token/refresh/', views.TokenRefreshAPIView.as_view(), name='api_token_refresh'),
    path('logout/',        views.LogoutAPIView.as_view(),        name='api_logout'),
]
