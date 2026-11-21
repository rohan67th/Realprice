from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import CustomUser, PasswordReset, Property, PropertyAuditLog
from django.contrib import messages
from django.core.mail import EmailMessage
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse

from django.db import transaction

# JWT helpers — used in every login/logout view
from auth_api.tokens import get_tokens_for_seller, get_tokens_for_buyer, set_jwt_cookies, clear_jwt_cookies
from auth_api.decorators import seller_required
from buyer.models import Buyer, VisitSchedule, Message



# ──────────────────────────────────────────────
# Unified Login (Admin + Seller + Buyer)
# ──────────────────────────────────────────────

def unified_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 1. Try Django auth first (covers Admin + Seller via CustomUser)
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # ── Admin ──
            if user.is_staff or user.is_superuser:
                login(request, user)
                tokens = get_tokens_for_seller(user)   # role='admin'
                response = redirect('admin_dashboard')
                set_jwt_cookies(response, tokens)
                return response

            # ── Seller (blocked) ──
            if user.is_blocked:
                messages.error(request, "Your account has been blocked by the admin.")
                return redirect('login')

            # ── Seller (rejected — gone forever) ──
            if getattr(user, 'review_status', '') == 'rejected':
                messages.error(request, "Your seller account application was not approved. Please check your email for details.")
                return redirect('login')

            # ── Seller (approved) ──
            if user.is_approved:
                login(request, user)
                tokens = get_tokens_for_seller(user)   # role='seller'
                profile_url = reverse('seller_profile', kwargs={'user_id': user.id})
                response = redirect(profile_url)
                set_jwt_cookies(response, tokens)
                return response

            # ── Seller (changes requested — let them log in to edit profile) ──
            if getattr(user, 'review_status', '') == 'changes_requested':
                login(request, user)
                tokens = get_tokens_for_seller(user)
                profile_url = reverse('seller_profile', kwargs={'user_id': user.id})
                response = redirect(profile_url)
                set_jwt_cookies(response, tokens)
                return response

            # ── Seller (pending) ──
            messages.error(request, "Your account is pending admin approval.")
            return redirect('login')

        # 2. Try Buyer model (separate model, not in Django auth)
        try:
            buyer = Buyer.objects.get(name=username)
            if buyer.check_password(password):
                tokens = get_tokens_for_buyer(buyer)
                messages.success(request, f"Welcome back, {buyer.name}!")
                response = redirect('buyer_landing')
                set_jwt_cookies(response, tokens)
                return response
            else:
                messages.error(request, 'Invalid credentials.')
                return redirect('login')
        except Buyer.DoesNotExist:
            pass

        # 3. Nothing matched
        messages.error(request, 'Invalid credentials.')
        return redirect('login')

    return render(request, 'unified_login.html')


def admin_logout(request):
    logout(request)
    response = redirect('/')
    clear_jwt_cookies(response)
    return response

from django.core.mail import send_mail

def approve_seller(request, seller_id):
    seller = get_object_or_404(CustomUser, id=seller_id)
    seller.is_approved = True
    seller.save()

    send_mail(
        subject='Your Seller Account Has Been Approved',
        message='Hi {},\n\nYour seller account has been approved! You can now log in and start using the platform.'.format(seller.username),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[seller.email],
        fail_silently=False,
    )

    messages.success(request, f"{seller.email} has been approved and notified.")
    return redirect('admin_dashboard')

def decline_seller(request, seller_id):
    seller = get_object_or_404(CustomUser, id=seller_id)

    send_mail(
        subject='Your Seller Account Has Been Declined',
        message='Hi {},\n\nWe’re sorry, but your seller account request has been declined.'.format(seller.username),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[seller.email],
        fail_silently=False,
    )

    seller.delete()
    messages.warning(request, f"{seller.email} has been declined and notified.")
    return redirect('admin_dashboard')


def seller_list(request):
    users = CustomUser.objects.filter(is_approved=True, is_superuser=False)
    all_sellers = CustomUser.objects.filter(is_superuser=False)
    total_sellers = all_sellers.count()
    active_sellers = all_sellers.filter(is_approved=True, is_blocked=False).count()
    blocked_sellers = all_sellers.filter(is_blocked=True).count()
    pending_sellers = all_sellers.filter(is_approved=False).count()
    return render(request, 'seller_list.html', {
        'users': users,
        'total_sellers': total_sellers,
        'active_sellers': active_sellers,
        'blocked_sellers': blocked_sellers,
        'pending_sellers': pending_sellers,
    })

def buyer_list(request):
    buyers = Buyer.objects.all()
    total_buyers = buyers.count()
    active_buyers = buyers.filter(is_active=True).count()
    suspended_buyers = buyers.filter(is_active=False).count()
    return render(request, 'buyer_list.html', {
        'buyers': buyers,
        'total_buyers': total_buyers,
        'active_buyers': active_buyers,
        'suspended_buyers': suspended_buyers,
    })


def toggle_block_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    user.is_blocked = not user.is_blocked
    user.save()
    return redirect('seller_list')


