import os
import unittest
from unittest.mock import Mock, patch

from src import paypal_payments


TEST_ENV = {
    'PAYPAL_MODE': 'sandbox',
    'PAYPAL_CLIENT_ID': 'sandbox-client-id',
    'PAYPAL_CLIENT_SECRET': 'sandbox-client-secret',
    'PAYPAL_WEBHOOK_ID': 'sandbox-webhook-id',
    'PAYPAL_PRO_PLAN_ID': 'P-PRO-PLAN',
    'PAYPAL_PREMIUM_PLAN_ID': 'P-PREMIUM-PLAN',
    'PAYPAL_PUBLIC_BASE_URL': 'https://trading.example.test'
}


class TestPayPalPayments(unittest.TestCase):
    def test_sandbox_settings_require_all_credentials_and_plan_ids(self):
        with patch.dict(os.environ, {'PAYPAL_MODE': 'sandbox'}, clear=True):
            self.assertFalse(paypal_payments.is_configured())
            with self.assertRaises(paypal_payments.PayPalConfigurationError):
                paypal_payments.plan_id('PRO')

        with patch.dict(os.environ, TEST_ENV, clear=True):
            self.assertTrue(paypal_payments.is_configured())
            self.assertEqual(paypal_payments.plan_id('PRO'), 'P-PRO-PLAN')
            self.assertEqual(paypal_payments.plan_amount('PREMIUM'), 19.99)

    def test_production_mode_and_insecure_public_redirect_are_rejected(self):
        with patch.dict(os.environ, {**TEST_ENV, 'PAYPAL_MODE': 'production'}, clear=True):
            self.assertFalse(paypal_payments.is_configured())

        with patch.dict(
            os.environ,
            {**TEST_ENV, 'PAYPAL_PUBLIC_BASE_URL': 'http://public.example.test'},
            clear=True
        ):
            self.assertFalse(paypal_payments.is_configured())

    def test_subscription_creation_uses_sandbox_plan_and_fixed_redirects(self):
        token_response = Mock(ok=True)
        token_response.json.return_value = {'access_token': 'sandbox-token'}
        create_response = Mock(ok=True, content=b'{"id":"I-SUB"}')
        create_response.json.return_value = {'id': 'I-SUB'}
        with patch.dict(os.environ, TEST_ENV, clear=True), \
                patch.object(paypal_payments.requests, 'post', return_value=token_response), \
                patch.object(paypal_payments.requests, 'request', return_value=create_response) as send:
            result = paypal_payments.create_subscription(
                'PRO', user_id=42, request_id='request-42'
            )

        self.assertEqual(result['id'], 'I-SUB')
        method, url = send.call_args.args[:2]
        self.assertEqual(method, 'POST')
        self.assertEqual(
            url,
            'https://api-m.sandbox.paypal.com/v1/billing/subscriptions'
        )
        self.assertEqual(send.call_args.kwargs['headers']['PayPal-Request-Id'], 'request-42')
        payload = send.call_args.kwargs['json']
        self.assertEqual(payload['plan_id'], 'P-PRO-PLAN')
        self.assertEqual(payload['custom_id'], 'trading-platform:user:42:plan:PRO')
        self.assertEqual(
            payload['application_context']['return_url'],
            'https://trading.example.test/billing/paypal/return'
        )

    def test_webhook_signature_is_verified_by_paypal_before_acceptance(self):
        token_response = Mock(ok=True)
        token_response.json.return_value = {'access_token': 'sandbox-token'}
        verify_response = Mock(ok=True, content=b'{"verification_status":"SUCCESS"}')
        verify_response.json.return_value = {'verification_status': 'SUCCESS'}
        headers = {
            'PAYPAL-AUTH-ALGO': 'SHA256withRSA',
            'PAYPAL-CERT-URL': 'https://api.paypal.com/cert',
            'PAYPAL-TRANSMISSION-ID': 'transmission-1',
            'PAYPAL-TRANSMISSION-SIG': 'signature',
            'PAYPAL-TRANSMISSION-TIME': '2026-01-01T00:00:00Z'
        }
        event = {'id': 'event-1', 'event_type': 'BILLING.SUBSCRIPTION.ACTIVATED'}
        with patch.dict(os.environ, TEST_ENV, clear=True), \
                patch.object(paypal_payments.requests, 'post', return_value=token_response), \
                patch.object(paypal_payments.requests, 'request', return_value=verify_response) as send:
            verified = paypal_payments.verify_webhook(headers, event)

        self.assertTrue(verified)
        payload = send.call_args.kwargs['json']
        self.assertEqual(payload['webhook_id'], 'sandbox-webhook-id')
        self.assertEqual(payload['webhook_event'], event)

    def test_webhook_without_signature_headers_is_rejected_without_provider_call(self):
        with patch.dict(os.environ, TEST_ENV, clear=True), \
                patch.object(paypal_payments.requests, 'post') as oauth, \
                patch.object(paypal_payments.requests, 'request') as verify:
            self.assertFalse(paypal_payments.verify_webhook({}, {'id': 'bad'}))

        oauth.assert_not_called()
        verify.assert_not_called()


if __name__ == '__main__':
    unittest.main()
