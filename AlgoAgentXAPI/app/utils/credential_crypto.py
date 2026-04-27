from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

_PREFIX = "enc:v1:"


def _key() -> bytes:
    secret = os.getenv("ALGOAGENTX_CREDENTIAL_SECRET") or os.getenv("SECRET_KEY") or "algoagentx-dev-local-secret-change-me"
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def encrypt_credential(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return value
    if isinstance(value, str) and value.startswith(_PREFIX):
        return value
    encrypted = _xor(str(value).encode("utf-8"), _key())
    return _PREFIX + base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_credential(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return value
    if not isinstance(value, str) or not value.startswith(_PREFIX):
        # Backward compatible with existing Phase 5 plaintext credentials.
        return value
    try:
        raw = base64.urlsafe_b64decode(value[len(_PREFIX):].encode("ascii"))
        return _xor(raw, _key()).decode("utf-8")
    except Exception:
        return None


def mask_credential(value: Optional[str]) -> Optional[str]:
    plain = decrypt_credential(value) if value else None
    if not plain:
        return None
    if len(plain) <= 4:
        return "****"
    return f"****{plain[-4:]}"