def approve_property(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    property_obj.approval_status = 'approved'
    property_obj.reviewed_at = timezone.now()
    property_obj.reviewed_by = request.user if request.user.is_authenticated else None
    property_obj.seller_feedback = ''
    property_obj.save()
    messages.success(request, f'Property "{property_obj}" approved successfully.')
    return redirect('admin_dashboard')


def decline_property(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    property_obj.approval_status = 'rejected'
    property_obj.reviewed_at = timezone.now()
    property_obj.reviewed_by = request.user if request.user.is_authenticated else None
    property_obj.save()
    messages.success(request, f'Property "{property_obj}" has been rejected.')
    return redirect('admin_dashboard')


def admin_property_list(request):
    properties = Property.objects.filter(is_approved=True).select_related('seller')
    total_properties = properties.count()
    for_sale_count = properties.filter(status='Available').count()
    for_rent_count = properties.filter(status='Rented').count()
    return render(request, 'admin_property_list.html', {
        'properties': properties,
        'total_properties': total_properties,
        'for_sale_count': for_sale_count,
        'for_rent_count': for_rent_count,
    })


from buyer.models import Complaint

def complaints_admin_view(request):
    complaints = Complaint.objects.select_related('property', 'buyer').order_by('-created_at')
    context = {
        'complaints': complaints
    }
    return render(request, 'admin_complaints_list.html', context)


def delete_property(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == "POST":
        property_obj.delete()
        messages.success(request, "Property deleted successfully.")
        return redirect('admin_property_list') 

    messages.error(request, "Invalid request method.")
    return redirect('admin_property_list')


def delete_buyer(request, buyer_id):
    if request.method == 'POST':
        buyer = get_object_or_404(Buyer, id=buyer_id)
        buyer.delete()
        messages.success(request, "Buyer deleted successfully.")
    return redirect('buyer_list')



#Seller
import re

MAX_FILE_SIZE_MB = 2  # Max 2MB
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


def is_strong_password(password):
    # At least 6 characters, one letter, one digit, one special character
    return (
        len(password) >= 6 and
        re.search(r"[A-Za-z]", password) and
        re.search(r"\d", password) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def seller_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        profile_pic = request.FILES.get('profile_pic')
        proof_of_identity = request.FILES.get('proof_of_identity')

        if not re.search(r'[A-Za-z]', username):
            messages.error(request, "Username should contain only letters.")
            return redirect('register')
        
        if not re.fullmatch(r'^[0-9]{10}$', phone):
            messages.error(request, "Enter a valid 10-digit phone number.")
            return redirect('register')
        
        if proof_of_identity and proof_of_identity.size > MAX_FILE_SIZE:
            messages.error(request, f"File size exceeds limit of {MAX_FILE_SIZE_MB}MB.")
            return redirect('register')
        

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')
        
        if not is_strong_password(password):
            messages.error(request, "Password must be at least 6 characters with letters, numbers, and a special character.")
            return redirect('register')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            address=address,
            gender=gender,
            profile_pic=profile_pic,
            password=password,
            proof_of_identity=proof_of_identity,
            role='seller',
            review_status='pending',
        )

        messages.success(request, "Registration successful! Your account is pending admin approval. You'll receive an email once reviewed.")
        return redirect('login')

    return render(request, 'register.html')

# seller_login has been merged into unified_login above


def logout_view(request):
    logout(request)
    response = redirect('login')
    clear_jwt_cookies(response)
    return response


def _get_seller_visit_counts(user):
    qs = VisitSchedule.objects.filter(property__seller=user)
    return {
        'all': qs.count(),
        'pending': qs.filter(status=VisitSchedule.Status.PENDING).count(),
        'approved': qs.filter(status=VisitSchedule.Status.APPROVED).count(),
        'declined': qs.filter(status=VisitSchedule.Status.DECLINED).count(),
        'rescheduled': qs.filter(status=VisitSchedule.Status.RESCHEDULE_PROPOSED).count(),
        'cancelled': qs.filter(status=VisitSchedule.Status.CANCELLED).count(),
        'completed': qs.filter(status=VisitSchedule.Status.COMPLETED).count(),
    }


@seller_required
def seller_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    seller_properties = Property.objects.filter(seller=user)
    buyers = Buyer.objects.all()

    visits_qs = (
        VisitSchedule.objects
        .filter(property__seller=user)
        .select_related('buyer', 'property')
        .order_by('-scheduled_date', '-scheduled_time')
    )

    counts = _get_seller_visit_counts(user)
    today = timezone.now().date()
    week_ahead = today + timezone.timedelta(days=7)
    week_visits_count = visits_qs.filter(
        scheduled_date__gte=today,
        scheduled_date__lte=week_ahead,
        status__in=[VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED]
    ).count()

    import json
    visits_json = []
    for v in visits_qs[:12]:
        photo_url = ''
        if v.buyer and v.buyer.profile_pic:
            try:
                photo_url = v.buyer.profile_pic.url
            except Exception:
                photo_url = ''

        date_display = v.scheduled_date.strftime('%b %d, %Y')
        if v.scheduled_date == today:
            date_display = 'Today'
        elif v.scheduled_date == today + timezone.timedelta(days=1):
            date_display = 'Tomorrow'

        time_display = v.scheduled_time.strftime('%I:%M %p') if v.scheduled_time else ''

        can_chat = v.status in (VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED)
        chat_url = (reverse('seller_chats_page', args=[user.id]) + f'?visit_id={v.id}') if can_chat else ''

        visits_json.append({
            'id': v.id,
            'buyer': v.buyer.name if v.buyer else 'Buyer',
            'buyer_name': v.buyer.name if v.buyer else 'Buyer',
            'buyer_email': v.buyer.email if v.buyer else '',
            'buyer_phone': getattr(v.buyer, 'phone', '') or '',
            'photo': photo_url,
            'initials': ''.join([part[0].upper() for part in (v.buyer.name if v.buyer else 'B').split()[:2]]) or 'B',
            'property': f"{v.property.property_type} - {v.property.location}" if v.property else 'Property',
            'property_title': f"{v.property.property_type} in {v.property.location}" if v.property else 'Property',
            'property_price': str(v.property.price) if v.property and v.property.price else '',
            'property_address': v.property.address if v.property and v.property.address else '',
            'date': date_display,
            'time': time_display,
            'scheduled_date': v.scheduled_date.strftime('%Y-%m-%d'),
            'scheduled_time': v.scheduled_time.strftime('%H:%M') if v.scheduled_time else '',
            'proposed_date': v.proposed_date.strftime('%Y-%m-%d') if v.proposed_date else '',
            'proposed_date_display': v.proposed_date.strftime('%b %d, %Y') if v.proposed_date else '',
            'proposed_time': v.proposed_time.strftime('%H:%M') if v.proposed_time else '',
            'proposed_time_display': v.proposed_time.strftime('%I:%M %p') if v.proposed_time else '',
            'decline_reason': v.decline_reason or '',
            'message': v.message or '',
            'status': v.status,
            'can_chat': can_chat,
            'chat_url': chat_url,
            'approve_url': reverse('approve_visit', args=[v.id]),
            'decline_url': reverse('decline_visit', args=[v.id]),
            'reschedule_url': reverse('seller_reschedule_visit', args=[v.id]),
            'complete_url': reverse('seller_complete_visit', args=[v.id]),
        })

    # Real messages for approved/completed visits
    recent_messages_qs = (
        Message.objects.filter(
            visit__property__seller=user,
            visit__status__in=[VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED]
        )
        .select_related('visit', 'visit__buyer', 'visit__property', 'sender_buyer', 'sender_seller')
        .order_by('-timestamp')
    )
    seen_visits = set()
    messages_json = []
    for msg in recent_messages_qs:
        if msg.visit_id in seen_visits:
            continue
        seen_visits.add(msg.visit_id)
        buyer_obj = msg.visit.buyer
        buyer_name = buyer_obj.name if buyer_obj else 'Buyer'
        photo_url = ''
        if buyer_obj and buyer_obj.profile_pic:
            try:
                photo_url = buyer_obj.profile_pic.url
            except Exception:
                photo_url = ''
        initials = ''.join([part[0].upper() for part in buyer_name.split()[:2]]) or 'B'

        time_diff = timezone.now() - msg.timestamp
        if time_diff.days == 0:
            time_display = msg.timestamp.strftime('%I:%M %p')
        elif time_diff.days == 1:
            time_display = 'Yesterday'
        else:
            time_display = msg.timestamp.strftime('%b %d')

        messages_json.append({
            'visit_id': msg.visit_id,
            'name': buyer_name,
            'avatar': photo_url,
            'initials': initials,
            'last': msg.content[:60] + ('…' if len(msg.content) > 60 else ''),
            'time': time_display,
            'property': f"{msg.visit.property.property_type}" if msg.visit.property else '',
            'chat_url': reverse('seller_chats_page', args=[user.id]) + f'?visit_id={msg.visit_id}',
        })
        if len(messages_json) >= 5:
            break

    return render(request, 'seller/dashboard.html', {
        'user': user,
        'page_title': 'Dashboard',
        'visits_json': json.dumps(visits_json),
        'messages_json': json.dumps(messages_json),
        'pending_visits_count': counts['pending'],
        'week_visits_count': week_visits_count,
        'approved_visits_count': counts['approved'],
        'declined_visits_count': counts['declined'],
        'rescheduled_visits_count': counts['rescheduled'],
        'completed_visits_count': counts['completed'],
        'total_visits_count': counts['all'],
        'seller_properties': seller_properties,
        'buyers': buyers,
    })

def seller_property_list(request):
    properties = Property.objects.filter(is_approved=True)
    return render(request,'seller_property_list.html',{'properties': properties})


@seller_required
def seller_edit_property(request, id):
    property = get_object_or_404(Property, id=id, seller=request.user)
    if request.method == 'POST':
        property_type = request.POST.get('property_type')
        address = request.POST.get('address')
        location = request.POST.get('location')
        latitude = request.POST.get('latitude') or None
        longitude = request.POST.get('longitude') or None
        area_sqft = request.POST.get('area_sqft') or None
        bedrooms = request.POST.get('bedrooms') or None
        bathrooms = request.POST.get('bathrooms') or None
        features = request.POST.get('features', '')
        description = request.POST.get('description', '')
        status = request.POST.get('status', 'Available')
        price = request.POST.get('price')

        # Fetch images if uploaded
        main_image = request.FILES.get('main_image')
        image_1 = request.FILES.get('image_1')
        image_2 = request.FILES.get('image_2')
        image_3 = request.FILES.get('image_3')

        from decimal import Decimal, InvalidOperation
        try:
            price_decimal = Decimal(price)
        except (InvalidOperation, TypeError):
            price_decimal = None

        if price_decimal is not None:
            property.property_type = property_type
            property.address = address
            property.location = location
            property.latitude = latitude
            property.longitude = longitude
            property.area_sqft = area_sqft
            property.bedrooms = bedrooms
            property.bathrooms = bathrooms
            property.features = features
            property.description = description
            property.status = status
            property.price = price_decimal

            if main_image:
                property.main_image = main_image
            if image_1:
                property.image_1 = image_1
            if image_2:
                property.image_2 = image_2
            if image_3:
                property.image_3 = image_3

            # If property was "changes_requested", auto-resubmit to pending
            was_changes_requested = property.approval_status == 'changes_requested'
            if was_changes_requested:
                property.approval_status = 'pending'
                property.seller_feedback = ''
                property.admin_notes = ''

            property.save()

            if was_changes_requested:
                PropertyAuditLog.objects.create(
                    property=property,
                    action='resubmit',
                    admin_user=None,
                    notes='Seller edited and resubmitted the property for review.',
                )
                messages.success(request, 'Property updated and resubmitted for admin review.')
            else:
                messages.success(request, 'Property updated successfully.')
            return redirect('seller_properties_page', user_id=request.user.id)
        else:
            messages.error(request, 'Invalid price entered.')

    return render(request, 'edit_property.html', {'property': property})


@seller_required
def seller_delete_property(request, id):
    property = get_object_or_404(Property, id=id, seller=request.user)
    property.delete()
    messages.success(request, 'Property deleted successfully.')
    return redirect('seller_property_list')


def seller_pending_properties(request):
    properties = Property.objects.filter(is_approved=False)
    return render(request, 'seller_pending_properties.html', {'properties': properties})


#Property Management

@seller_required
def add_property(request):
    if request.method == 'POST':
        property_type = request.POST.get('property_type')
        address = request.POST.get('address')
        location = request.POST.get('location')
        latitude = request.POST.get('latitude') or None
        longitude = request.POST.get('longitude') or None
        area_sqft = request.POST.get('area_sqft') or None
        bedrooms = request.POST.get('bedrooms') or None
        bathrooms = request.POST.get('bathrooms') or None
        features = request.POST.get('features', '')
        description = request.POST.get('description', '')
        status = request.POST.get('status', 'Available')
        price = request.POST.get('price')

        # Fetch all image fields from request.FILES
        main_image = request.FILES.get('main_image')
        image_1 = request.FILES.get('image_1')
        image_2 = request.FILES.get('image_2')
        image_3 = request.FILES.get('image_3')

        from decimal import Decimal, InvalidOperation
        try:
            price_decimal = Decimal(price)
        except (InvalidOperation, TypeError):
            price_decimal = None

        if price_decimal is not None:
            property = Property.objects.create(
                property_type=property_type,
                address=address,
                location=location,
                latitude=latitude,
                longitude=longitude,
                area_sqft=area_sqft,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                features=features,
                description=description,
                price=price_decimal,
                status=status,
                seller=request.user,
                main_image=main_image,
                image_1=image_1,
                image_2=image_2,
                image_3=image_3,
                is_approved=False
            )
            messages.success(request, 'Property added and pending admin approval.')
            return redirect('property_list', seller_id=request.user.id)
        else:
            messages.error(request, 'Invalid price entered.')
    return render(request, 'seller/add_property.html', {'page_title': 'Add Property'})




def property_list(request, seller_id):
    seller = get_object_or_404(CustomUser, id=seller_id)  # Fetch seller from URL param
    properties = Property.objects.filter(seller=seller, is_approved=True)  # Filter by seller
    return render(request, 'property_list.html', {
        'seller': seller,
        'properties': properties,
    })


def property_detail(request, pk):
    from buyer import views_pages
    return views_pages.buyer_property_detail_view(request, pk)


#Forget password

def forget_password(request):
    
    if request.method =="POST":
        email = request.POST.get('email')

        try:
            user = CustomUser.objects.get(email=email)

            new_password_reset = PasswordReset(user=user)
            new_password_reset.save()

            password_reset_url = reverse('reset-password', kwargs={'reset_id': new_password_reset.reset_id})

            full_password_reset_url = f'{request.scheme}://{request.get_host()}{password_reset_url}'

            email_body = f'Reset your password using the link below:\n\n\n{full_password_reset_url}'
        

            email_message = EmailMessage(
                'Reset your password',
                email_body,
                settings.EMAIL_HOST_USER,
                [email]
            )

            email_message.fail_silently = False
            email_message.send()

            return HttpResponseRedirect(reverse("password-reset-sent", kwargs={"reset_id": new_password_reset.reset_id}))
        
        except CustomUser.DoesNotExist:
            messages.error(request, f"No user with email '{email}' found")
            return redirect('forgot-password')

    return render(request,'forget_password.html')


def password_reset_sent(request,reset_id):

    if PasswordReset.objects.filter(reset_id=reset_id).exists():
        return render(request, 'password_reset_sent.html')
    else:
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password')


def reset_password(request,reset_id):
    
    try:
        password_reset_id = PasswordReset.objects.get(reset_id=reset_id)

        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            passwords_have_error = False

            if password != confirm_password:
                passwords_have_error = True
                messages.error(request, 'Passwords do not match')
            
            expiration_time = password_reset_id.created_when + timezone.timedelta(minutes=10)

            if timezone.now() > expiration_time:
                passwords_have_error = True
                messages.error(request, 'Reset link has expired')

                password_reset_id.delete()

            if not passwords_have_error:
                user = password_reset_id.user
                user.set_password(password)
                user.save()

                password_reset_id.delete()

                messages.success(request, 'Password reset. Proceed to login')
                return redirect('login')
            
            else:
                return redirect('reset-password',reset_id=reset_id)

    
    
    except PasswordReset.DoesNotExist:
        
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password')

    return render(request, 'reset_password.html',{'reset_id': reset_id})

@seller_required
def edit_profile(request):
    user = CustomUser.objects.get(email=request.user.email)

    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.phone = request.POST.get('phone')
        user.address = request.POST.get('address')
        user.gender = request.POST.get('gender')

        # Handle profile picture if uploaded
        if 'profile_pic' in request.FILES:
            user.profile_pic = request.FILES['profile_pic']

        # Handle proof of identity if uploaded
        if 'proof_of_identity' in request.FILES:
            user.proof_of_identity = request.FILES['proof_of_identity']

        user.save()

        messages.success(request, "Profile updated successfully!")
        profile_url = reverse('seller_profile', kwargs={'user_id': user.id})
        return redirect(profile_url)

    return render(request, 'edit_seller.html', {'user': user})



def landingpage(request):
    property = Property.objects.all()
    return render(request,'landingpage.html',{'properties': property})


def register_choice(request):
    return render(request, 'register_choice.html')


def about(request):
    return render(request,'about.html')


def contact(request):
    return render(request,'contact.html')

from buyer.models import Buyer


def dashboard(request):
    pending_sellers = CustomUser.objects.filter(is_approved=False, is_superuser=False)
    pending_properties = Property.objects.filter(is_approved=False)
    total_sellers = CustomUser.objects.filter(is_superuser=False).count()
    total_properties = Property.objects.count()
    total_buyers = Buyer.objects.filter(is_staff=False).count()

    # Additional context for Dark Crisp dashboard
    total_users = total_sellers + total_buyers
    total_listings = Property.objects.filter(is_approved=True).count()
    pending_approvals = pending_sellers.count() + pending_properties.count()
    pending_seller_count = pending_sellers.count()
    pending_property_count = pending_properties.count()
    open_complaints_count = Complaint.objects.filter(status='open').count()
    recent_properties = Property.objects.filter(is_approved=True).select_related('seller').order_by('-posted_at')[:4]
    recent_sellers = CustomUser.objects.filter(is_superuser=False).order_by('-id')[:5]

    return render(request, "dashboard.html", {
        "pending_sellers": pending_sellers,
        "pending_properties": pending_properties,
        "total_sellers": total_sellers,
        "total_properties": total_properties,
        "total_buyers": total_buyers,
        "total_users": total_users,
        "total_listings": total_listings,
        "pending_approvals": pending_approvals,
        "pending_seller_count": pending_seller_count,
        "pending_property_count": pending_property_count,
        "open_complaints_count": open_complaints_count,
        "recent_properties": recent_properties,
        "recent_sellers": recent_sellers,
    })



# Scdeduled Visit
from .models import CustomUser
from buyer.models import VisitSchedule


@seller_required
def visit_requests(request, seller_id):
    seller = get_object_or_404(CustomUser, id=seller_id)
    visits = VisitSchedule.objects.filter(property__seller=seller,status='pending')

    print(f"Seller ID: {seller_id}, Visits Count: {visits.count()}")  # Debugging line
    return render(request, 'visit_requests.html', {'visits': visits, 'seller': seller})


@seller_required
def approve_visit(request, visit_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true' or request.content_type == 'application/json'

    with transaction.atomic():
        visit = (
            VisitSchedule.objects
            .select_for_update()
            .select_related('property', 'property__seller', 'buyer')
            .filter(id=visit_id, property__seller=request.user)
            .first()
        )
        if not visit:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Visit not found or not owned by you.'}, status=404)
            raise Http404

        # Transition rules: only pending or reschedule_proposed can be approved
        if visit.status == VisitSchedule.Status.APPROVED:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Visit is already approved.'}, status=400)
            messages.error(request, 'Visit is already approved.')
            return redirect('seller_visits_page', user_id=visit.property.seller.id)

        if visit.status in (VisitSchedule.Status.DECLINED, VisitSchedule.Status.CANCELLED, VisitSchedule.Status.COMPLETED):
            if is_ajax:
                return JsonResponse({'success': False, 'error': f'Cannot approve a {visit.status} visit.'}, status=400)
            messages.error(request, f'Cannot approve a {visit.status} visit.')
            return redirect('seller_visits_page', user_id=visit.property.seller.id)

        # Past-date rejection
        now = timezone.now()
        today = now.date()
        if visit.scheduled_date < today or (visit.scheduled_date == today and visit.scheduled_time and visit.scheduled_time < now.time()):
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Cannot approve a visit scheduled in the past.'}, status=400)
            messages.error(request, 'Cannot approve a visit scheduled in the past.')
            return redirect('seller_visits_page', user_id=visit.property.seller.id)

        visit.status = VisitSchedule.Status.APPROVED
        visit.is_notified = True
        visit.responded_at = timezone.now()
        visit.save()

    counts = _get_seller_visit_counts(request.user)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'approved',
            'status_label': 'Approved',
            'visit_id': visit.id,
            'chat_url': reverse('seller_chats_page', args=[visit.property.seller.id]) + f'?visit_id={visit.id}',
            'counts': counts,
        })

    messages.success(request, f'Visit approved for {visit.buyer.name if visit.buyer else "buyer"}.')
    referer = request.META.get('HTTP_REFERER')
    if referer and 'visit' in referer:
        return redirect(referer)
    return redirect('seller_visits_page', user_id=visit.property.seller.id)


@seller_required
def decline_visit(request, visit_id, seller_id=None):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true' or request.content_type == 'application/json'

    reason = request.POST.get('reason', '').strip()
    if not reason and request.content_type == 'application/json':
        try:
            import json as pyjson
            body = pyjson.loads(request.body)
            reason = body.get('reason', '').strip()
        except Exception:
            pass

    with transaction.atomic():
        visit = (
            VisitSchedule.objects
            .select_for_update()
            .select_related('property', 'property__seller', 'buyer')
            .filter(id=visit_id, property__seller=request.user)
            .first()
        )
        if not visit:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Visit not found or not owned by you.'}, status=404)
            raise Http404

        if visit.status in (VisitSchedule.Status.DECLINED, VisitSchedule.Status.CANCELLED, VisitSchedule.Status.COMPLETED):
            if is_ajax:
                return JsonResponse({'success': False, 'error': f'Cannot decline a visit that is already {visit.status}.'}, status=400)
            messages.error(request, f'Cannot decline a visit that is already {visit.status}.')
            return redirect('seller_visits_page', user_id=visit.property.seller.id)

        visit.status = VisitSchedule.Status.DECLINED
        if reason:
            visit.decline_reason = reason
        visit.responded_at = timezone.now()
        visit.save()

    counts = _get_seller_visit_counts(request.user)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'declined',
            'status_label': 'Declined',
            'visit_id': visit.id,
            'counts': counts,
        })

    messages.info(request, f'Visit declined for {visit.buyer.name if visit.buyer else "buyer"}.')
    referer = request.META.get('HTTP_REFERER')
    if referer and 'visit' in referer:
        return redirect(referer)
    return redirect('seller_visits_page', user_id=visit.property.seller.id)


