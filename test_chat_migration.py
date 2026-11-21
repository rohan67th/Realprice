"""
test_chat_migration.py

Automated test suite verifying the Seller <-> Buyer chat migration:
- Seller A accessing their conversations on new seller chat
- Seller B forbidden from Seller A's conversations
- Buyer A accessing their conversations
- Buyer B forbidden from Buyer A's conversation
- Unauthenticated access rejected
- Chat gate checks: Pending, Declined, Cancelled -> 403
- Chat gate checks: Approved, Completed -> 200
- Sending message: seller -> FastAPI -> database
- Sending message: buyer -> FastAPI -> database
- Message history retrieval and participant checks
"""

import os
import django
import json
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_prediction.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.utils import timezone
from app.models import CustomUser, Property
from buyer.models import Buyer, VisitSchedule, Message
from auth_api.tokens import get_tokens_for_seller, get_tokens_for_buyer


class ChatMigrationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()

        # Create Seller A
        cls.seller_a, _ = CustomUser.objects.get_or_create(
            username='test_seller_a',
            defaults={
                'email': 'seller_a@test.com',
                'phone': '1112223333',
                'address': 'Seller A St',
                'gender': 'Male',
                'role': 'seller',
                'is_staff': False,
            }
        )
        cls.seller_a.set_password('Password123!')
        cls.seller_a.save()

        # Create Seller B
        cls.seller_b, _ = CustomUser.objects.get_or_create(
            username='test_seller_b',
            defaults={
                'email': 'seller_b@test.com',
                'phone': '4445556666',
                'address': 'Seller B Ave',
                'gender': 'Female',
                'role': 'seller',
                'is_staff': False,
            }
        )
        cls.seller_b.set_password('Password123!')
        cls.seller_b.save()

        # Create Buyer A
        cls.buyer_a, _ = Buyer.objects.get_or_create(
            email='buyer_a@test.com',
            defaults={
                'name': 'Buyer A',
                'phone': '1234567890',
                'address': 'Buyer A St',
                'gender': 'M',
            }
        )
        cls.buyer_a.set_password('Password123!')
        cls.buyer_a.save()

        # Create Buyer B
        cls.buyer_b, _ = Buyer.objects.get_or_create(
            email='buyer_b@test.com',
            defaults={
                'name': 'Buyer B',
                'phone': '0987654321',
                'address': 'Buyer B Ave',
                'gender': 'F',
            }
        )
        cls.buyer_b.set_password('Password123!')
        cls.buyer_b.save()

        # Create Property for Seller A
        cls.prop_a, _ = Property.objects.get_or_create(
            slug='prop-seller-a-test',
            defaults={
                'seller': cls.seller_a,
                'property_type': 'Apartment',
                'location': 'Downtown',
                'price': 2500000,
                'is_approved': True,
                'approval_status': 'approved',
                'status': 'Available',
            }
        )

        # Create Visits with various statuses for Buyer A and Seller A
        cls.approved_visit, _ = VisitSchedule.objects.get_or_create(
            buyer=cls.buyer_a,
            property=cls.prop_a,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
            status='approved',
        )

        cls.pending_visit, _ = VisitSchedule.objects.get_or_create(
            buyer=cls.buyer_a,
            property=cls.prop_a,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
            status='pending',
        )

        cls.completed_visit, _ = VisitSchedule.objects.get_or_create(
            buyer=cls.buyer_a,
            property=cls.prop_a,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
            status='completed',
        )

        cls.declined_visit, _ = VisitSchedule.objects.get_or_create(
            buyer=cls.buyer_a,
            property=cls.prop_a,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
            status='declined',
        )

        cls.cancelled_visit, _ = VisitSchedule.objects.get_or_create(
            buyer=cls.buyer_a,
            property=cls.prop_a,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
            status='cancelled',
        )

    @classmethod
    def tearDownClass(cls):
        Message.objects.filter(visit__property=cls.prop_a).delete()
        VisitSchedule.objects.filter(property=cls.prop_a).delete()
        Property.objects.filter(id=cls.prop_a.id).delete()
        Buyer.objects.filter(id__in=[cls.buyer_a.id, cls.buyer_b.id]).delete()
        CustomUser.objects.filter(id__in=[cls.seller_a.id, cls.seller_b.id]).delete()
        super().tearDownClass()

    def _auth_seller(self, user):
        client = Client()
        client.force_login(user)
        tokens = get_tokens_for_seller(user)
        client.cookies['access_token'] = tokens['access']
        client.cookies['refresh_token'] = tokens['refresh']
        return client, tokens['access']

    def _auth_buyer(self, buyer):
        client = Client()
        tokens = get_tokens_for_buyer(buyer)
        client.cookies['access_token'] = tokens['access']
        client.cookies['refresh_token'] = tokens['refresh']
        return client, tokens['access']

    # 1. Unauthenticated user rejected
    def test_unauthenticated_user_cannot_access_chat(self):
        client = Client()
        res = client.get(f'/seller_profile/{self.seller_a.id}/chats/')
        # Redirects to login
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

        # API send message without auth rejected
        res = client.post(
            '/api/messaging/send/',
            data=json.dumps({'visit_id': self.approved_visit.id, 'content': 'Hi'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 401)

    # 2. Seller A can view their new chats page
    def test_seller_a_can_view_new_chats_page(self):
        client, _ = self._auth_seller(self.seller_a)
        res = client.get(f'/seller_profile/{self.seller_a.id}/chats/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Chats', res.content)
        self.assertIn(b'chat-thread', res.content)
        self.assertIn(b'seller-conversations-data', res.content)
        # Should contain Buyer A's name in JSON data
        self.assertIn(b'Buyer A', res.content)

    # 3. Seller B cannot access Seller A's chat page
    def test_seller_b_cannot_access_seller_a_chats(self):
        client, _ = self._auth_seller(self.seller_b)
        res = client.get(f'/seller_profile/{self.seller_a.id}/chats/')
        # seller_required raises Http404 on mismatched owner_id
        self.assertEqual(res.status_code, 404)

    # 4. Chat Gate: Pending, Declined, Cancelled visits rejected
    def test_chat_gate_rejected_statuses(self):
        client, _ = self._auth_seller(self.seller_a)

        for visit in [self.pending_visit, self.declined_visit, self.cancelled_visit]:
            res = client.post(
                '/api/messaging/send/',
                data=json.dumps({'visit_id': visit.id, 'content': 'Test gate'}),
                content_type='application/json'
            )
            self.assertEqual(res.status_code, 403)
            self.assertIn('approved or completed', res.json().get('detail', '').lower())

            res_hist = client.get(f'/api/messaging/history/{visit.id}/')
            self.assertEqual(res_hist.status_code, 403)

    # 5. Chat Gate: Approved and Completed visits allowed
    def test_chat_gate_approved_and_completed_allowed(self):
        client_s, _ = self._auth_seller(self.seller_a)
        client_b, _ = self._auth_buyer(self.buyer_a)

        for visit in [self.approved_visit, self.completed_visit]:
            # Seller sends message
            res_s = client_s.post(
                '/api/messaging/send/',
                data=json.dumps({'visit_id': visit.id, 'content': f'Hello on {visit.status}'}),
                content_type='application/json'
            )
            self.assertEqual(res_s.status_code, 200)
            self.assertTrue(res_s.json().get('success'))

            # Buyer sends message
            res_b = client_b.post(
                '/api/messaging/send/',
                data=json.dumps({'visit_id': visit.id, 'content': f'Buyer reply on {visit.status}'}),
                content_type='application/json'
            )
            self.assertEqual(res_b.status_code, 200)
            self.assertTrue(res_b.json().get('success'))

            # History accessible
            res_hist = client_s.get(f'/api/messaging/history/{visit.id}/')
            self.assertEqual(res_hist.status_code, 200)
            msgs = res_hist.json().get('messages', [])
            self.assertGreaterEqual(len(msgs), 2)

    # 6. Unauthorized Seller B cannot message Seller A's visit
    def test_unauthorized_seller_b_cannot_message_or_view(self):
        client_b, _ = self._auth_seller(self.seller_b)
        res = client_b.post(
            '/api/messaging/send/',
            data=json.dumps({'visit_id': self.approved_visit.id, 'content': 'Imposter seller'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn('not the seller', res.json().get('detail', '').lower())

        res_hist = client_b.get(f'/api/messaging/history/{self.approved_visit.id}/')
        self.assertEqual(res_hist.status_code, 403)

    # 7. Unauthorized Buyer B cannot message Buyer A's visit
    def test_unauthorized_buyer_b_cannot_message_or_view(self):
        client_bb, _ = self._auth_buyer(self.buyer_b)
        res = client_bb.post(
            '/api/messaging/send/',
            data=json.dumps({'visit_id': self.approved_visit.id, 'content': 'Imposter buyer'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn('not the buyer', res.json().get('detail', '').lower())

        res_hist = client_bb.get(f'/api/messaging/history/{self.approved_visit.id}/')
        self.assertEqual(res_hist.status_code, 403)

    # 8. Both Seller and Buyer see identical message records
    def test_seller_and_buyer_share_same_messages(self):
        client_s, _ = self._auth_seller(self.seller_a)
        client_b, _ = self._auth_buyer(self.buyer_a)

        unique_seller_msg = f"Seller msg {timezone.now().timestamp()}"
        unique_buyer_msg = f"Buyer msg {timezone.now().timestamp()}"

        # 1. Seller sends
        r1 = client_s.post(
            '/api/messaging/send/',
            data=json.dumps({'visit_id': self.approved_visit.id, 'content': unique_seller_msg}),
            content_type='application/json'
        )
        self.assertEqual(r1.status_code, 200)

        # 2. Buyer sends
        r2 = client_b.post(
            '/api/messaging/send/',
            data=json.dumps({'visit_id': self.approved_visit.id, 'content': unique_buyer_msg}),
            content_type='application/json'
        )
        self.assertEqual(r2.status_code, 200)

        # 3. Seller reads history
        hist_s = client_s.get(f'/api/messaging/history/{self.approved_visit.id}/').json().get('messages', [])
        s_contents = [m['content'] for m in hist_s]
        self.assertIn(unique_seller_msg, s_contents)
        self.assertIn(unique_buyer_msg, s_contents)

        # 4. Buyer reads history
        hist_b = client_b.get(f'/api/messaging/history/{self.approved_visit.id}/').json().get('messages', [])
        b_contents = [m['content'] for m in hist_b]
        self.assertIn(unique_seller_msg, b_contents)
        self.assertIn(unique_buyer_msg, b_contents)

        # Verify sender roles
        last_s = next(m for m in hist_s if m['content'] == unique_seller_msg)
        last_b = next(m for m in hist_s if m['content'] == unique_buyer_msg)
        self.assertEqual(last_s['sender_seller_id'], self.seller_a.id)
        self.assertIsNone(last_s['sender_buyer_id'])
        self.assertEqual(last_b['sender_buyer_id'], self.buyer_a.id)
        self.assertIsNone(last_b['sender_seller_id'])


if __name__ == '__main__':
    unittest.main()
