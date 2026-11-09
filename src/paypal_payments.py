"""PayPal sandbox subscription helpers.

The module never stores or logs merchant credentials. Production processing is
intentionally disabled until it receives a separate review and deployment config.
"""

import os
from urllib.parse import urlparse

import requests


PLAN_AMOUNTS_USD = {'PRO': 9.99, 'PREMIUM': 19.99}
SANDBOX_API = 'https://api-m.sandbox.paypal.com'


class PayPalConfigurationError(RuntimeError):
    """Raised when required PayPal sandbox settings are missing or invalid."""


class PayPalProviderError(RuntimeError):
    """Raised when PayPal rejects or cannot process an API request."""


def _settings():
    mode = os.environ.get('PAYPAL_MODE', 'sandbox').strip().lower()
    if mode != 'sandbox':
        raise PayPalConfigurationError(
            'Solo está habilitado PayPal sandbox; producción requiere activación separada.'
        )

    required = {
        'client_id': os.environ.get('PAYPAL_CLIENT_ID', '').strip(),
        'client_secret': os.environ.get('PAYPAL_CLIENT_SECRET', ''),
        'webhook_id': os.environ.get('PAYPAL_WEBHOOK_ID', '').strip(),
        'pro_plan_id': os.environ.get('PAYPAL_PRO_PLAN_ID', '').strip(),
        'premium_plan_id': os.environ.get('PAYPAL_PREMIUM_PLAN_ID', '').strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise PayPalConfigurationError(
            'Configura PayPal sandbox: ' + ', '.join(missing) + '.'
        )

    base_url = os.environ.get('PAYPAL_PUBLIC_BASE_URL', 'http://localhost:5000').rstrip('/')
    parsed_base_url = urlparse(base_url)
    if (
        parsed_base_url.scheme not in ('http', 'https') or
        not parsed_base_url.hostname or
        parsed_base_url.username or parsed_base_url.password or
        parsed_base_url.query or parsed_base_url.fragment or
        (
            parsed_base_url.scheme != 'https' and
            parsed_base_url.hostname not in ('localhost', '127.0.0.1')
        )
    ):
        raise PayPalConfigurationError(
            'PAYPAL_PUBLIC_BASE_URL debe usar HTTPS; HTTP solo se permite en localhost.'
        )
    required['base_url'] = base_url
    required['api_base'] = SANDBOX_API
    return required


def is_configured():
    try:
        _settings()
        return True
    except PayPalConfigurationError:
        return False


def plan_id(plan):
    settings = _settings()
    if plan == 'PRO':
        return settings['pro_plan_id']
    if plan == 'PREMIUM':
        return settings['premium_plan_id']
    raise PayPalConfigurationError('Plan PayPal no válido.')


def plan_amount(plan):
    try:
        return PLAN_AMOUNTS_USD[plan]
    except KeyError as exc:
        raise PayPalConfigurationError('Plan PayPal no válido.') from exc


def _request(method, path, *, payload=None, request_id=None):
    settings = _settings()
    try:
        token_response = requests.post(
            f"{settings['api_base']}/v1/oauth2/token",
            auth=(settings['client_id'], settings['client_secret']),
            data={'grant_type': 'client_credentials'},
            headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
            timeout=15
        )
    except requests.RequestException as exc:
        raise PayPalProviderError('No se pudo conectar con PayPal sandbox.') from exc
    if not token_response.ok:
        raise PayPalProviderError(
            f'PayPal sandbox rechazó la autenticación (HTTP {token_response.status_code}).'
        )
    try:
        access_token = token_response.json()['access_token']
    except (ValueError, KeyError, TypeError) as exc:
        raise PayPalProviderError('PayPal sandbox devolvió un token inválido.') from exc

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    if request_id:
        headers['PayPal-Request-Id'] = request_id
    try:
        response = requests.request(
            method,
            f"{settings['api_base']}{path}",
            headers=headers,
            json=payload,
            timeout=20
        )
    except requests.RequestException as exc:
        raise PayPalProviderError('No se pudo completar la solicitud con PayPal sandbox.') from exc
    if not response.ok:
        raise PayPalProviderError(
            f'PayPal sandbox rechazó la solicitud (HTTP {response.status_code}).'
        )
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise PayPalProviderError('PayPal sandbox devolvió una respuesta inválida.') from exc


def create_subscription(plan, user_id, request_id):
    settings = _settings()
    plan_id_value = plan_id(plan)
    return _request(
        'POST',
        '/v1/billing/subscriptions',
        request_id=request_id,
        payload={
            'plan_id': plan_id_value,
            'custom_id': f'trading-platform:user:{int(user_id)}:plan:{plan}',
            'application_context': {
                'brand_name': 'Asistente de Trading',
                'locale': 'es-CR',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'SUBSCRIBE_NOW',
                'return_url': (
                    f"{settings['base_url']}/billing/paypal/return"
                ),
                'cancel_url': (
                    f"{settings['base_url']}/billing/paypal/cancel"
                )
            }
        }
    )


def get_subscription(subscription_id):
    return _request('GET', f'/v1/billing/subscriptions/{subscription_id}')


def get_plan_details(paypal_plan_id):
    return _request('GET', f'/v1/billing/plans/{paypal_plan_id}')


def cancel_subscription(subscription_id, reason):
    return _request(
        'POST',
        f'/v1/billing/subscriptions/{subscription_id}/cancel',
        payload={'reason': reason[:128]}
    )


def verify_webhook(headers, event):
    settings = _settings()
    payload = {
        'auth_algo': headers.get('PAYPAL-AUTH-ALGO'),
        'cert_url': headers.get('PAYPAL-CERT-URL'),
        'transmission_id': headers.get('PAYPAL-TRANSMISSION-ID'),
        'transmission_sig': headers.get('PAYPAL-TRANSMISSION-SIG'),
        'transmission_time': headers.get('PAYPAL-TRANSMISSION-TIME'),
        'webhook_id': settings['webhook_id'],
        'webhook_event': event
    }
    if not all(payload[key] for key in (
        'auth_algo', 'cert_url', 'transmission_id',
        'transmission_sig', 'transmission_time'
    )):
        return False
    result = _request(
        'POST',
        '/v1/notifications/verify-webhook-signature',
        payload=payload
    )
    return result.get('verification_status') == 'SUCCESS'