@seller_required
def seller_reschedule_visit(request, visit_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true' or request.content_type == 'application/json'

    proposed_date_str = request.POST.get('proposed_date', '').strip()
    proposed_time_str = request.POST.get('proposed_time', '').strip()
    if (not proposed_date_str or not proposed_time_str) and request.content_type == 'application/json':
        try:
            import json as pyjson
            body = pyjson.loads(request.body)
            proposed_date_str = body.get('proposed_date', '').strip()
            proposed_time_str = body.get('proposed_time', '').strip()
        except Exception:
            pass

    if not proposed_date_str or not proposed_time_str:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Both proposed date and time are required.'}, status=400)
        messages.error(request, 'Both proposed date and time are required.')
        return redirect('seller_visits_page', user_id=request.user.id)

    from datetime import datetime as dt
    try:
        prop_date = dt.strptime(proposed_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format (expected YYYY-MM-DD).'}, status=400)

    try:
        prop_time = dt.strptime(proposed_time_str, '%H:%M').time()
    except ValueError:
        try:
            prop_time = dt.strptime(proposed_time_str, '%H:%M:%S').time()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid time format (expected HH:MM).'}, status=400)

    now = timezone.now()
    if prop_date < now.date() or (prop_date == now.date() and prop_time < now.time()):
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Proposed date and time must be in the future.'}, status=400)
        messages.error(request, 'Proposed date and time must be in the future.')
        return redirect('seller_visits_page', user_id=request.user.id)

    with transaction.atomic():
        visit = (
            VisitSchedule.objects
            .select_for_update()
            .select_related('property', 'property__seller', 'buyer')
            .filter(id=visit_id, property__seller=request.user)
            .first()
        )
        if not visit:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Visit not found or not owned by you.'}, status=404)
            raise Http404

        if visit.status in (VisitSchedule.Status.DECLINED, VisitSchedule.Status.CANCELLED, VisitSchedule.Status.COMPLETED):
            if is_ajax:
                return JsonResponse({'success': False, 'error': f'Cannot reschedule a {visit.status} visit.'}, status=400)
            messages.error(request, f'Cannot reschedule a {visit.status} visit.')
            return redirect('seller_visits_page', user_id=visit.property.seller.id)

        visit.proposed_date = prop_date
        visit.proposed_time = prop_time
        visit.status = VisitSchedule.Status.RESCHEDULE_PROPOSED
        visit.responded_at = timezone.now()
        visit.save()

    counts = _get_seller_visit_counts(request.user)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'reschedule_proposed',
            'status_label': 'Reschedule Proposed',
            'visit_id': visit.id,
            'proposed_date': prop_date.isoformat(),
            'proposed_time': prop_time.strftime('%I:%M %p'),
            'counts': counts,
        })

    messages.info(request, f'Proposed new time for {visit.buyer.name if visit.buyer else "buyer"}.')
    return redirect('seller_visits_page', user_id=visit.property.seller.id)


