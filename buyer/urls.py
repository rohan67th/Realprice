from django.urls import path
from . import views
from . import views_pages
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    # ── New server-rendered buyer pages ──
    path('', views_pages.buyer_landing_view, name='buyer_landing'),
    path('listings/<str:mode>/', views_pages.buyer_listings_view, name='buyer_listings'),
    path('saved/', views_pages.buyer_saved_view, name='buyer_saved'),
    path('saved/toggle/<int:pk>/', views_pages.buyer_saved_toggle_view, name='buyer_saved_toggle'),
    path('tours/', views_pages.buyer_tours_view, name='buyer_tours'),
    path('tours/request/<int:pk>/', views_pages.buyer_tour_request_view, name='buyer_tour_request'),
    path('chat/', views_pages.buyer_chat_view, name='buyer_chat'),
    path('property/<int:pk>/', views_pages.buyer_property_detail_view, name='buyer_property_detail'),
    path('interest-action/<int:pk>/', views_pages.buyer_interest_view, name='buyer_interest'),

    # ── Existing buyer routes (unchanged) ──
    # buyer_login removed — unified into app 'login' URL
    path('buyer_registration/', views.buyer_registration, name='buyer_registration'),
    path('buyer_profile/<int:user_id>/', views.buyer_profile, name='buyer_profile'),
    path('seller_logout/', views.seller_logout, name='seller_logout'),
    path('edit_profile_buyer/<int:user_id>/', views.edit_profile_buyer, name='edit_profile_buyer'),
    # Legacy landing URL — redirects to new buyer_landing
    path('buyer_landing/', views_pages.buyer_landing_view, name='buyer_landing_legacy'),
    path('<int:buyer_id>/property/<int:pk>/', views.property_detail_buyer, name='property_detail_buyer'),
    path('interest/<int:property_id>/', views.show_interest, name='show_interest'),

    path('predict-price/', views.price_prediction_view, name='predict_price'),
    path('price-prediction/', views.price_prediction_page, name='price_prediction_page'),

    path('<int:buyer_id>/property/<int:property_id>/schedule/', views.schedule_visit, name='schedule_visit'),

    path('visit-success/', views.visit_success, name='visit_success'),

    # notifications
    path('<int:buyer_id>/notifications/', views.buyer_notifications, name='buyer_notifications'),
    path('visit/<int:visit_id>/confirm-reschedule/', views.buyer_confirm_reschedule, name='buyer_confirm_reschedule'),
    path('visit/<int:visit_id>/cancel/', views.buyer_cancel_visit, name='buyer_cancel_visit'),

    # Messaging API proxy endpoints
    path('messages/send/', views.send_message, name='buyer_send_message'),
    path('messages/<int:visit_id>/', views.get_messages, name='buyer_get_messages'),

    # chat (legacy per-visit chat)
    path('<int:visit_id>/<str:sender_type>/<int:sender_id>/', views.chat_view, name='chat'),

    # complaints
    path('property/<int:property_id>/complaint/<int:buyer_id>/', views.submit_complaint, name='submit_complaint'),
    path('<int:buyer_id>/complaints/', views.buyer_complaints, name='buyer_complaints'),

    # Rent
    path('rent/property/<int:property_id>/send/<int:buyer_id>/', views.send_rent_request, name='send_rent_request'),

    # Forget password
    path('forgot-password/', views.forget_password_buyer, name='forgot-password-buyer'),
    path('password-reset-sent/<str:reset_id>/', views.password_reset_sent_buyer, name='password-reset-sent-buyer'),
    path('reset-password/<str:reset_id>/', views.reset_password_buyer, name='reset-password-buyer'),

    # price prediction 10 years
    path('predict/price/<int:property_id>/', views.predict_future_price_view, name='predict_future_price'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)