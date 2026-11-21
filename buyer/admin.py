from django.contrib import admin
from .models import (
    Buyer, PasswordResetBuyer, BuyerInterest, VisitSchedule,
    Message, Complaint, RentRequest, SavedProperty,
)


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_active')
    search_fields = ('name', 'email')


@admin.register(SavedProperty)
class SavedPropertyAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'property', 'created_at')
    list_filter = ('created_at',)
    raw_id_fields = ('buyer', 'property')


@admin.register(VisitSchedule)
class VisitScheduleAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'property', 'scheduled_date', 'scheduled_time', 'status')
    list_filter = ('status', 'scheduled_date')
    raw_id_fields = ('buyer', 'property')


@admin.register(BuyerInterest)
class BuyerInterestAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'property', 'status', 'timestamp')
    list_filter = ('status',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'property', 'category', 'priority', 'status', 'created_at')
    list_filter = ('category', 'priority', 'status')


@admin.register(RentRequest)
class RentRequestAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'property', 'start_date', 'end_date', 'status')
    list_filter = ('status',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('visit', 'sender_buyer', 'sender_seller', 'timestamp')


@admin.register(PasswordResetBuyer)
class PasswordResetBuyerAdmin(admin.ModelAdmin):
    list_display = ('user', 'reset_id', 'created_when')
