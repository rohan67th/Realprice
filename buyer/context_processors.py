"""
buyer/context_processors.py

Adds buyer-related context variables to every template.
"""


def buyer_context(request):
    """
    Inject buyer-related variables available to every template:
    - chat_unread: number of unread chat messages (TODO(fastapi): wire to FastAPI)
    - current_buyer: alias for request.current_buyer set by JWTAuthMiddleware
    """
    buyer = getattr(request, 'current_buyer', None)

    # TODO(fastapi): Fetch unread count from the FastAPI chat service
    # e.g. requests.get(f"{CHAT_SERVICE_API_URL}/unread/{buyer.id}") if buyer else 0
    chat_unread = 0

    return {
        'current_buyer': buyer,
        'chat_unread': chat_unread,
    }
