"""
buyer/views_pages.py

Server-rendered buyer page views.  All views use @buyer_jwt_required
(from auth_api.decorators) which guarantees request.current_buyer is set.
"""
from datetime import timedelta
import json
import urllib.request
from decimal import Decimal

from django.http import Http404, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.cache import cache
from django.contrib import messages
from django.db.models import Q, F

from auth_api.decorators import buyer_jwt_required
from app.models import Property
from .models import Buyer, SavedProperty, VisitSchedule, BuyerInterest
from .search import apply_search
from .templatetags.buyer_tags import _type_category


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def _listable_qs():
    """Base queryset: approved + available properties, eager-load seller."""
    return (
        Property.objects
        .filter(approval_status='approved', status='Available')
        .select_related('seller')
    )


def _saved_ids(buyer):
    """Return a set of property IDs that this buyer has saved."""
    return set(
        SavedProperty.objects
        .filter(buyer=buyer)
        .values_list('property_id', flat=True)
    )


def _next_tour(buyer):
    """Return the next upcoming approved tour for this buyer, or None."""
    return (
        VisitSchedule.objects
        .filter(buyer=buyer, status='approved', scheduled_date__gte=timezone.now().date())
        .select_related('property')
        .order_by('scheduled_date', 'scheduled_time')
        .first()
    )


def _upcoming_tours_count(buyer):
    """Count upcoming approved tours."""
    return VisitSchedule.objects.filter(
        buyer=buyer, status='approved',
        scheduled_date__gte=timezone.now().date(),
    ).count()


# ────────────────────────────────────────────────────────────
# buyer_landing — /buyer/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
def buyer_landing_view(request):
    buyer = request.current_buyer
    qs = _listable_qs()

    featured_sale = qs.filter(listing_type='sale').order_by('-posted_at')[:6]
    featured_rent = qs.filter(listing_type='rent').order_by('-posted_at')[:6]

    saved = _saved_ids(buyer)
    saved_count = len(saved) if saved else SavedProperty.objects.filter(buyer=buyer).count()

    # Count saved properties that had a price drop
    saved_drop_count = 0
    if saved:
        drop_qs = Property.objects.filter(
            id__in=saved,
            previous_price__isnull=False,
        )
        for p in drop_qs:
            if p.price < p.previous_price:
                saved_drop_count += 1

    next_tour = _next_tour(buyer)
    tours_count = _upcoming_tours_count(buyer)

    # New matches this week (properties posted in last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    new_matches = qs.filter(posted_at__gte=week_ago).count()

    recently_viewed = request.session.get('recently_viewed', [])
    recently_viewed_count = len(recently_viewed)

    return render(request, 'buyer/buyer_landing.html', {
        'buyer': buyer,
        'featured_sale': featured_sale,
        'featured_rent': featured_rent,
        'saved_ids': saved,
        'saved_count': saved_count,
        'saved_drop_count': saved_drop_count,
        'next_tour': next_tour,
        'tours_count': tours_count,
        'new_matches': new_matches,
        'recently_viewed_count': recently_viewed_count,
    })