@seller_required
def seller_complete_visit(request, visit_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true' or request.content_type == 'application/json'

    with transaction.atomic():
        visit = (
            VisitSchedule.objects
            .select_for_update()
            .select_related('property', 'property__seller', 'buyer')
            .filter(id=visit_id, property__seller=request.user)
            .first()
        )
        if not visit:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Visit not found or not owned by you.'}, status=404)
            raise Http404

        if visit.status != VisitSchedule.Status.APPROVED:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Only approved visits can be marked as completed.'}, status=400)
            messages.error(request, 'Only approved visits can be marked as completed.')
            return redirect('seller_visits_page', user_id=visit.property.seller.id)

        visit.status = VisitSchedule.Status.COMPLETED
        visit.save()

    counts = _get_seller_visit_counts(request.user)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'completed',
            'status_label': 'Completed',
            'visit_id': visit.id,
            'chat_url': reverse('seller_chats_page', args=[visit.property.seller.id]) + f'?visit_id={visit.id}',
            'counts': counts,
        })

    messages.success(request, 'Visit marked as completed.')
    return redirect('seller_visits_page', user_id=visit.property.seller.id)


@seller_required
def seller_create_visit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        buyer_id = request.POST.get('buyer_id')
        buyer_name = request.POST.get('buyer_name', '').strip()
        scheduled_date_str = request.POST.get('scheduled_date')
        scheduled_time_str = request.POST.get('scheduled_time')
        message = request.POST.get('message', '').strip()

        property_obj = get_object_or_404(Property, id=property_id, seller=user)

        buyer = None
        if buyer_id:
            buyer = Buyer.objects.filter(id=buyer_id).first()
        if not buyer and buyer_name:
            if '@' in buyer_name:
                buyer = Buyer.objects.filter(email__iexact=buyer_name).first()
            if not buyer:
                buyer = Buyer.objects.filter(name__iexact=buyer_name).first()
            if not buyer:
                from django.utils.text import slugify
                base_email = buyer_name if '@' in buyer_name else f"{slugify(buyer_name or 'buyer')}@example.com"
                email = base_email
                counter = 1
                while Buyer.objects.filter(email=email).exists():
                    email = f"{base_email.split('@')[0]}_{counter}@{base_email.split('@')[1]}"
                    counter += 1
                buyer = Buyer.objects.create(
                    name=buyer_name,
                    email=email,
                    phone='',
                    address='',
                    gender='O',
                    password='pbkdf2_sha256$placeholder'
                )

        if not buyer:
            buyer = Buyer.objects.first()

        if property_obj and buyer and scheduled_date_str and scheduled_time_str:
            from datetime import datetime
            try:
                scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
            except ValueError:
                scheduled_date = scheduled_date_str
            try:
                scheduled_time = datetime.strptime(scheduled_time_str, '%H:%M').time()
            except ValueError:
                scheduled_time = scheduled_time_str

            VisitSchedule.objects.create(
                buyer=buyer,
                property=property_obj,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                message=message,
                status='approved',
                is_notified=True
            )
            messages.success(request, f'Visit scheduled with {buyer.name} for {property_obj.property_type}.')
        else:
            messages.error(request, 'Please fill in all required fields.')

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('seller_visits_page', user_id=user.id)


