from datetime import timedelta, date, time
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from app.models import CustomUser, Property
from buyer.models import Buyer, VisitSchedule, Message
from auth_api.tokens import get_tokens_for_seller, get_tokens_for_buyer


class VisitScheduleWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Seller 1
        self.seller1 = CustomUser.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            phone='9999988888',
            address='Seller 1 Address',
            gender='M',
            password='Password123!',
            is_staff=False
        )

        # Create Seller 2 (for cross-ownership checks)
        self.seller2 = CustomUser.objects.create_user(
            username='seller2',
            email='seller2@example.com',
            phone='9999988889',
            address='Seller 2 Address',
            gender='F',
            password='Password123!',
            is_staff=False
        )

        # Create Buyer 1
        self.buyer1 = Buyer.objects.create(
            name='Buyer One',
            email='buyer1@example.com',
            phone='9876543210',
            address='123 Main St',
            gender='M',
            password='pbkdf2_sha256$hashed'
        )

        # Create Buyer 2
        self.buyer2 = Buyer.objects.create(
            name='Buyer Two',
            email='buyer2@example.com',
            phone='9876543211',
            address='456 Oak St',
            gender='F',
            password='pbkdf2_sha256$hashed'
        )

        # Create Property for Seller 1
        self.prop1 = Property.objects.create(
            seller=self.seller1,
            property_type='Apartment',
            location='Koramangala, Bangalore',
            address='1st Block, Koramangala',
            price=7500000,
            status='Available',
            is_approved=True
        )

        # Create Property for Seller 2
        self.prop2 = Property.objects.create(
            seller=self.seller2,
            property_type='Villa',
            location='Indiranagar, Bangalore',
            address='100 Feet Rd',
            price=15000000,
            status='Available',
            is_approved=True
        )

        # Future visit date/time
        self.future_date = timezone.now().date() + timedelta(days=3)
        self.future_time = time(14, 30)

        # Visit on Seller 1's property
        self.visit = VisitSchedule.objects.create(
            buyer=self.buyer1,
            property=self.prop1,
            scheduled_date=self.future_date,
            scheduled_time=self.future_time,
            message='Would love to inspect this apartment.',
            status=VisitSchedule.Status.PENDING
        )

    def _auth_seller(self, seller):
        self.client.force_login(seller)
        tokens = get_tokens_for_seller(seller)
        self.client.cookies['access_token'] = tokens['access']

    def _auth_buyer(self, buyer):
        self.client.logout()
        tokens = get_tokens_for_buyer(buyer)
        self.client.cookies['access_token'] = tokens['access']

    # ──────────────────────────────────────────────
    # 1. Transition Rules
    # ──────────────────────────────────────────────

    def test_approve_pending_visit(self):
        """Seller can approve a pending visit on their property."""
        self._auth_seller(self.seller1)
        url = reverse('approve_visit', args=[self.visit.id])
        res = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'approved')

        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitSchedule.Status.APPROVED)
        self.assertTrue(self.visit.is_notified)
        self.assertIsNotNone(self.visit.responded_at)

    def test_decline_pending_visit_with_reason(self):
        """Seller can decline a visit and provide a decline reason."""
        self._auth_seller(self.seller1)
        url = reverse('decline_visit', args=[self.visit.id])
        res = self.client.post(
            url,
            data={'reason': 'Owner is travelling out of town.'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'declined')

        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitSchedule.Status.DECLINED)
        self.assertEqual(self.visit.decline_reason, 'Owner is travelling out of town.')
        self.assertIsNotNone(self.visit.responded_at)

    def test_seller_reschedule_visit(self):
        """Seller can propose a new visit date and time."""
        self._auth_seller(self.seller1)
        new_date = timezone.now().date() + timedelta(days=5)
        new_time = '16:00'

        url = reverse('seller_reschedule_visit', args=[self.visit.id])
        res = self.client.post(
            url,
            data={'proposed_date': new_date.strftime('%Y-%m-%d'), 'proposed_time': new_time},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'reschedule_proposed')

        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitSchedule.Status.RESCHEDULE_PROPOSED)
        self.assertEqual(self.visit.proposed_date, new_date)
        self.assertEqual(self.visit.proposed_time, time(16, 0))

    def test_buyer_confirm_reschedule(self):
        """
        When buyer confirms reschedule:
        Copy proposed time into scheduled_date/scheduled_time and set status back to 'approved'.
        """
        # First set visit to reschedule_proposed
        new_date = timezone.now().date() + timedelta(days=4)
        new_time = time(11, 0)
        self.visit.status = VisitSchedule.Status.RESCHEDULE_PROPOSED
        self.visit.proposed_date = new_date
        self.visit.proposed_time = new_time
        self.visit.save()

        # Buyer 1 confirms
        self._auth_buyer(self.buyer1)
        url = reverse('buyer_confirm_reschedule', args=[self.visit.id])
        res = self.client.post(url)

        self.assertEqual(res.status_code, 302)  # Redirects with success message
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitSchedule.Status.APPROVED)
        self.assertEqual(self.visit.scheduled_date, new_date)
        self.assertEqual(self.visit.scheduled_time, new_time)
        self.assertIsNone(self.visit.proposed_date)
        self.assertIsNone(self.visit.proposed_time)

    def test_buyer_cancel_visit(self):
        """Buyer can cancel their visit."""
        self._auth_buyer(self.buyer1)
        url = reverse('buyer_cancel_visit', args=[self.visit.id])
        res = self.client.post(url)

        self.assertEqual(res.status_code, 302)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitSchedule.Status.CANCELLED)

    def test_seller_complete_visit(self):
        """Seller can mark an approved visit as completed."""
        self.visit.status = VisitSchedule.Status.APPROVED
        self.visit.save()

        self._auth_seller(self.seller1)
        url = reverse('seller_complete_visit', args=[self.visit.id])
        res = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(res.status_code, 200)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitSchedule.Status.COMPLETED)

    # ──────────────────────────────────────────────
    # 2. Ownership & Horizontal Access Checks
    # ──────────────────────────────────────────────

    def test_seller_cannot_act_on_another_sellers_visit(self):
        """Seller 2 cannot approve, decline, reschedule, or complete Seller 1's visit."""
        self._auth_seller(self.seller2)

        # Attempt approve
        res = self.client.post(
            reverse('approve_visit', args=[self.visit.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 404)

        # Attempt decline
        res = self.client.post(
            reverse('decline_visit', args=[self.visit.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 404)

        # Attempt reschedule
        res = self.client.post(
            reverse('seller_reschedule_visit', args=[self.visit.id]),
            data={'proposed_date': '2030-01-01', 'proposed_time': '12:00'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 404)

        # Attempt complete
        res = self.client.post(
            reverse('seller_complete_visit', args=[self.visit.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 404)

    def test_buyer_cannot_act_on_another_buyers_visit(self):
        """Buyer 2 cannot confirm reschedule or cancel Buyer 1's visit."""
        self.visit.status = VisitSchedule.Status.RESCHEDULE_PROPOSED
        self.visit.proposed_date = timezone.now().date() + timedelta(days=2)
        self.visit.proposed_time = time(10, 0)
        self.visit.save()

        self._auth_buyer(self.buyer2)

        # Confirm reschedule on Buyer 1's visit
        res = self.client.post(reverse('buyer_confirm_reschedule', args=[self.visit.id]))
        self.assertEqual(res.status_code, 404)

        # Cancel Buyer 1's visit
        res = self.client.post(reverse('buyer_cancel_visit', args=[self.visit.id]))
        self.assertEqual(res.status_code, 404)

    # ──────────────────────────────────────────────
    # 3. Double-Accept Race & Idempotency
    # ──────────────────────────────────────────────

    def test_double_accept_fails_cleanly(self):
        """Accepting an already approved visit fails cleanly with status 400."""
        self.visit.status = VisitSchedule.Status.APPROVED
        self.visit.save()

        self._auth_seller(self.seller1)
        url = reverse('approve_visit', args=[self.visit.id])
        res = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data['success'])
        self.assertIn('already approved', data['error'].lower())

    def test_accept_declined_or_cancelled_visit_fails(self):
        """Accepting a declined or cancelled visit fails cleanly with status 400."""
        self._auth_seller(self.seller1)
        url = reverse('approve_visit', args=[self.visit.id])

        # Test declined
        self.visit.status = VisitSchedule.Status.DECLINED
        self.visit.save()
        res = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 400)

        # Test cancelled
        self.visit.status = VisitSchedule.Status.CANCELLED
        self.visit.save()
        res = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 400)

    # ──────────────────────────────────────────────
    # 4. Past-Date Rejection
    # ──────────────────────────────────────────────

    def test_accept_past_date_visit_fails(self):
        """Accepting a visit whose date is in the past fails cleanly with status 400."""
        self.visit.scheduled_date = timezone.now().date() - timedelta(days=2)
        self.visit.status = VisitSchedule.Status.PENDING
        self.visit.save()

        self._auth_seller(self.seller1)
        url = reverse('approve_visit', args=[self.visit.id])
        res = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data['success'])
        self.assertIn('past', data['error'].lower())

    # ──────────────────────────────────────────────
    # 5. Chat Gate (UI & Django View Access)
    # ──────────────────────────────────────────────

    def test_seller_chat_locked_before_accept(self):
        """Seller cannot access chat if visit is pending, declined, or cancelled."""
        self._auth_seller(self.seller1)
        url = reverse('seller_chat', args=[self.visit.id, 'seller', self.seller1.id])

        # Pending -> locked
        self.visit.status = VisitSchedule.Status.PENDING
        self.visit.save()
        res = self.client.get(url)
        self.assertIn(b'Chat is locked', res.content)

        # Declined -> locked
        self.visit.status = VisitSchedule.Status.DECLINED
        self.visit.save()
        res = self.client.get(url)
        self.assertIn(b'Chat is locked', res.content)

        # Cancelled -> locked
        self.visit.status = VisitSchedule.Status.CANCELLED
        self.visit.save()
        res = self.client.get(url)
        self.assertIn(b'Chat is locked', res.content)

    def test_seller_chat_unlocked_after_accept_or_complete(self):
        """Seller chat is accessible once visit is approved or completed."""
        self._auth_seller(self.seller1)
        url = reverse('seller_chat', args=[self.visit.id, 'seller', self.seller1.id])

        # Approved -> unlocked
        self.visit.status = VisitSchedule.Status.APPROVED
        self.visit.save()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Chat with', res.content)

        # Completed -> unlocked
        self.visit.status = VisitSchedule.Status.COMPLETED
        self.visit.save()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Chat with', res.content)

    def test_buyer_chat_locked_before_accept(self):
        """Buyer chat view rejects access until visit is approved or completed."""
        self._auth_buyer(self.buyer1)
        url = reverse('chat', args=[self.visit.id, 'buyer', self.buyer1.id])

        self.visit.status = VisitSchedule.Status.PENDING
        self.visit.save()
        res = self.client.get(url)
        self.assertIn(b'Chat is locked', res.content)

        self.visit.status = VisitSchedule.Status.DECLINED
        self.visit.save()
        res = self.client.get(url)
        self.assertIn(b'Chat is locked', res.content)

    def test_buyer_chat_unlocked_after_accept(self):
        """Buyer chat view works when visit is approved."""
        self._auth_buyer(self.buyer1)
        url = reverse('chat', args=[self.visit.id, 'buyer', self.buyer1.id])

        self.visit.status = VisitSchedule.Status.APPROVED
        self.visit.save()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Chat with', res.content)