# ────────────────────────────────────────────────────────────
# buyer_listings — /buyer/listings/<mode>/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
def buyer_listings_view(request, mode):
    if mode not in ('buy', 'rent'):
        raise Http404

    buyer = request.current_buyer
    listing_type = 'rent' if mode == 'rent' else 'sale'
    qs = _listable_qs().filter(listing_type=listing_type)

    # ── Filters from GET params ──
    prop_type = request.GET.get('type')       # house | apartment
    sort = request.GET.get('sort')            # new
    drops = request.GET.get('drops')          # 1
    q = request.GET.get('q', '').strip()

    if prop_type == 'house':
        qs = qs.filter(property_type__in=['House', 'Land'])
    elif prop_type == 'apartment':
        qs = qs.filter(property_type__in=['Apartment', 'Commercial'])

    if sort == 'new':
        cutoff = timezone.now() - timedelta(days=14)
        qs = qs.filter(posted_at__gte=cutoff)

    if drops == '1':
        qs = qs.filter(
            previous_price__isnull=False,
            price__lt=F('previous_price'),
        )

    # ── Smart search ──
    if q:
        qs, detected_mode = apply_search(q, qs, mode)
        if detected_mode != mode:
            # Redirect to the correct mode with the same query
            from django.urls import reverse
            url = reverse('buyer_listings', args=[detected_mode])
            params = request.GET.copy()
            return redirect(f"{url}?{params.urlencode()}")

    # ── Ordering ──
    qs = qs.order_by('-posted_at')

    # ── Pagination ──
    paginator = Paginator(qs, 12)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    # Build query string without 'page' for pagination links
    get_params = request.GET.copy()
    get_params.pop('page', None)
    query_string = get_params.urlencode()

    saved = _saved_ids(buyer)

    # Active filter for the quick-filter bar
    active_filter = 'all'
    if prop_type == 'house':
        active_filter = 'house'
    elif prop_type == 'apartment':
        active_filter = 'apartment'
    elif sort == 'new':
        active_filter = 'new'
    elif drops == '1':
        active_filter = 'drops'

    return render(request, 'buyer/buyer_listings.html', {
        'buyer': buyer,
        'mode': mode,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'saved_ids': saved,
        'active_filter': active_filter,
        'query_string': query_string,
        'search_q': q,
    })


# ────────────────────────────────────────────────────────────
# buyer_saved — /buyer/saved/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
def buyer_saved_view(request):
    buyer = request.current_buyer
    filter_mode = request.GET.get('mode', 'all')  # all | buy | rent

    qs = (
        SavedProperty.objects
        .filter(buyer=buyer)
        .select_related('property', 'property__seller')
        .order_by('-created_at')
    )

    if filter_mode == 'buy':
        qs = qs.filter(property__listing_type='sale')
    elif filter_mode == 'rent':
        qs = qs.filter(property__listing_type='rent')

    properties = [sp.property for sp in qs]
    saved_ids = {p.id for p in properties}

    return render(request, 'buyer/buyer_saved.html', {
        'buyer': buyer,
        'properties': properties,
        'saved_ids': saved_ids,
        'filter_mode': filter_mode,
    })


# ────────────────────────────────────────────────────────────
# buyer_saved_toggle — POST /buyer/saved/toggle/<pk>/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
@require_POST
def buyer_saved_toggle_view(request, pk):
    buyer = request.current_buyer
    prop = get_object_or_404(Property, pk=pk)

    obj, created = SavedProperty.objects.get_or_create(buyer=buyer, property=prop)
    if not created:
        obj.delete()
        is_saved = False
    else:
        is_saved = True

    count = SavedProperty.objects.filter(buyer=buyer).count()
    return JsonResponse({'saved': is_saved, 'count': count})


# ────────────────────────────────────────────────────────────
# buyer_tours — /buyer/tours/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
def buyer_tours_view(request):
    buyer = request.current_buyer
    today = timezone.now().date()

    upcoming = (
        VisitSchedule.objects
        .filter(buyer=buyer, scheduled_date__gte=today)
        .select_related('property', 'property__seller')
        .order_by('scheduled_date', 'scheduled_time')
    )
    past = (
        VisitSchedule.objects
        .filter(buyer=buyer, scheduled_date__lt=today)
        .select_related('property', 'property__seller')
        .order_by('-scheduled_date', '-scheduled_time')
    )

    return render(request, 'buyer/buyer_tours.html', {
        'buyer': buyer,
        'upcoming': upcoming,
        'past': past,
    })


