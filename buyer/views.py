from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from app.models import Property
from .models import Buyer, PasswordResetBuyer, BuyerInterest
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth import logout
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest, Http404
from django.db import transaction
from django.utils import timezone
from .models import RentRequest, VisitSchedule

# JWT helpers
from auth_api.tokens import get_tokens_for_buyer, set_jwt_cookies, clear_jwt_cookies
from auth_api.decorators import buyer_jwt_required
from rest_framework_simplejwt.tokens import RefreshToken
import httpx


def buyer_registration(request):
    if request.method == "POST":
        # Extract data from the POST request
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        gender = request.POST.get('gender')
        profile_pic = request.FILES.get('profile_pic')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')


        if not name or not email or not phone or not address or not gender or not password:
            messages.error(request, "All fields are required.")
            return redirect('register')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')
        
        try:
            faculty = Buyer(
                name=name,
                email=email,
                phone=phone,
                address=address,
                gender=gender,
                profile_pic=profile_pic
            )
            # Hash the password before saving it
            faculty.set_password(password)
            faculty.save()

            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')

        except ValidationError as e:
            messages.error(request, f"Error: {e}")
            return redirect('buyer_registration')

    return render(request, 'buyer_registration.html')



# buyer_login has been merged into unified_login in app/views.py


@buyer_jwt_required
def buyer_landing(request):
    buyer = request.current_buyer   # set by JWTAuthMiddleware
    properties = Property.objects.filter(is_approved=True)
    return render(request, 'buyer_landing.html', {'buyer': buyer, 'properties': properties})

@buyer_jwt_required
def property_detail_buyer(request, buyer_id, pk):
    from . import views_pages
    return views_pages.buyer_property_detail_view(request, pk, buyer_id=buyer_id)


@buyer_jwt_required
def buyer_profile(request, user_id):
    buyer = get_object_or_404(Buyer, id=user_id)
    saved_count = buyer.saved_properties.count()
    tours_count = buyer.visitschedule_set.count()
    interests_count = buyer.buyerinterest_set.count()
    complaints_count = buyer.complaint_set.count()

    activities = []
    try:
        for visit in buyer.visitschedule_set.select_related('property').order_by('-created_at')[:3]:
            prop_title = getattr(visit.property, 'property_type', 'Property')
            activities.append({
                'icon': 'ri-calendar-check-line',
                'title': f'Tour booked for {prop_title}',
                'detail': f'{visit.scheduled_date} at {visit.scheduled_time} ({visit.get_status_display()})',
                'when': visit.created_at.strftime('%d %b %Y') if visit.created_at else ''
            })
        for interest in buyer.buyerinterest_set.select_related('property').order_by('-timestamp')[:3]:
            prop_title = getattr(interest.property, 'property_type', 'Property')
            activities.append({
                'icon': 'ri-heart-3-line',
                'title': f'Interest sent for {prop_title}',
                'detail': f'Status: {interest.status}',
                'when': interest.timestamp.strftime('%d %b %Y') if interest.timestamp else ''
            })
        for complaint in buyer.complaint_set.order_by('-created_at')[:2]:
            activities.append({
                'icon': 'ri-customer-service-2-line',
                'title': f'Complaint submitted ({complaint.get_category_display()})',
                'detail': f'Status: {complaint.get_status_display()}',
                'when': complaint.created_at.strftime('%d %b %Y') if complaint.created_at else ''
            })
    except Exception:
        pass

    return render(request, 'buyer_profile.html', {
        'buyer': buyer,
        'saved_count': saved_count,
        'tours_count': tours_count,
        'interests_count': interests_count,
        'complaints_count': complaints_count,
        'activities': activities[:6],
    })


def seller_logout(request):
    logout(request)
    response = redirect('/')
    clear_jwt_cookies(response)
    return response



