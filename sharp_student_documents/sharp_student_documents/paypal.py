import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def paypal_api_base() -> str:
    mode = getattr(settings, "PAYPAL_MODE", "sandbox")
    return "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"


def paypal_access_token(*, timeout_s: int = 20) -> str:
    client_id = getattr(settings, "PAYPAL_CLIENT_ID", None)
    client_secret = getattr(settings, "PAYPAL_CLIENT_SECRET", None)
    if not client_id or not client_secret:
        raise ValueError("Missing PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET")

    resp = requests.post(
        f"{paypal_api_base()}/v1/oauth2/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=timeout_s,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def verify_paypal_webhook_signature(
    *,
    request,
    webhook_event: Dict[str, Any],
    timeout_s: int = 20,
) -> bool:
    """
    Verify a PayPal webhook via PayPal's verify-webhook-signature endpoint.
    Returns True only when PayPal responds with verification_status == SUCCESS.
    """
    webhook_id = getattr(settings, "PAYPAL_WEBHOOK_ID", None)
    if not webhook_id:
        logger.error("PAYPAL_WEBHOOK_ID not configured; rejecting webhook")
        return False

    meta = getattr(request, "META", {}) or {}
    required: Dict[str, Optional[str]] = {
        "auth_algo": meta.get("HTTP_PAYPAL_AUTH_ALGO"),
        "cert_url": meta.get("HTTP_PAYPAL_CERT_URL"),
        "transmission_id": meta.get("HTTP_PAYPAL_TRANSMISSION_ID"),
        "transmission_sig": meta.get("HTTP_PAYPAL_TRANSMISSION_SIG"),
        "transmission_time": meta.get("HTTP_PAYPAL_TRANSMISSION_TIME"),
    }
    if any(not v for v in required.values()):
        logger.warning("Missing PayPal signature headers; rejecting webhook")
        return False

    try:
        token = paypal_access_token(timeout_s=timeout_s)
    except Exception:
        logger.exception("Failed to obtain PayPal access token for webhook verification")
        return False

    payload = {
        **required,
        "webhook_id": webhook_id,
        "webhook_event": webhook_event,
    }

    try:
        resp = requests.post(
            f"{paypal_api_base()}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        return resp.json().get("verification_status") == "SUCCESS"
    except Exception:
        logger.exception("PayPal webhook signature verification failed")
        return False