# ────────────────────────────────────────────────────────────
# buyer_chat — /buyer/chat/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
def buyer_chat_view(request):
    buyer = request.current_buyer

    from django.conf import settings
    chat_ws_url = getattr(settings, 'CHAT_SERVICE_WS_URL', '')
    chat_api_url = getattr(settings, 'CHAT_SERVICE_API_URL', '')

    import json, urllib.parse
    # Query approved and completed visits for this buyer
    visits = (
        VisitSchedule.objects.filter(
            buyer=buyer,
            status__in=[VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED]
        )
        .select_related('property', 'property__seller')
        .order_by('-scheduled_date', '-scheduled_time')
    )

    conversations = []
    for v in visits:
        last_msg = v.chat_messages.order_by('-timestamp').first()
        seller = v.property.seller if v.property else None
        seller_name = seller.username if seller and getattr(seller, 'username', None) else 'Seller'
        avatar = ''
        if seller and getattr(seller, 'profile_pic', None):
            try:
                avatar = seller.profile_pic.url
            except Exception:
                avatar = ''
        if not avatar:
            avatar = f"https://ui-avatars.com/api/?name={urllib.parse.quote(seller_name)}&background=6366f1&color=fff"

        time_str = ''
        if last_msg:
            time_str = last_msg.timestamp.strftime('%I:%M %p')
        elif v.scheduled_time:
            time_str = v.scheduled_time.strftime('%I:%M %p')

        conversations.append({
            'visit_id': v.id,
            'id': v.id,
            'seller_id': seller.id if seller else None,
            'seller_name': seller_name,
            'name': seller_name,
            'property_id': v.property_id,
            'property': f"{v.property.property_type} - {v.property.location}" if v.property else '',
            'property_title': f"{v.property.property_type} - {v.property.location}" if v.property else '',
            'avatar': avatar,
            'last': last_msg.content if last_msg else 'No messages yet',
            'time': time_str,
            'status': v.status,
            'unread': 0,
        })

    initial_visit_id = request.GET.get('visit_id', '')
    if not initial_visit_id and request.GET.get('property'):
        prop_id = request.GET.get('property')
        matching = next((c for c in conversations if str(c['property_id']) == str(prop_id)), None)
        if matching:
            initial_visit_id = str(matching['visit_id'])

    return render(request, 'buyer/buyer_chat.html', {
        'buyer': buyer,
        'chat_ws_url': chat_ws_url,
        'chat_api_url': chat_api_url or '/api/messaging',
        'conversations_json': json.dumps(conversations),
        'initial_visit_id': initial_visit_id,
    })


# ────────────────────────────────────────────────────────────
# AI Price Estimate Helper
# ────────────────────────────────────────────────────────────

