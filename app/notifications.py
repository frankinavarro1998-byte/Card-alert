from __future__ import annotations
import base64
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import webpush, WebPushException
from .db import rows, execute

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT))
DATA_DIR.mkdir(parents=True, exist_ok=True)
PRIVATE_KEY = DATA_DIR / "vapid_private.pem"
PUBLIC_KEY = DATA_DIR / "vapid_public.txt"


def ensure_vapid_keys() -> str:
    if not PRIVATE_KEY.exists() or not PUBLIC_KEY.exists():
        key = ec.generate_private_key(ec.SECP256R1())
        PRIVATE_KEY.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        pub = key.public_key().public_numbers()
        raw = b"\x04" + pub.x.to_bytes(32, "big") + pub.y.to_bytes(32, "big")
        PUBLIC_KEY.write_text(base64.urlsafe_b64encode(raw).rstrip(b"=").decode())
    return PUBLIC_KEY.read_text().strip()


def send_push(title: str, body: str, url: str) -> None:
    ensure_vapid_keys()
    payload = json.dumps({"title": title, "body": body, "url": url})
    for sub in rows("SELECT id, subscription_json FROM push_subscriptions"):
        try:
            webpush(
                subscription_info=json.loads(sub["subscription_json"]),
                data=payload,
                vapid_private_key=str(PRIVATE_KEY),
                vapid_claims={"sub": "mailto:card-alert@localhost"},
            )
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                execute("DELETE FROM push_subscriptions WHERE id=?", (sub["id"],))
