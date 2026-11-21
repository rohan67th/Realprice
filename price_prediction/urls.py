"""
URL configuration for price_prediction project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

from buyer.views import send_message, get_messages

urlpatterns = [
    path('admin/', admin.site.urls),
    # JWT Authentication API  (POST /auth/seller/login/ etc.)
    path('auth/', include('auth_api.urls')),
    path('buyer/', include('buyer.urls')),
    path('chatbot/', include('chatbot.urls')),
    # FastAPI Messaging Proxy (matching FastAPI /api/messaging routes)
    path('api/messaging/send', send_message, name='api_messaging_send_no_slash'),
    path('api/messaging/send/', send_message, name='api_messaging_send'),
    path('api/messaging/history/<int:visit_id>', get_messages, name='api_messaging_history_no_slash'),
    path('api/messaging/history/<int:visit_id>/', get_messages, name='api_messaging_history'),
    path('', include('app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    



    
