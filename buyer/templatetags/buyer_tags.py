"""
buyer/templatetags/buyer_tags.py

Custom template tags/filters for the buyer module.
"""
from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def display_price(property_obj):
    """
    Format price for display:
    - Rent listings: "$2,800/mo"
    - Sale listings: "$4.2M" (millions), "$650K" (thousands), "$500" (raw)
    """
    price = property_obj.price
    listing = getattr(property_obj, 'listing_type', 'sale')

    if listing == 'rent':
        return f"${price:,.0f}/mo"

    # Sale pricing — human-friendly
    if price >= 1_000_000:
        millions = price / Decimal('1000000')
        # Show one decimal if meaningful, else integer
        if millions == int(millions):
            return f"${int(millions)}M"
        return f"${millions:.1f}M"
    elif price >= 1_000:
        thousands = price / Decimal('1000')
        if thousands == int(thousands):
            return f"${int(thousands)}K"
        return f"${thousands:.1f}K"
    return f"${price:,.0f}"


@register.filter
def format_detail_price(property_obj):
    """
    Format price for detail page:
    - Rent listings: "$2,800/mo"
    - Sale listings: "$4,200,000" (with intcomma formatting)
    """
    if not property_obj or not property_obj.price:
        return "$0"
    price = property_obj.price
    listing = getattr(property_obj, 'listing_type', 'sale')
    if listing == 'rent':
        return f"${price:,.0f}/mo"
    return f"${price:,.0f}"


@register.filter
def property_type_category(property_type):
    """
    Map the Property.property_type choices to house/apartment for filtering.
    House, Land → 'house'
    Apartment, Commercial → 'apartment'
    """
    return _type_category(property_type)


def _type_category(property_type):
    """Shared helper for mapping property_type → house/apartment."""
    mapping = {
        'House': 'house',
        'Land': 'house',
        'Apartment': 'apartment',
        'Commercial': 'apartment',
    }
    return mapping.get(property_type, 'house')


@register.filter
def is_in(value, collection):
    """Check if value is in a collection (set, list, queryset of ids, etc.)."""
    return value in collection


@register.filter
def badge_info(property_obj):
    """
    Return badge dict {text, css_bg, css_border, css_text} for a property card.
    Priority: Price Drop > New > listing type label.
    """
    from datetime import timedelta
    from django.utils import timezone

    is_new = (timezone.now() - property_obj.posted_at).days <= 14
    has_drop = (
        property_obj.previous_price is not None
        and property_obj.price < property_obj.previous_price
    )
    listing = getattr(property_obj, 'listing_type', 'sale')

    if has_drop:
        return {
            'text': 'Price Drop',
            'bg': 'bg-red-500/25',
            'border': 'border-red-500/30',
            'text_color': 'text-red-200',
        }
    elif is_new:
        return {
            'text': 'New',
            'bg': 'bg-indigo-500/25',
            'border': 'border-indigo-500/30',
            'text_color': 'text-indigo-200',
        }
    elif listing == 'rent':
        return {
            'text': 'Rental',
            'bg': 'bg-teal-500/25',
            'border': 'border-teal-500/30',
            'text_color': 'text-teal-200',
        }
    else:
        return {
            'text': 'For Sale',
            'bg': 'bg-blue-500/25',
            'border': 'border-blue-500/30',
            'text_color': 'text-blue-200',
        }


@register.filter
def price_gradient(property_obj):
    """Return a CSS gradient string based on listing type and type category."""
    listing = getattr(property_obj, 'listing_type', 'sale')
    cat = _type_category(property_obj.property_type)

    if listing == 'rent':
        return 'linear-gradient(135deg,#5eead4,#2dd4bf,#14b8a6)'
    if cat == 'apartment':
        return 'linear-gradient(135deg,#c4b5fd,#a78bfa,#8b5cf6)'
    return 'linear-gradient(135deg,#a5b4fc,#818cf8,#6366f1)'
