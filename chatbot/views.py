import json
import google.generativeai as genai
from openai import OpenAI
import httpx
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from .models import Conversation, ChatMessage


def chat_page(request):
    return render(request, 'chatbot/chat_page.html')


@csrf_exempt
@require_http_methods(["POST"])
def get_api_response(request):
    """
    Proxy view that forwards chatbot requests to the FastAPI microservice.
    Uses the user's JWT access_token cookie for authentication.
    """
    try:
        # 1. Prepare data for FastAPI
        data = json.loads(request.body)
        
        # 2. Get JWT token from cookies or session fallback
        access_token = request.COOKIES.get('access_token')
        
        if not access_token:
            buyer_id = request.session.get('buyer_id')
            if buyer_id:
                try:
                    from buyer.models import Buyer
                    from auth_api.tokens import get_tokens_for_buyer
                    buyer = Buyer.objects.get(id=buyer_id)
                    tokens = get_tokens_for_buyer(buyer)
                    access_token = tokens['access']
                except Exception:
                    pass
            elif hasattr(request, 'current_buyer') and request.current_buyer:
                from auth_api.tokens import get_tokens_for_buyer
                tokens = get_tokens_for_buyer(request.current_buyer)
                access_token = tokens['access']
            elif hasattr(request, 'user') and request.user.is_authenticated:
                from auth_api.tokens import get_tokens_for_seller
                tokens = get_tokens_for_seller(request.user)
                access_token = tokens['access']

        if not access_token:
            return JsonResponse({
                'status': 'error',
                'error_message': 'Please log in to use the chatbot.'
            }, status=401)

        # 3. Call FastAPI microservice
        fastapi_url = "http://127.0.0.1:8001/api/chatbot/message"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                fastapi_url, 
                json=data, 
                headers=headers,
                cookies=request.COOKIES # also pass cookies just in case
            )
            
            # 4. Return the FastAPI response directly to the frontend
            return JsonResponse(response.json(), status=response.status_code)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error_message': 'Invalid JSON format.'}, status=400)
    except httpx.RequestError as e:
        return JsonResponse({'status': 'error', 'error_message': f'Microservice unavailable: {str(e)}'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error_message': str(e)}, status=500)

