"""Security utilities for TraceFox services."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Union

from pydantic import BaseModel

from services.shared.config import get_settings


def validate_webhook_signature(
    provider: str,
    payload: Union[BaseModel, dict, bytes],
    signature: str | None,
) -> bool:
    """
    Validate the signature of a webhook request.

    Args:
        provider: The webhook provider (e.g., 'github').
        payload: The request body (Pydantic model, dict, or raw bytes).
        signature: The signature header value (e.g., 'sha256=...').

    Returns:
        True if the signature is valid, False otherwise.
    """
    settings = get_settings()

    # In development mode, we might trust requests without signatures or with dummy ones
    # Check if we are in dev mode via auth settings
    try:
        if settings.auth.github.dev_mode:
             # Relaxed validation for dev mode if signature is missing or dummy
             if not signature or signature == "dev-signature":
                 return True
    except (AttributeError, ValueError):
        pass

    if not signature:
        return False
        
    # Determine the secret key based on provider
    secret = None
    if provider == "github":
        # Using client_secret as fallback if no specific webhook secret is defined
        # ideally this should be TRACEFOX_AUTH__GITHUB__WEBHOOK_SECRET
        secret = settings.github.get("webhook_secret") or settings.auth.github.client_secret
    
    if not secret:
        # If no secret is configured, we can't validate. 
        # Fail safe: return False unless strict execution is not required?
        # For now, logging a warning would be good but we just return False.
        return False

    # Normalize payload to bytes
    if isinstance(payload, BaseModel):
        # converting pydantic to json bytes - NOTE: this is fragile as field order/whitespace mismatch 
        # vs original request invalidates HMAC. 
        # Ideally we should validate raw bytes in the route handler.
        body_bytes = payload.json().encode("utf-8")
    elif isinstance(payload, dict):
        body_bytes = json.dumps(payload).encode("utf-8")
    else:
        body_bytes = payload

    if provider == "github":
        # GitHub signatures are prefixed with 'sha256='
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        expected_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=body_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

    return False
