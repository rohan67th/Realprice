from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from buyer.views import chat_view


urlpatterns = [
    path('',views.landingpage,name='landingpage'),
    path('about/',views.about,name='about'),
    path('register-choice/',views.register_choice,name='register_choice'),
    path('contact/',views.contact,name='contact'),


    #seller
    path('register/',views.seller_register,name='register'),
    path('login/',views.unified_login,name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('seller_profile/<int:user_id>/', views.seller_profile, name='seller_profile'),
    path('forgot-password/', views.forget_password, name='forgot-password'),
    path('password-reset-sent/<str:reset_id>/', views.password_reset_sent, name='password-reset-sent'),
    path('reset-password/<str:reset_id>/', views.reset_password, name='reset-password'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('property_list/<int:seller_id>/', views.property_list, name='property_list'),
    path('add_property/', views.add_property, name='add_property'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('seller_properties/', views.seller_property_list, name='seller_property_list'),
    path('seller_properties/edit/<int:id>/', views.seller_edit_property, name='seller_edit_property'),
    path('seller_properties/delete/<int:id>/', views.seller_delete_property, name='seller_delete_property'),
    path('seller_pending-properties/', views.seller_pending_properties, name='seller_pending_properties'),






    #admin
    # admin_login removed — unified into 'login'
    path('admin_login/',views.unified_login,name='admin_login'),  # backward compat redirect
    path('dashboard/',views.dashboard,name='admin_dashboard'),
    path('admin_logout/',views.admin_logout,name='admin_logout'),
    path('approve_seller/<int:seller_id>/', views.approve_seller, name='approve_seller'),
    path('decline_seller/<int:seller_id>/', views.decline_seller, name='decline_seller'),
    path('seller_list/', views.seller_list, name='seller_list'),
    path('buyer_list/', views.buyer_list, name='buyer_list'),
    path('toggle-block/<int:user_id>/', views.toggle_block_user, name='toggle_block_user'),
    path('property/<int:property_id>/approve/', views.approve_property, name='approve_property'),
    path('property/<int:property_id>/decline/', views.decline_property, name='decline_property'),
    path('properties/', views.admin_property_list, name='admin_property_list'),
    path('admin_complaints/', views.complaints_admin_view, name='admin_complaints'),
    path('property/delete/<int:property_id>/', views.delete_property, name='delete_property'),
    path('delete-buyer/<int:buyer_id>/', views.delete_buyer, name='delete_buyer'),
    path('delete-seller/<int:seller_id>/', views.delete_seller, name='delete_seller'),

    # new admin pages
    path('seller-approvals/', views.seller_approvals, name='seller_approvals'),
    path('seller-approval-action/<int:seller_id>/', views.seller_approval_action, name='seller_approval_action'),
    path('seller-document/<int:seller_id>/', views.seller_document_view, name='seller_document_view'),
    path('seller-resubmit/<int:seller_id>/', views.seller_resubmit_application, name='seller_resubmit'),
    path('listing-approvals/', views.listing_approvals, name='listing_approvals'),
    path('listing-approval-action/<int:property_id>/', views.listing_approval_action, name='listing_approval_action'),
    path('property-review-data/<int:property_id>/', views.property_review_data, name='property_review_data'),
    path('analytics/', views.admin_analytics, name='admin_analytics'),
    path('chatbot-logs/', views.chatbot_logs, name='chatbot_logs'),
    path('activity-logs/', views.activity_logs, name='activity_logs'),

    #schedule visit
    path('seller/<int:seller_id>/visit-requests/', views.visit_requests, name='visit_requests'),
    path('seller/visit/<int:visit_id>/approve/', views.approve_visit, name='approve_visit'),
    path('seller/visit/<int:visit_id>/decline/', views.decline_visit, name='decline_visit'),
    path('seller/visit/<int:visit_id>/reschedule/', views.seller_reschedule_visit, name='seller_reschedule_visit'),
    path('seller/visit/<int:visit_id>/complete/', views.seller_complete_visit, name='seller_complete_visit'),




    #rent request
    path('seller/<int:seller_id>/rent-requests/', views.pending_rent_requests, name='seller_rent_requests'),
    # path('rent/approve/<int:request_id>/', views.approve_rent_request, name='approve_rent_request'),
    # path('rent/decline/<int:request_id>/', views.decline_rent_request, name='decline_rent_request'), 
    # path('seller/<int:seller_id>/rent-requests/', views.rent_requests, name='rent_requests'),
    path('rent-request/<int:request_id>/approve/', views.approve_rent_request, name='approve_rent_request'),
    path('rent-request/<int:request_id>/decline/', views.decline_rent_request, name='decline_rent_request'),


    

    path('chat/<int:visit_id>/<str:sender_type>/<int:sender_id>/', views.chat_with_buyer, name='seller_chat'),

    # Modular split seller pages
    path('seller_profile/<int:user_id>/properties/', views.seller_properties_page, name='seller_properties_page'),
    path('seller_profile/<int:user_id>/visits/', views.seller_visits_page, name='seller_visits_page'),
    path('seller_profile/<int:user_id>/visits/create/', views.seller_create_visit, name='seller_create_visit'),
    path('seller_profile/<int:user_id>/calendar/', views.seller_calendar_page, name='seller_calendar_page'),
    path('seller_profile/<int:user_id>/chats/', views.seller_chats_page, name='seller_chats_page'),
    path('seller_profile/<int:user_id>/notifications/', views.seller_notifications_page, name='seller_notifications_page'),
    path('seller_profile/<int:user_id>/rent-requests/', views.seller_rent_requests_page, name='seller_rent_requests_page'),
    path('seller_profile/<int:user_id>/billing/', views.seller_billing_page, name='seller_billing_page'),
    path('seller_profile/<int:user_id>/analytics/', views.seller_analytics_page, name='seller_analytics_page'),
    path('seller_profile/<int:user_id>/profile-details/', views.seller_profile_details_page, name='seller_profile_details_page'),
    path('seller_profile/<int:user_id>/settings/', views.seller_settings_page, name='seller_settings_page'),
    path('seller_profile/<int:user_id>/empty-states/', views.seller_empty_states_page, name='seller_empty_states_page'),
    path('seller_profile/<int:user_id>/loading-states/', views.seller_loading_states_page, name='seller_loading_states_page'),





] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)