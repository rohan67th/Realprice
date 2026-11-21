"""
buyer/search.py

Smart search parser — converts natural-language property queries into
Django ORM filters.  Port of the front-end parseQuery() that was in
buyer_landing.html's JS.

Usage:
    from buyer.search import apply_search
    qs, detected_mode = apply_search(request.GET.get('q', ''), qs, current_mode)
"""
import re
from django.db.models import Q
from buyer.templatetags.buyer_tags import _type_category


# ── Mode-detection patterns ──────────────────────────────────────────────
_RENT_RE = re.compile(r'\b(for\s+rent|rent(?:ing|als?)?)\b', re.I)
_BUY_RE  = re.compile(r'\b(for\s+sale|buy(?:ing)?|purchase)\b', re.I)

# ── Type detection ───────────────────────────────────────────────────────
_APT_RE   = re.compile(r'apartment|penthouse|loft|condo|flat', re.I)
_HOUSE_RE = re.compile(r'house|villa|townhome|townhouse|estate', re.I)

# ── Beds ─────────────────────────────────────────────────────────────────
_BEDS_RE = re.compile(r'(\d+)\s*\+?\s*(?:bed|br|bhk|bedroom)', re.I)

# ── Price (under/over) ───────────────────────────────────────────────────
_UNDER_RE = re.compile(
    r'(?:under|below|less\s+than|max|up\s+to|<)\s*\$?\s*'
    r'(\d+(?:\.\d+)?)(?!\d|\s*(?:bed|br|bhk))\s*(m|million|k)?',
    re.I,
)
_OVER_RE = re.compile(
    r'(?:over|above|more\s+than|min|at\s+least|>)\s*\$?\s*'
    r'(\d+(?:\.\d+)?)(?!\d|\s*(?:bed|br|bhk))\s*(m|million|k)?',
    re.I,
)

# ── Fresh listing ────────────────────────────────────────────────────────
_FRESH_RE = re.compile(r'just\s+listed|new\s+listing|newest|recent', re.I)


def _money(raw: str, unit: str | None, mode: str) -> float | None:
    """Convert a textual price into the DB value (Decimal-compatible float)."""
    try:
        n = float(raw)
    except (ValueError, TypeError):
        return None

    unit = (unit or '').lower()

    if mode == 'rent':
        # Rent prices are monthly in dollars
        if unit == 'k':
            return n * 1000
        return n
    else:
        # Sale prices stored in raw dollars
        if unit in ('m', 'million'):
            return n * 1_000_000
        if unit == 'k':
            return n * 1_000
        # Bare number: if < 1000 assume millions shorthand
        if n < 1000:
            return n * 1_000_000
        return n


def apply_search(query: str, qs, mode: str):
    """
    Parse *query* and filter *qs* accordingly.

    Returns (filtered_qs, detected_mode).
    - detected_mode may differ from the input *mode* if the query contains
      explicit "rent"/"buy" language.
    """
    if not query or not query.strip():
        return qs, mode

    q = query.strip()
    detected_mode = mode

    # ── Mode ──
    if _RENT_RE.search(q):
        detected_mode = 'rent'
    elif _BUY_RE.search(q):
        detected_mode = 'buy'

    if detected_mode != mode:
        qs = qs.filter(listing_type='rent' if detected_mode == 'rent' else 'sale')

    # ── Type ──
    if _APT_RE.search(q):
        qs = qs.filter(property_type__in=['Apartment', 'Commercial'])
    elif _HOUSE_RE.search(q):
        qs = qs.filter(property_type__in=['House', 'Land'])

    # ── Beds ──
    m = _BEDS_RE.search(q)
    if m:
        qs = qs.filter(bedrooms__gte=int(m.group(1)))

    # ── Price cap ──
    m = _UNDER_RE.search(q)
    if m:
        val = _money(m.group(1), m.group(2), detected_mode)
        if val is not None:
            qs = qs.filter(price__lte=val)

    m = _OVER_RE.search(q)
    if m:
        val = _money(m.group(1), m.group(2), detected_mode)
        if val is not None:
            qs = qs.filter(price__gte=val)

    # ── Fresh ──
    if _FRESH_RE.search(q):
        from django.utils import timezone
        from datetime import timedelta
        qs = qs.filter(posted_at__gte=timezone.now() - timedelta(days=14))

    # ── Location words ──
    # Strip out the tokens already matched by other regexes
    leftover = q
    for rx in (_RENT_RE, _BUY_RE, _APT_RE, _HOUSE_RE, _BEDS_RE, _UNDER_RE, _OVER_RE, _FRESH_RE):
        leftover = rx.sub('', leftover)

    # Location: remaining words ≥ 3 chars, matched against location and address
    loc_tokens = [w for w in re.findall(r'[a-zA-Z]{3,}', leftover)
                  if w.lower() not in ('bed', 'bath', 'for', 'the', 'and', 'with')]
    if loc_tokens:
        loc_q = Q()
        for tok in loc_tokens:
            loc_q |= Q(location__icontains=tok) | Q(address__icontains=tok)
        qs = qs.filter(loc_q)

    return qs, detected_mode
