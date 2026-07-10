import base64
import hashlib
import hmac
import json
import time

from django.test import TestCase, override_settings

from .models import CustomUser, UserProfile


class ClerkWebhookTests(TestCase):
    signing_key = b'local-webhook-test-key'

    def _headers(self, body):
        webhook_id = 'msg_test_123'
        timestamp = str(int(time.time()))
        payload = f'{webhook_id}.{timestamp}.'.encode() + body
        signature = base64.b64encode(hmac.new(self.signing_key, payload, hashlib.sha256).digest()).decode()
        return {
            'HTTP_SVIX_ID': webhook_id,
            'HTTP_SVIX_TIMESTAMP': timestamp,
            'HTTP_SVIX_SIGNATURE': f'v1,{signature}',
        }

    @override_settings(CLERK_WEBHOOK_SIGNING_SECRET='whsec_bG9jYWwtd2ViaG9vay10ZXN0LWtleQ')
    def test_user_deleted_event_removes_local_user_and_profile(self):
        user = CustomUser.objects.create_user(
            email='deleted@example.com', name='Deleted User', clerk_user_id='user_deleted_test'
        )
        UserProfile.objects.create(user=user)
        body = json.dumps({'type': 'user.deleted', 'data': {'id': user.clerk_user_id}}).encode()

        response = self.client.post(
            '/api/accounts/clerk-webhook/', body, content_type='application/json', **self._headers(body)
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(pk=user.pk).exists())
        self.assertFalse(UserProfile.objects.filter(user_id=user.pk).exists())

    def test_unsigned_webhook_is_rejected(self):
        response = self.client.post('/api/accounts/clerk-webhook/', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 401)