def get_ai_price_estimate(property_obj):
    """
    Returns AI price estimate dict for sale properties using FastAPI ML service:
    {
        'estimated_price': float,
        'listed_price': float,
        'verdict': str ('Fairly priced', 'Below estimate', 'Above estimate'),
        'verdict_class': str (literal Tailwind classes),
        'bar_pos': int (percentage 10-90 for horizontal meter),
        'diff_pct': float,
    }
    Cached for 1 hour per property id + posted_at timestamp.
    Silently returns None on any failure.
    """
    if getattr(property_obj, 'listing_type', 'sale') != 'sale':
        return None

    cache_key = f"rf_ai_est_{property_obj.id}_{property_obj.posted_at.strftime('%Y%m%d%H%M%S')}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        bedrooms = float(property_obj.bedrooms) if property_obj.bedrooms else 3.0
        ave_rooms = bedrooms + 2.0
        lat = float(property_obj.latitude) if property_obj.latitude else 37.88
        lon = float(property_obj.longitude) if property_obj.longitude else -122.23
        area = float(property_obj.area_sqft) if property_obj.area_sqft else 1800.0
        med_inc = max(2.0, min(15.0, area / 250.0))

        payload = json.dumps({
            "features": [
                med_inc,
                12.0,
                ave_rooms,
                bedrooms,
                1400.0,
                3.0,
                lat,
                lon,
            ]
        }).encode('utf-8')

        req = urllib.request.Request(
            "http://127.0.0.1:8001/api/ml/predict",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('success'):
                raw_pred = float(data.get('predicted_price') or data.get('prediction', 0))
                listed = float(property_obj.price)
                if listed > 0 and raw_pred > 0:
                    diff = listed - raw_pred
                    diff_pct = diff / raw_pred

                    if abs(diff_pct) <= 0.05:
                        verdict = "Fairly priced"
                        verdict_class = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                        bar_pos = 50
                    elif listed < raw_pred:
                        verdict = "Below estimate"
                        verdict_class = "text-blue-400 bg-blue-500/10 border-blue-500/20"
                        bar_pos = max(15, min(45, int(50 + diff_pct * 40)))
                    else:
                        verdict = "Above estimate"
                        verdict_class = "text-amber-400 bg-amber-500/10 border-amber-500/20"
                        bar_pos = max(55, min(85, int(50 + diff_pct * 40)))

                    res = {
                        'estimated_price': raw_pred,
                        'listed_price': listed,
                        'verdict': verdict,
                        'verdict_class': verdict_class,
                        'bar_pos': bar_pos,
                        'diff_pct': round(abs(diff_pct) * 100, 1),
                    }
                    cache.set(cache_key, res, 3600)
                    return res
    except Exception:
        pass
    return None


# ────────────────────────────────────────────────────────────
# property_detail — /property/<pk>/ or /buyer/<buyer_id>/property/<pk>/
# ────────────────────────────────────────────────────────────

def buyer_property_detail_view(request, pk, buyer_id=None):
    prop = get_object_or_404(Property.objects.select_related('seller'), pk=pk)

    # Permission check: Owner and admins can view unlisted
    user = getattr(request, 'user', None)
    is_owner = bool(user and getattr(user, 'is_authenticated', False) and prop.seller_id == getattr(user, 'id', None))
    is_admin = bool(
        getattr(request, 'jwt_role', None) == 'admin'
        or (user and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)))
    )
    is_listable = (prop.approval_status == 'approved' or prop.is_approved) and prop.status == 'Available'

    if not (is_listable or is_owner or is_admin):
        raise Http404("Property not found or not currently available.")

    buyer = getattr(request, 'current_buyer', None)
    if not buyer and buyer_id:
        try:
            buyer = Buyer.objects.get(id=buyer_id)
        except Buyer.DoesNotExist:
            buyer = None

    # Track recently viewed in session (up to 20 IDs, deduplicated, most recent first)
    recent = request.session.get('recently_viewed', [])
    if prop.pk in recent:
        recent.remove(prop.pk)
    recent.insert(0, prop.pk)
    request.session['recently_viewed'] = recent[:20]
    request.session.modified = True

    mode = 'rent' if prop.listing_type == 'rent' else 'buy'

    is_saved = False
    existing_tour = None
    has_interested = False
    saved_ids = set()

    if buyer:
        is_saved = SavedProperty.objects.filter(buyer=buyer, property=prop).exists()
        existing_tour = VisitSchedule.objects.filter(
            buyer=buyer,
            property=prop,
            scheduled_date__gte=timezone.now().date(),
        ).order_by('scheduled_date', 'scheduled_time').first()
        has_interested = BuyerInterest.objects.filter(buyer=buyer, property=prop).exists()
        saved_ids = _saved_ids(buyer)

    # Real gallery images: main_image first, do NOT repeat main_image
    gallery = []
    seen_urls = set()
    for img_field in [prop.main_image, prop.image_1, prop.image_2, prop.image_3]:
        if img_field and hasattr(img_field, 'url'):
            try:
                url = img_field.url
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    gallery.append(url)
            except ValueError:
                pass

    if not gallery:
        gallery = ['https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80']

    # AI price estimate (sale listings only)
    prediction = None
    if prop.listing_type == 'sale':
        prediction = get_ai_price_estimate(prop)

    # Similar properties (up to 3, same listing type, same property type, ±30% price or same location)
    similar_base = _listable_qs().filter(
        listing_type=prop.listing_type,
        property_type=prop.property_type,
    ).exclude(pk=prop.pk)

    price_min = prop.price * Decimal('0.70')
    price_max = prop.price * Decimal('1.30')
    similar_candidates = list(
        similar_base.filter(price__gte=price_min, price__lte=price_max).order_by('-posted_at')[:3]
    )

    if not similar_candidates:
        similar_candidates = list(
            similar_base.filter(location__iexact=prop.location).order_by('-posted_at')[:3]
        )
    if not similar_candidates:
        similar_candidates = list(similar_base.order_by('-posted_at')[:3])

    # Price per sq ft (sale only)
    price_per_sqft = None
    if prop.listing_type == 'sale' and prop.area_sqft and prop.area_sqft > 0:
        price_per_sqft = round(float(prop.price) / float(prop.area_sqft), 2)

    is_new = (timezone.now() - prop.posted_at).days <= 14
    has_price_drop = prop.previous_price is not None and prop.price < prop.previous_price
    tomorrow_date = (timezone.now().date() + timedelta(days=1)).isoformat()

    context = {
        'property': prop,
        'mode': mode,
        'buyer': buyer,
        'current_buyer': buyer,
        'is_saved': is_saved,
        'is_owner': is_owner,
        'is_admin': is_admin,
        'gallery': gallery,
        'similar': similar_candidates,
        'saved_ids': saved_ids,
        'prediction': prediction,
        'existing_tour': existing_tour,
        'has_interested': has_interested,
        'price_per_sqft': price_per_sqft,
        'is_new': is_new,
        'has_price_drop': has_price_drop,
        'tomorrow_date': tomorrow_date,
        'recently_viewed_count': len(recent),
    }
    return render(request, 'property_detail.html', context)


