from __future__ import annotations

import dkim


def sign_message(raw: bytes, selector: str, domain: str, private_key: bytes) -> bytes:
    signature = dkim.sign(raw, selector.encode(), domain.encode(), private_key)
    return signature + raw


def verify_message(raw: bytes) -> bool:
    try:
        return bool(dkim.verify(raw))
    except Exception:
        return False