def edit_profile_buyer(request,user_id):

    buyer = get_object_or_404(Buyer, id=user_id)

    if request.method == 'POST':
        buyer.name = request.POST.get('name')
        buyer.email = request.POST.get('email')
        buyer.phone = request.POST.get('phone')
        buyer.address = request.POST.get('address')
        buyer.gender = request.POST.get('gender')

        if 'profile_pic' in request.FILES:
            buyer.profile_pic = request.FILES['profile_pic']

        buyer.save()

        messages.success(request, "Profile updated successfully!")
        profile_url = reverse('buyer_profile', kwargs={'user_id': buyer.id})
        return redirect(profile_url)

    return render(request, 'edit_buyer.html', {'user': buyer})




#Forget password

from django.utils import timezone

def forget_password_buyer(request):
    
    if request.method =="POST":
        email = request.POST.get('email')

        try:
            user = Buyer.objects.get(email=email)

            new_password_reset = PasswordResetBuyer(user=user)
            new_password_reset.save()

            password_reset_url = reverse('reset-password-buyer', kwargs={'reset_id': new_password_reset.reset_id})

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

            return HttpResponseRedirect(reverse("password-reset-sent-buyer", kwargs={"reset_id": new_password_reset.reset_id}))
        
        except Buyer.DoesNotExist:
            messages.error(request, f"No user with email '{email}' found")
            return redirect('forgot-password-buyer')

    return render(request,'forget_password_buyer.html')


def password_reset_sent_buyer(request,reset_id):

    if PasswordResetBuyer.objects.filter(reset_id=reset_id).exists():
        return render(request, 'password_reset_sent_buyer.html')
    else:
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password-buyer')


def reset_password_buyer(request,reset_id):
    
    try:
        password_reset_id = PasswordResetBuyer.objects.get(reset_id=reset_id)

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
                return redirect('reset-password-buyer',reset_id=reset_id)

    
    
    except PasswordResetBuyer.DoesNotExist:
        
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password-buyer')

    return render(request, 'reset_password_buyer.html',{'reset_id': reset_id})



def show_interest(request, property_id):
    if request.method == 'POST':
        property_obj = get_object_or_404(Property, id=property_id)

        buyer = get_object_or_404(Buyer, email=request.user.email)

        interest, created = BuyerInterest.objects.get_or_create(
            buyer=buyer,
            property=property_obj
        )

        if not created:
            messages.info(request, "You've already expressed interest.")
        else:
            messages.success(request, "Your interest has been submitted.")

        return redirect('property_detail', property_id=property_id)








#price prediction

# ML inference is now handled by the FastAPI Microservice at http://localhost:8001
# We no longer load models or scalers locally in Django to save memory and improve async performance.


def price_prediction_view(request):
    """
    ML property price prediction view.
    Accepts POST with the 8 features, calls FastAPI POST /api/ml/predict,
    and returns a JSON response.
    """
    if request.method == 'POST':
        try:
            features = [
                float(request.POST["MedInc"]),
                float(request.POST["HouseAge"]),
                float(request.POST["AveRooms"]),
                float(request.POST["AveBedrms"]),
                float(request.POST["Population"]),
                float(request.POST["AveOccup"]),
                float(request.POST["Latitude"]),
                float(request.POST["Longitude"]),
            ]
        except (KeyError, ValueError) as e:
            return JsonResponse({
                'success': False,
                'error': f"Invalid or missing feature: {str(e)}"
            })

        fastapi_url = "http://127.0.0.1:8001/api/ml/predict"
        headers = {"Content-Type": "application/json"}

        # Pass JWT if present or generate for buyer
        access_token = request.COOKIES.get('access_token')
        if not access_token:
            try:
                r = RefreshToken()
                r['role'] = 'buyer'
                r['user_id'] = getattr(getattr(request, 'current_buyer', None), 'id', 1)
                access_token = str(r.access_token)
            except Exception:
                access_token = None

        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(fastapi_url, json={"features": features}, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    predicted_price = data.get('predicted_price', data.get('prediction'))
                    return JsonResponse({
                        'success': True,
                        'predicted_price': predicted_price,
                        'prediction': predicted_price,
                    })
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get('detail', err_data.get('error', response.text))
                    except Exception:
                        error_msg = response.text or f"ML service error ({response.status_code})"
                    return JsonResponse({'success': False, 'error': error_msg})
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return JsonResponse({'success': False, 'error': "ML service is unavailable"})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f"Prediction request failed: {str(e)}"})

    # GET request renders the price prediction page
    buyer = getattr(request, 'current_buyer', None)
    return render(request, 'price_prediction.html', {'buyer': buyer})