# ────────────────────────────────────────────────────────────
# buyer_tour_request — POST /buyer/tours/request/<pk>/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
@require_POST
def buyer_tour_request_view(request, pk):
    buyer = request.current_buyer
    prop = get_object_or_404(Property, pk=pk)

    scheduled_date_str = request.POST.get('scheduled_date', '').strip()
    scheduled_time_str = request.POST.get('scheduled_time', '').strip()
    message = request.POST.get('message', '').strip()

    if not scheduled_date_str or not scheduled_time_str:
        messages.error(request, 'Please select both a date and time for the tour.')
        return redirect('property_detail', pk=pk)

    try:
        from datetime import datetime
        scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
        scheduled_time = datetime.strptime(scheduled_time_str, '%H:%M').time()
    except ValueError:
        messages.error(request, 'Invalid date or time format.')
        return redirect('property_detail', pk=pk)

    if scheduled_date <= timezone.now().date():
        messages.error(request, 'Tours must be scheduled at least 1 day in advance.')
        return redirect('property_detail', pk=pk)

    # Reject duplicates for the same property, date, and time
    existing = VisitSchedule.objects.filter(
        buyer=buyer,
        property=prop,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        status__in=['pending', 'approved']
    ).exists()

    if existing:
        messages.warning(request, f'You already have a tour scheduled or requested for this property on {scheduled_date.strftime("%b %d, %Y")} at {scheduled_time.strftime("%I:%M %p")}.')
        return redirect('buyer_tours')

    VisitSchedule.objects.create(
        buyer=buyer,
        property=prop,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        message=message,
        status='pending'
    )

    messages.success(request, f'Tour requested for {scheduled_date.strftime("%b %d, %Y")} at {scheduled_time.strftime("%I:%M %p")}! The seller will confirm shortly.')
    return redirect('buyer_tours')


# ────────────────────────────────────────────────────────────
# buyer_interest — POST /buyer/interest/<pk>/
# ────────────────────────────────────────────────────────────

@buyer_jwt_required
@require_POST
def buyer_interest_view(request, pk):
    buyer = request.current_buyer
    prop = get_object_or_404(Property, pk=pk)

    interest, created = BuyerInterest.objects.get_or_create(
        buyer=buyer,
        property=prop,
    )
    if created:
        messages.success(request, "Your interest has been submitted to the seller.")
    else:
        messages.info(request, "You have already expressed interest in this property.")

    return redirect('property_detail', pk=pk)
