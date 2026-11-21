"""
auth_api/serializers.py

DRF serializers for all auth operations:
  - SellerLoginSerializer     → validates CustomUser credentials, returns tokens
  - SellerRegisterSerializer  → validates + creates a new CustomUser (seller)
  - BuyerLoginSerializer      → validates Buyer credentials, returns tokens
  - BuyerRegisterSerializer   → validates + creates a new Buyer
  - AdminLoginSerializer      → validates admin (is_staff) credentials, returns tokens
  - TokenRefreshSerializer    → refreshes an access token, preserving custom claims
"""

import re
from rest_framework import serializers
from django.contrib.auth import authenticate
from app.models import CustomUser
from buyer.models import Buyer


class SellerLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])

        if user is None:
            raise serializers.ValidationError('Invalid username or password.')

        if user.is_blocked:
            raise serializers.ValidationError('Your account has been blocked by the admin.')

        if not user.is_approved and not user.is_staff:
            raise serializers.ValidationError('Your account is pending admin approval.')

        from auth_api.tokens import get_tokens_for_seller
        return get_tokens_for_seller(user)


class SellerRegisterSerializer(serializers.Serializer):
    username         = serializers.CharField(max_length=150)
    email            = serializers.EmailField()
    phone            = serializers.CharField(max_length=15)
    address          = serializers.CharField()
    gender           = serializers.CharField(max_length=10)
    password         = serializers.CharField(write_only=True, min_length=6, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_username(self, value):
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError('Username must contain at least one letter.')
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value

    def validate_phone(self, value):
        if not re.fullmatch(r'^[0-9]{10}$', value):
            raise serializers.ValidationError('Enter a valid 10-digit phone number.')
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        # Enforce strong password: letters + digits + special char
        pwd = data['password']
        if not (re.search(r'[A-Za-z]', pwd) and
                re.search(r'\d', pwd) and
                re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd)):
            raise serializers.ValidationError({
                'password': 'Password must contain letters, numbers, and a special character.'
            })
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        return CustomUser.objects.create_user(**validated_data)


class BuyerLoginSerializer(serializers.Serializer):
    username = serializers.CharField(label='Name')   # Buyer model uses 'name' as identifier
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        try:
            buyer = Buyer.objects.get(name=data['username'])
        except Buyer.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials.')

        if not buyer.check_password(data['password']):
            raise serializers.ValidationError('Invalid credentials.')

        if not buyer.is_active:
            raise serializers.ValidationError('Your account is inactive.')

        from auth_api.tokens import get_tokens_for_buyer
        return get_tokens_for_buyer(buyer)


class BuyerRegisterSerializer(serializers.Serializer):
    name             = serializers.CharField(max_length=100)
    email            = serializers.EmailField()
    phone            = serializers.CharField(max_length=15)
    address          = serializers.CharField()
    gender           = serializers.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    password         = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_email(self, value):
        if Buyer.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        password = validated_data.pop('confirm_password')   # discard
        raw_password = validated_data.pop('password')
        buyer = Buyer(**validated_data)
        buyer.set_password(raw_password)
        buyer.save()
        return buyer


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])

        if user is None or not user.is_staff:
            raise serializers.ValidationError('Invalid admin credentials.')

        from auth_api.tokens import get_tokens_for_seller
        return get_tokens_for_seller(user)   # role='admin' is set inside


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, data):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError

        try:
            old_refresh = RefreshToken(data['refresh'])
            access = old_refresh.access_token

            # Re-propagate all custom claims so role / user_id survive rotation
            for claim in ('user_id', 'role', 'username', 'name', 'email'):
                if claim in old_refresh:
                    access[claim] = old_refresh[claim]

            return {
                'access': str(access),
                'refresh': str(old_refresh),
            }
        except TokenError as exc:
            raise serializers.ValidationError(str(exc))