@seller_required
def chat_with_buyer(request, visit_id, sender_type, sender_id):
    visit = get_object_or_404(VisitSchedule, id=visit_id, property__seller=request.user)

    # Chat unlocked only for approved and completed visits
    if visit.status not in (VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED):
        return render(request, 'chat/invalid_sender.html', {'message': 'Chat is locked until the visit is approved.'})

    if sender_type != 'seller' or request.user.id != int(sender_id):
        return render(request, 'chat/invalid_sender.html', {'message': 'Invalid or unauthorized sender.'})

    messages = Message.objects.filter(visit=visit).order_by('timestamp')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()

        if not content:
            return render(request, 'seller_chat.html', {
                'visit': visit,
                'messages': messages,
                'sender_type': 'seller',
                'sender_id': request.user.id,
                'error': 'Message cannot be empty.'
            })

        Message.objects.create(
            visit=visit,
            content=content,
            sender_seller=request.user,
        )
        return redirect('seller_chat', visit_id=visit.id, sender_type='seller', sender_id=request.user.id)

    return render(request, 'seller_chat.html', {
        'visit': visit,
        'messages': messages,
        'sender_type': 'seller',
        'sender_id': request.user.id,
    })

    return render(request, 'seller_chat.html', {
        'visit': visit,
        'messages': messages,
        'sender_type': 'seller',
        'sender_id': sender_id,
    })

from buyer.models import RentRequest


@seller_required
def pending_rent_requests(request, seller_id):
    seller = get_object_or_404(CustomUser, id=seller_id)
    properties = Property.objects.filter(seller=seller)
    rent_requests = RentRequest.objects.filter(property__in=properties, status='pending')

    return render(request, 'seller_rent_request.html', {
        'rent_requests': rent_requests,
        'seller': seller
    })
@seller_required
def approve_rent_request(request, request_id):
    rent_request = get_object_or_404(RentRequest, id=request_id, property__seller=request.user)
    rent_request.status = 'approved'
    rent_request.save()
    return redirect('seller_rent_requests', seller_id=rent_request.property.seller.id)

@seller_required
def decline_rent_request(request, request_id):
    rent_request = get_object_or_404(RentRequest, id=request_id, property__seller=request.user)
    rent_request.status = 'rejected'
    rent_request.save()
    return redirect('seller_rent_requests', seller_id=rent_request.property.seller.id)


# ──────────────────────────────────────────────
# New Admin Placeholder Views
# ──────────────────────────────────────────────

"""
Seller approvals — admin views.

Fixes applied vs. the original:
  1. All three views are now gated behind login + admin-check (see `admin_required`
     below). Adjust the check inside `admin_required` to match however RealtyFlow
     already identifies admins elsewhere in the codebase (e.g. request.user.role == 'admin').
  2. seller_document_view no longer redirects to the raw storage URL — it streams
     the file itself, so it can never be reached without passing the admin check.
  3. save() + audit log creation + email are wrapped in transaction.atomic() so a
     failure can't leave the seller's status and the audit trail out of sync.
  4. Reject / request_changes now require a non-empty note.
  5. Duplicate "create log + send email" logic pulled into one helper.
  6. Failed emails are logged instead of silently disappearing (fail_silently=True
     was hiding delivery failures).

NOTE on the seller list query: the original filtered `is_superuser=False`, which
will also include buyers if CustomUser is shared across roles. I've left the
query as-is but flagged it below — swap in your actual role field
(e.g. `role='seller'`) if one exists on the model.
"""

import logging
 
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
 
logger = logging.getLogger(__name__)
 
 
def _is_admin(user):
    # TODO: match this to however admin status is actually determined in
    # RealtyFlow (e.g. a `role` field). is_staff is a reasonable default.
    return user.is_authenticated and (user.is_staff or user.is_superuser)
 
 
