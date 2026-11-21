"""
auth_api/views.py

DRF API views for JWT authentication.

All endpoints accept JSON and return JSON.
On successful login they also set httpOnly JWT cookies so that the existing
Django template-based views work seamlessly without JS changes.

Available endpoints (mounted at /auth/ via auth_api/urls.py):
  POST /auth/seller/login/     → SellerLoginAPIView
  POST /auth/seller/register/  → SellerRegisterAPIView
  POST /auth/buyer/login/      → BuyerLoginAPIView
  POST /auth/buyer/register/   → BuyerRegisterAPIView
  POST /auth/admin/login/      → AdminLoginAPIView
  POST /auth/token/refresh/    → TokenRefreshAPIView
  POST /auth/logout/           → LogoutAPIView
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers import (
    SellerLoginSerializer,
    SellerRegisterSerializer,
    BuyerLoginSerializer,
    BuyerRegisterSerializer,
    AdminLoginSerializer,
    TokenRefreshSerializer,
)
from .tokens import set_jwt_cookies, clear_jwt_cookies


class SellerLoginAPIView(APIView):
    """
    POST /auth/seller/login/
    Body: { "username": "...", "password": "..." }
    Returns JWT tokens + sets httpOnly cookies.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SellerLoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            response = Response(data, status=status.HTTP_200_OK)
            set_jwt_cookies(response, data)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerRegisterAPIView(APIView):
    """
    POST /auth/seller/register/
    Body: { "username", "email", "phone", "address", "gender", "password", "confirm_password" }
    Creates a pending-approval seller account.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SellerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Registration successful. Your account is pending admin approval.'},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuyerLoginAPIView(APIView):
    """
    POST /auth/buyer/login/
    Body: { "username": "<buyer name>", "password": "..." }
    Returns JWT tokens + sets httpOnly cookies.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BuyerLoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            response = Response(data, status=status.HTTP_200_OK)
            set_jwt_cookies(response, data)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuyerRegisterAPIView(APIView):
    """
    POST /auth/buyer/register/
    Body: { "name", "email", "phone", "address", "gender", "password", "confirm_password" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BuyerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Registration successful. Please log in.'},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminLoginAPIView(APIView):
    """
    POST /auth/admin/login/
    Body: { "username": "...", "password": "..." }
    Only succeeds for is_staff=True users.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            response = Response(data, status=status.HTTP_200_OK)
            set_jwt_cookies(response, data)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshAPIView(APIView):
    """
    POST /auth/token/refresh/
    Reads refresh token from cookie OR request body.
    Returns a new access token (and rotated refresh token).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Prefer the httpOnly cookie; fall back to request body for API clients
        refresh_token = (
            request.COOKIES.get('refresh_token')
            or request.data.get('refresh')
        )

        if not refresh_token:
            return Response(
                {'error': 'Refresh token not provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        if serializer.is_valid():
            data = serializer.validated_data
            response = Response(data, status=status.HTTP_200_OK)
            set_jwt_cookies(response, data)
            return response
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    """
    POST /auth/logout/
    Clears JWT cookies. Works for all roles.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(
            {'message': 'Logged out successfully.'},
            status=status.HTTP_200_OK,
        )
        clear_jwt_cookies(response)
        return response