# Alias for clarity
predict_ml_price = price_prediction_view



def price_prediction_page(request):
    """Renders the redesigned price prediction page that matches the buyer landing design."""
    buyer = getattr(request, 'current_buyer', None)
    return render(request, 'price_prediction.html', {'buyer': buyer})






#Schedule a visit
from .models import VisitSchedule

def schedule_visit(request, buyer_id, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    buyer = get_object_or_404(Buyer, id=buyer_id)

    if request.method == "POST":
        scheduled_date = request.POST.get("scheduled_date")
        scheduled_time = request.POST.get("scheduled_time")
        message = request.POST.get("message")

        VisitSchedule.objects.create(
            buyer=buyer,
            property=property_obj,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            message=message,
        )
        return redirect('visit_success')  # Or redirect back to the property page

    return render(request, 'schedule_visit.html', {
        'property': property_obj,
        'buyer': buyer,
    })



def visit_success(request):
    return render(request, 'visit_success.html')


def send_rent_request(request, property_id, buyer_id):
    buyer = get_object_or_404(Buyer, id=buyer_id)
    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == 'POST':
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']

        RentRequest.objects.create(
            property=property_obj,
            buyer=buyer,
            start_date=start_date,
            end_date=end_date
        )
        return redirect('property_detail_buyer',buyer_id=buyer.id, pk=property_obj.id)

    return render(request, 'rent_request.html', {'property': property_obj, 'buyer': buyer})

def rent(request):
    return render(request,'rent_request.html')


#Notifications

def buyer_notifications(request, buyer_id):
    buyer = get_object_or_404(Buyer, id=buyer_id)

    # 1. Synthesized Visit notifications: approved, declined, reschedule_proposed, cancelled
    notifications = (
        VisitSchedule.objects.filter(buyer=buyer)
        .exclude(status=VisitSchedule.Status.PENDING)
        .select_related('property', 'property__seller')
        .order_by('-responded_at', '-created_at')
    )

    # 2. Rent payments (assuming is_paid=True and not yet seen)
    rent_notifications = RentRequest.objects.filter(
        buyer=buyer,
        status='approved',
        is_paid=True,
        is_seen_by_buyer=False
    )

    # 3. Approved/Declined rent request updates (excluding pending)
    approval_notifications = RentRequest.objects.filter(
        buyer=buyer,
    ).exclude(status='pending').order_by('-updated_at')

    return render(request, 'buyer_notifications.html', {
        'buyer': buyer,
        'notifications': notifications,
        'rent_notifications': rent_notifications,
        'approval_notifications': approval_notifications,
    })


@buyer_jwt_required
def buyer_confirm_reschedule(request, visit_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    buyer = request.current_buyer
    with transaction.atomic():
        visit = (
            VisitSchedule.objects
            .select_for_update()
            .select_related('property')
            .filter(id=visit_id, buyer=buyer)
            .first()
        )
        if not visit:
            raise Http404("Visit not found or not owned by you.")

        if visit.status != VisitSchedule.Status.RESCHEDULE_PROPOSED:
            messages.error(request, f"Cannot confirm reschedule for a visit with status '{visit.status}'.")
            return redirect('buyer_notifications', buyer_id=buyer.id)

        if not visit.proposed_date or not visit.proposed_time:
            messages.error(request, "No proposed date or time found on this visit.")
            return redirect('buyer_notifications', buyer_id=buyer.id)

        # Copy proposed time into scheduled_date / scheduled_time and set status back to 'approved'
        visit.scheduled_date = visit.proposed_date
        visit.scheduled_time = visit.proposed_time
        visit.proposed_date = None
        visit.proposed_time = None
        visit.status = VisitSchedule.Status.APPROVED
        visit.is_seen_by_buyer = True
        visit.responded_at = timezone.now()
        visit.save()

    messages.success(request, f"Reschedule confirmed! Visit to {visit.property.property_type} is confirmed for {visit.scheduled_date} at {visit.scheduled_time}.")
    return redirect('buyer_notifications', buyer_id=buyer.id)


@buyer_jwt_required
def buyer_cancel_visit(request, visit_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    buyer = request.current_buyer
    with transaction.atomic():
        visit = (
            VisitSchedule.objects
            .select_for_update()
            .filter(id=visit_id, buyer=buyer)
            .first()
        )
        if not visit:
            raise Http404("Visit not found or not owned by you.")

        if visit.status in (VisitSchedule.Status.CANCELLED, VisitSchedule.Status.COMPLETED):
            messages.error(request, f"Visit is already {visit.status}.")
            return redirect('buyer_notifications', buyer_id=buyer.id)

        visit.status = VisitSchedule.Status.CANCELLED
        visit.responded_at = timezone.now()
        visit.save()

    messages.info(request, "Your visit has been cancelled.")
    return redirect('buyer_notifications', buyer_id=buyer.id)


# chat

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Message, VisitSchedule, Buyer
from app.models import CustomUser


@csrf_exempt
def send_message(request):
    """
    Proxy to FastAPI messaging service (/api/messaging/send).
    csrf_exempt is used because this is a JSON REST API endpoint authenticating
    via JWT access_token (either from cookies or active session).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fastapi_url = "http://127.0.0.1:8001/api/messaging/send"

            access_token = request.COOKIES.get('access_token')
            if not access_token:
                if request.user.is_authenticated:
                    from auth_api.tokens import get_tokens_for_seller
                    access_token = get_tokens_for_seller(request.user)['access']
                elif getattr(request, 'current_buyer', None):
                    from auth_api.tokens import get_tokens_for_buyer
                    access_token = get_tokens_for_buyer(request.current_buyer)['access']

            headers = {"Content-Type": "application/json"}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            with httpx.Client(timeout=10.0) as client:
                response = client.post(fastapi_url, json=data, headers=headers)
                return JsonResponse(response.json(), status=response.status_code)
        except httpx.RequestError:
            return JsonResponse({'error': 'FastAPI messaging service unavailable'}, status=503)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Only POST allowed'}, status=405)


def get_messages(request, visit_id):
    """
    Proxy to FastAPI messaging service (/api/messaging/history/{visit_id}).
    Authenticates via JWT access_token (cookie or active session).
    """
    fastapi_url = f"http://127.0.0.1:8001/api/messaging/history/{visit_id}"

    access_token = request.COOKIES.get('access_token')
    if not access_token:
        if request.user.is_authenticated:
            from auth_api.tokens import get_tokens_for_seller
            access_token = get_tokens_for_seller(request.user)['access']
        elif getattr(request, 'current_buyer', None):
            from auth_api.tokens import get_tokens_for_buyer
            access_token = get_tokens_for_buyer(request.current_buyer)['access']

    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(fastapi_url, headers=headers)
            if response.status_code == 200:
                messages_data = response.json()
                formatted_messages = []
                for msg in messages_data:
                    sender_name = 'Buyer' if msg.get('sender_buyer_id') else 'Seller'
                    formatted_messages.append({
                        'id': msg.get('id'),
                        'visit_id': msg.get('visit_id', visit_id),
                        'sender': sender_name,
                        'sender_buyer_id': msg.get('sender_buyer_id'),
                        'sender_seller_id': msg.get('sender_seller_id'),
                        'content': msg.get('content', ''),
                        'timestamp': msg.get('timestamp')
                    })
                return JsonResponse({'messages': formatted_messages, 'success': True})
            return JsonResponse(response.json(), status=response.status_code)
    except httpx.RequestError:
        return JsonResponse({'error': 'FastAPI messaging service unavailable'}, status=503)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def chat_view(request, visit_id, sender_type, sender_id):
    visit = get_object_or_404(VisitSchedule, id=visit_id)

    # Chat gate: only approved and completed visits unlock chat
    if visit.status not in (VisitSchedule.Status.APPROVED, VisitSchedule.Status.COMPLETED):
        return render(request, 'chat/not_approved.html', {'message': 'Chat is locked until the seller accepts the visit.'})

    # Ownership / participant checks
    if sender_type == 'buyer':
        if visit.buyer_id != sender_id:
            raise Http404("Buyer not authorized for this visit chat.")
        if request.jwt_role == 'buyer' and request.current_buyer and request.current_buyer.id != sender_id:
            raise Http404("Unauthorized buyer access.")
    elif sender_type == 'seller':
        if visit.property.seller_id != sender_id:
            raise Http404("Seller not authorized for this visit chat.")
        if request.user.is_authenticated and request.user.id != sender_id:
            raise Http404("Unauthorized seller access.")
    else:
        return render(request, 'chat/invalid_sender.html')

    if request.method == 'POST':
        content = request.POST.get('content')
        msg_data = {'visit': visit, 'content': content}

        if sender_type == 'buyer':
            buyer = get_object_or_404(Buyer, id=sender_id)
            msg_data['sender_buyer'] = buyer
        elif sender_type == 'seller':
            seller = get_object_or_404(CustomUser, id=sender_id)
            msg_data['sender_seller'] = seller

        Message.objects.create(**msg_data)
        return redirect('chat', visit_id=visit.id, sender_type=sender_type, sender_id=sender_id)

    messages = visit.chat_messages.order_by('timestamp')

    return render(request, 'chat.html', {
        'visit': visit,
        'messages': messages,
        'sender_type': sender_type,
        'sender_id': sender_id,
        'error': 'Invalid sender type.'
    })


from .models import Complaint

#complaints
def submit_complaint(request, property_id,buyer_id):
    if request.method == 'POST':
        category = request.POST.get('category')
        priority = request.POST.get('priority')
        description = request.POST.get('description')

        property_obj = get_object_or_404(Property, id=property_id)
        buyer = get_object_or_404(Buyer, id=buyer_id)

        Complaint.objects.create(
            property=property_obj,
            buyer=buyer,
            category=category,
            priority=priority,
            description=description
        )

        messages.success(request, 'Your complaint has been submitted successfully.')
        return redirect('property_detail_buyer', buyer_id=buyer_id, pk=property_id)



def buyer_complaints(request, buyer_id):
    buyer = get_object_or_404(Buyer, id=buyer_id)
    complaints = Complaint.objects.filter(buyer=buyer)
    return render(request, 'complaints.html', {'buyer': buyer, 'complaints': complaints})



from .utils import predict_future_price

def predict_future_price_view(request, property_id):
    """Future price projection proxy for an existing property."""
    fastapi_url = f"http://127.0.0.1:8001/api/ml/predict/future/{property_id}"
    
    access_token = request.COOKIES.get('access_token')
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(fastapi_url, headers=headers)
            if response.status_code == 200:
                return JsonResponse({'success': True, **response.json()})
            return JsonResponse({'success': False, 'error': response.text})
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return JsonResponse({'success': False, 'error': "ML service is unavailable"})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Backward-compatible alias
predict_price_view = predict_future_price_view