admin_required = user_passes_test(_is_admin, login_url='login')
 
 
def _notify(seller, subject, body):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[seller.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send email to seller id=%s (%s)", seller.id, seller.email)
 
 
@login_required
@admin_required
def seller_approvals(request):
    from .models import SellerAuditLog
 
    sellers = CustomUser.objects.filter(role='seller')
    q = request.GET.get('q', '').strip()
    if q:
        sellers = sellers.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )
 
    # Action-queue model: only show actionable statuses by default.
    # Approved and rejected sellers are GONE from this page.
    status_filter = request.GET.get('status', 'pending')
    if status_filter == 'blocked':
        sellers = sellers.filter(is_blocked=True)
    elif status_filter == 'all':
        # 'All' still excludes approved/rejected — they're gone forever from
        # this page. Only shows pending + changes_requested + blocked.
        sellers = sellers.exclude(review_status__in=['approved', 'rejected']).filter(is_blocked=False) | \
                  sellers.filter(is_blocked=True)
    elif status_filter in ('pending', 'changes_requested'):
        sellers = sellers.filter(review_status=status_filter, is_blocked=False)
    else:
        # Fallback to pending for any unknown filter
        status_filter = 'pending'
        sellers = sellers.filter(review_status='pending', is_blocked=False)
 
    all_sellers = CustomUser.objects.filter(role='seller')
    pending_count = all_sellers.filter(review_status='pending', is_blocked=False).count()
    changes_requested_count = all_sellers.filter(review_status='changes_requested', is_blocked=False).count()
    approved_count = all_sellers.filter(review_status='approved', is_blocked=False).count()
    rejected_count = all_sellers.filter(review_status='rejected', is_blocked=False).count()
    blocked_count = all_sellers.filter(is_blocked=True).count()
 
    paginator = Paginator(sellers, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
 
    seller_ids = [s.id for s in page_obj]
    audit_logs = (
        SellerAuditLog.objects.filter(seller_id__in=seller_ids)
        .select_related('admin_user')
        .order_by('created_at')
    )
    audit_logs_by_seller = {}
    for log in audit_logs:
        audit_logs_by_seller.setdefault(log.seller_id, []).append(log)
 
    sellers_payload = []
    for s in page_obj:
        sellers_payload.append({
            'id': s.id,
            'username': s.username,
            'email': s.email,
            'phone': s.phone or '',
            'gender': s.gender or '',
            'address': s.address or '',
            'profilePic': s.profile_pic.url if s.profile_pic else '',
            'hasProof': bool(s.proof_of_identity),
            'proofFilename': s.proof_of_identity.name.split('/')[-1] if s.proof_of_identity else '',
            'reviewStatus': s.review_status,
            'isBlocked': s.is_blocked,
            'blockReason': s.block_reason or '',
            'rejectionReason': s.rejection_reason or '',
            'dateJoined': s.date_joined.strftime('%b %d, %Y %I:%M %p') if s.date_joined else 'N/A',
            'docUrl': reverse('seller_document_view', args=[s.id]),
            'actionUrl': reverse('seller_approval_action', args=[s.id]),
        })
 
    audit_payload = {
        str(seller_id): [
            {
                'action': log.get_action_display(),
                'actionRaw': log.action,
                'admin': log.admin_user.username if log.admin_user else 'System',
                'notes': log.notes or '',
                'date': log.created_at.strftime('%b %d, %I:%M %p'),
            }
            for log in logs
        ]
        for seller_id, logs in audit_logs_by_seller.items()
    }
 
    return render(request, 'seller_approvals.html', {
        'page_obj': page_obj,
        'sellers': page_obj,
        'q': q,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'changes_requested_count': changes_requested_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'blocked_count': blocked_count,
        'sellers_json': sellers_payload,
        'audit_json': audit_payload,
    })
 
 
@login_required
@admin_required
@require_POST
def seller_approval_action(request, seller_id):
    from .models import SellerAuditLog
 
    seller = get_object_or_404(CustomUser, id=seller_id, role='seller')
    action = request.POST.get('action', '')
    notes = request.POST.get('notes', '').strip()
 
    if action in ('reject', 'request_changes') and not notes:
        messages.error(request, "Please add a note explaining the reason before submitting.")
        return redirect('seller_approvals')
 
    if action == 'approve':
        with transaction.atomic():
            seller.review_status = 'approved'
            seller.is_approved = True
            seller.rejection_reason = ''
            seller.save()
            SellerAuditLog.objects.create(
                seller=seller, action='approve', admin_user=request.user,
                notes=notes or 'Seller approved by admin.',
            )
        _notify(
            seller,
            'Your Seller Account Has Been Approved',
            f'Hi {seller.username},\n\nYour seller account has been approved! '
            'You can now log in and start using the platform.\n\nBest regards,\nREAL PRICE Team',
        )
        messages.success(request, f"{seller.username} has been approved and notified via email.")
 
    elif action == 'reject':
        # Terminal — rejected sellers are gone forever from the approvals page.
        # The seller cannot resubmit; they receive the reason via email.
        with transaction.atomic():
            seller.review_status = 'rejected'
            seller.is_approved = False
            seller.rejection_reason = notes
            seller.save()
            SellerAuditLog.objects.create(
                seller=seller, action='reject', admin_user=request.user, notes=notes,
            )
        _notify(
            seller,
            'Your Seller Account Application Was Not Approved',
            f'Hi {seller.username},\n\nAfter review, we are unable to approve your seller '
            f'account application.\n\nReason: {notes}\n\n'
            'If you believe this is an error, please contact our support team.\n\n'
            'Best regards,\nREAL PRICE Team',
        )
        messages.warning(request, f"{seller.username} has been rejected and notified via email.")
 
    elif action == 'request_changes':
        # Not terminal — seller can log in, edit their profile/documents,
        # and resubmit via seller_resubmit_application() to return to 'pending'.
        with transaction.atomic():
            seller.review_status = 'changes_requested'
            seller.is_approved = False
            seller.rejection_reason = notes
            seller.save()
            SellerAuditLog.objects.create(
                seller=seller, action='request_changes', admin_user=request.user, notes=notes,
            )
        _notify(
            seller,
            'Action Required: Changes Needed for Your Seller Account',
            f'Hi {seller.username},\n\nWe have reviewed your seller account application and '
            f'need some changes before we can approve it.\n\nAdmin Notes: {notes}\n\n'
            'Please log in and update your profile/documents, then resubmit for review.\n\n'
            'Best regards,\nREAL PRICE Team',
        )
        messages.info(request, f"Change request sent to {seller.username} via email.")
 
    else:
        messages.error(request, "Invalid action.")
 
    return redirect('seller_approvals')
 
 
@login_required
@admin_required
@require_POST
def delete_seller(request, seller_id):
    seller = get_object_or_404(CustomUser, id=seller_id, role='seller')
    username = seller.username
    seller.delete()
    messages.success(request, f"Seller '{username}' has been successfully deleted.")
    return redirect('seller_list')
 
 
@login_required
@require_POST
def seller_resubmit_application(request, seller_id):
    """
    Seller-side action. Only the seller themselves can trigger it, and only from
    'changes_requested' — this is the one and only door back into the review
    queue. Rejected sellers have no equivalent endpoint.
    """
    from .models import SellerAuditLog
 
    seller = get_object_or_404(CustomUser, id=seller_id, role='seller')
    if request.user.id != seller.id:
        raise Http404()
 
    if seller.review_status != 'changes_requested':
        messages.error(request, "This application isn't awaiting resubmission.")
        return redirect('seller_profile', user_id=seller.id)
 
    with transaction.atomic():
        seller.review_status = 'pending'
        seller.rejection_reason = ''
        seller.save()
        SellerAuditLog.objects.create(
            seller=seller, action='resubmit', admin_user=None,
            notes='Seller updated their profile/documents and resubmitted for review.',
        )
 
    messages.success(request, "Your application has been resubmitted for review. You will be notified once reviewed.")
    return redirect('seller_profile', user_id=seller.id)
 
 
@login_required
@admin_required
def seller_document_view(request, seller_id):
    """
    Streams the seller's ID document directly instead of redirecting to the
    storage URL. This keeps the document behind the admin_required check.
    """
    seller = get_object_or_404(CustomUser, id=seller_id, role='seller')
    if not seller.proof_of_identity:
        messages.error(request, "No document uploaded by this seller.")
        return redirect('seller_approvals')
 
    try:
        file_handle = seller.proof_of_identity.open('rb')
    except FileNotFoundError:
        raise Http404("Document not found.")
 
    filename = seller.proof_of_identity.name.split('/')[-1]
    response = FileResponse(file_handle, as_attachment=False, filename=filename)
    return response
 

@login_required
@admin_required
def listing_approvals(request):
    """Admin listing approvals page with status tabs, search, and pagination."""
    properties = Property.objects.select_related('seller').order_by('-posted_at')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        properties = properties.filter(
            Q(property_type__icontains=q) |
            Q(location__icontains=q) |
            Q(address__icontains=q) |
            Q(seller__username__icontains=q) |
            Q(seller__email__icontains=q)
        )

    # Status tab filtering
    status_filter = request.GET.get('status', 'all')
    if status_filter in ('pending', 'approved', 'rejected', 'changes_requested'):
        properties = properties.filter(approval_status=status_filter)
    # 'all' shows everything

    # Counts for stat cards
    all_props = Property.objects.all()
    pending_count = all_props.filter(approval_status='pending').count()
    approved_count = all_props.filter(approval_status='approved').count()
    rejected_count = all_props.filter(approval_status='rejected').count()
    changes_requested_count = all_props.filter(approval_status='changes_requested').count()

    # Pagination
    paginator = Paginator(properties, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'listing_approvals.html', {
        'page_obj': page_obj,
        'properties': page_obj,
        'q': q,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'changes_requested_count': changes_requested_count,
        'total_count': pending_count + approved_count + rejected_count + changes_requested_count,
    })


@login_required
@admin_required
@require_POST
def listing_approval_action(request, property_id):
    """Unified POST handler for property approval actions."""
    property_obj = get_object_or_404(Property, id=property_id)
    action = request.POST.get('action', '')
    admin_notes = request.POST.get('admin_notes', '').strip()
    seller_feedback = request.POST.get('seller_feedback', '').strip()

    if action in ('reject', 'request_changes') and not seller_feedback:
        messages.error(request, 'Please provide feedback to the seller before submitting.')
        return redirect('listing_approvals')

    if action == 'approve':
        with transaction.atomic():
            property_obj.approval_status = 'approved'
            property_obj.reviewed_at = timezone.now()
            property_obj.reviewed_by = request.user
            property_obj.admin_notes = admin_notes
            property_obj.seller_feedback = ''
            property_obj.save()
            PropertyAuditLog.objects.create(
                property=property_obj,
                action='approve',
                admin_user=request.user,
                notes=admin_notes or 'Property approved by admin.',
                seller_feedback='',
            )
        messages.success(request, f'Property "{property_obj}" has been approved.')

    elif action == 'reject':
        with transaction.atomic():
            property_obj.approval_status = 'rejected'
            property_obj.reviewed_at = timezone.now()
            property_obj.reviewed_by = request.user
            property_obj.admin_notes = admin_notes
            property_obj.seller_feedback = seller_feedback
            property_obj.save()
            PropertyAuditLog.objects.create(
                property=property_obj,
                action='reject',
                admin_user=request.user,
                notes=admin_notes,
                seller_feedback=seller_feedback,
            )
        messages.warning(request, f'Property "{property_obj}" has been rejected.')

    elif action == 'request_changes':
        with transaction.atomic():
            property_obj.approval_status = 'changes_requested'
            property_obj.reviewed_at = timezone.now()
            property_obj.reviewed_by = request.user
            property_obj.admin_notes = admin_notes
            property_obj.seller_feedback = seller_feedback
            property_obj.save()
            PropertyAuditLog.objects.create(
                property=property_obj,
                action='request_changes',
                admin_user=request.user,
                notes=admin_notes,
                seller_feedback=seller_feedback,
            )
        messages.info(request, f'Change request sent for "{property_obj}".')

    else:
        messages.error(request, 'Invalid action.')

    # Preserve current tab filter on redirect
    return redirect(f"{reverse('listing_approvals')}?status={request.POST.get('current_tab', 'all')}")


@login_required
@admin_required
def property_review_data(request, property_id):
    """Return JSON with full property details for the review modal (AJAX)."""
    prop = get_object_or_404(Property.objects.select_related('seller'), id=property_id)
    seller = prop.seller
    seller_property_count = Property.objects.filter(seller=seller).count()

    # Collect image URLs
    images = []
    if prop.main_image:
        images.append({'label': 'Cover Image', 'url': prop.main_image.url})
    for attr, label in [('image_1', 'Gallery 1'), ('image_2', 'Gallery 2'), ('image_3', 'Gallery 3')]:
        img = getattr(prop, attr)
        if img:
            images.append({'label': label, 'url': img.url})

    data = {
        'id': prop.id,
        'property_type': prop.property_type,
        'address': prop.address,
        'location': prop.location,
        'latitude': prop.latitude,
        'longitude': prop.longitude,
        'area_sqft': prop.area_sqft,
        'bedrooms': prop.bedrooms,
        'bathrooms': prop.bathrooms,
        'features': prop.features,
        'description': prop.description,
        'price': str(prop.price),
        'status': prop.status,
        'approval_status': prop.approval_status,
        'approval_label': prop.get_approval_display_label(),
        'posted_at': prop.posted_at.strftime('%b %d, %Y %I:%M %p') if prop.posted_at else 'N/A',
        'images': images,
        'admin_notes': prop.admin_notes,
        'seller_feedback': prop.seller_feedback,
        'action_url': reverse('listing_approval_action', args=[prop.id]),
        'seller': {
            'id': seller.id,
            'username': seller.username,
            'email': seller.email,
            'phone': seller.phone or 'N/A',
            'profile_pic': seller.profile_pic.url if seller.profile_pic else '',
            'review_status': seller.get_review_status_display() if hasattr(seller, 'get_review_status_display') else seller.review_status,
            'total_properties': seller_property_count,
            'profile_url': reverse('seller_profile', args=[seller.id]),
        },
    }
    return JsonResponse(data)


def admin_analytics(request):
    return render(request, 'analytics.html')


def chatbot_logs(request):
    return render(request, 'chatbot_logs.html')


def activity_logs(request):
    return render(request, 'activity_logs.html')


# ──────────────────────────────────────────────
# Seller Dashboard Split Views
# ──────────────────────────────────────────────

@seller_required
def seller_properties_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    properties = Property.objects.filter(seller=user).order_by('-posted_at')
    buyers = Buyer.objects.all()
    import json
    properties_json = []
    for p in properties:
        properties_json.append({
            'id': p.id,
            'property_type': p.property_type,
            'location': p.location,
            'address': p.address,
            'price': str(p.price),
            'status': p.status,
            'approval_status': p.approval_status,
            'approval_label': p.get_approval_display_label(),
            'approval_badge': p.get_approval_badge_class(),
            'seller_feedback': p.seller_feedback,
            'main_image': p.main_image.url if p.main_image else '',
            'posted_at': p.posted_at.strftime('%b %d, %Y') if p.posted_at else 'N/A',
            'bedrooms': p.bedrooms,
            'bathrooms': p.bathrooms,
            'area_sqft': p.area_sqft,
            'features': p.features,
            'edit_url': reverse('seller_edit_property', args=[p.id]),
            'delete_url': reverse('seller_delete_property', args=[p.id]),
            'detail_url': reverse('property_detail', args=[p.id]),
        })
    return render(request, 'seller/properties.html', {
        'user': user,
        'page_title': 'My Properties',
        'properties_list': properties,
        'properties_json': json.dumps(properties_json),
        'seller_properties': properties,
        'buyers': buyers,
    })

@seller_required
def seller_visits_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    seller_properties = Property.objects.filter(seller=user)
    buyers = Buyer.objects.all()

    visits_qs = VisitSchedule.objects.filter(property__seller=user).select_related('buyer', 'property').order_by('-scheduled_date', '-scheduled_time')

    today = timezone.now().date()

    visits_data = []
    for v in visits_qs:
        photo_url = ''
        if v.buyer and v.buyer.profile_pic:
            try:
                photo_url = v.buyer.profile_pic.url
            except Exception:
                photo_url = ''

        date_display = v.scheduled_date.strftime('%b %d, %Y')
        if v.scheduled_date == today:
            date_display = 'Today'
        elif v.scheduled_date == today + timezone.timedelta(days=1):
            date_display = 'Tomorrow'

        time_display = v.scheduled_time.strftime('%I:%M %p') if v.scheduled_time else ''

        prop_img = ''
        if v.property and v.property.main_image:
            try:
                prop_img = v.property.main_image.url
            except Exception:
                prop_img = ''

        can_chat = v.status in (VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED)
        chat_url = (reverse('seller_chats_page', args=[user.id]) + f'?visit_id={v.id}') if can_chat else ''

        visits_data.append({
            'id': v.id,
            'buyer_name': v.buyer.name if v.buyer else 'Anonymous Buyer',
            'buyer_email': v.buyer.email if v.buyer else '',
            'buyer_phone': getattr(v.buyer, 'phone', '') or '',
            'buyer_photo': photo_url,
            'buyer_initials': ''.join([part[0].upper() for part in (v.buyer.name if v.buyer else 'B').split()[:2]]) or 'B',
            'property_id': v.property.id if v.property else None,
            'property_title': f"{v.property.property_type} - {v.property.location}" if v.property else 'Property',
            'property_address': v.property.address if v.property else '',
            'property_price': str(v.property.price) if v.property and v.property.price else '',
            'property_img': prop_img,
            'scheduled_date': v.scheduled_date.strftime('%Y-%m-%d'),
            'date_display': date_display,
            'scheduled_time': v.scheduled_time.strftime('%H:%M') if v.scheduled_time else '',
            'time_display': time_display,
            'proposed_date': v.proposed_date.strftime('%Y-%m-%d') if v.proposed_date else '',
            'proposed_date_display': v.proposed_date.strftime('%b %d, %Y') if v.proposed_date else '',
            'proposed_time': v.proposed_time.strftime('%H:%M') if v.proposed_time else '',
            'proposed_time_display': v.proposed_time.strftime('%I:%M %p') if v.proposed_time else '',
            'decline_reason': v.decline_reason or '',
            'message': v.message or '',
            'status': v.status,
            'can_chat': can_chat,
            'created_at': v.created_at.strftime('%b %d, %Y') if v.created_at else '',
            'approve_url': reverse('approve_visit', args=[v.id]),
            'decline_url': reverse('decline_visit', args=[v.id]),
            'reschedule_url': reverse('seller_reschedule_visit', args=[v.id]),
            'complete_url': reverse('seller_complete_visit', args=[v.id]),
            'chat_url': chat_url,
        })

    counts = _get_seller_visit_counts(user)
    import json
    return render(request, 'seller/visits.html', {
        'user': user,
        'page_title': 'Scheduled Visits',
        'visits_list': visits_qs,
        'visits_json': json.dumps(visits_data),
        'seller_properties': seller_properties,
        'buyers': buyers,
        'total_count': counts['all'],
        'pending_count': counts['pending'],
        'approved_count': counts['approved'],
        'declined_count': counts['declined'],
        'rescheduled_count': counts['rescheduled'],
        'completed_count': counts['completed'],
    })

@seller_required
def seller_calendar_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    seller_properties = Property.objects.filter(seller=user)
    buyers = Buyer.objects.all()
    visits_qs = VisitSchedule.objects.filter(property__seller=user).select_related('buyer', 'property')

    calendar_events = []
    for v in visits_qs:
        calendar_events.append({
            'year': v.scheduled_date.year,
            'month': v.scheduled_date.month,
            'day': v.scheduled_date.day,
            'title': f"{v.buyer.name if v.buyer else 'Visit'} · {v.property.property_type if v.property else ''}",
            'type': 'visit',
            'time': v.scheduled_time.strftime('%I:%M %p') if v.scheduled_time else '',
            'status': v.status,
        })
    import json
    return render(request, 'seller/calendar.html', {
        'user': user,
        'page_title': 'Calendar',
        'calendar_events_json': json.dumps(calendar_events),
        'seller_properties': seller_properties,
        'buyers': buyers,
    })

@seller_required
def seller_chats_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    # Query approved and completed visits for properties owned by this seller
    visits = (
        VisitSchedule.objects.filter(
            property__seller=user,
            status__in=[VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED]
        )
        .select_related('buyer', 'property')
        .order_by('-scheduled_date', '-scheduled_time')
    )

    import urllib.parse
    conversations = []
    for v in visits:
        last_msg = v.chat_messages.order_by('-timestamp').first()
        avatar = ''
        if v.buyer and v.buyer.profile_pic:
            try:
                avatar = v.buyer.profile_pic.url
            except Exception:
                avatar = ''
        if not avatar:
            buyer_name = v.buyer.name if v.buyer else 'Buyer'
            avatar = f"https://ui-avatars.com/api/?name={urllib.parse.quote(buyer_name)}&background=4f46e5&color=fff"

        time_str = ''
        if last_msg:
            time_str = last_msg.timestamp.strftime('%I:%M %p')
        elif v.scheduled_time:
            time_str = v.scheduled_time.strftime('%I:%M %p')

        conversations.append({
            'id': v.id,
            'visit_id': v.id,
            'name': v.buyer.name if v.buyer else 'Buyer',
            'buyer_id': v.buyer_id,
            'buyer_name': v.buyer.name if v.buyer else 'Buyer',
            'property_id': v.property_id,
            'property': f"{v.property.property_type} - {v.property.location}" if v.property else '',
            'avatar': avatar,
            'last': last_msg.content if last_msg else 'No messages yet',
            'time': time_str,
            'status': v.status,
            'unread': 0,
            'online': True,
        })

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'conversations': conversations})

    initial_visit_id = request.GET.get('visit_id', '')

    import json
    return render(request, 'seller/chats.html', {
        'user': user,
        'page_title': 'Chats',
        'conversations': conversations,
        'conversations_json': json.dumps(conversations),
        'initial_visit_id': initial_visit_id,
    })

@seller_required
def seller_notifications_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/notifications.html', {'user': user, 'page_title': 'Notifications'})

@seller_required
def seller_rent_requests_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/rent_requests.html', {'user': user, 'page_title': 'Rent Requests'})

@seller_required
def seller_billing_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/billing.html', {'user': user, 'page_title': 'Billing History'})

@seller_required
def seller_analytics_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/analytics.html', {'user': user, 'page_title': 'Analytics'})

@seller_required
def seller_profile_details_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/profile.html', {'user': user, 'page_title': 'Profile'})

@seller_required
def seller_settings_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/settings.html', {'user': user, 'page_title': 'Settings'})

@seller_required
def seller_empty_states_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/empty_states.html', {'user': user, 'page_title': 'Empty States'})

@seller_required
def seller_loading_states_page(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'seller/loading_states.html', {'user': user, 'page_title': 'Loading States'})
