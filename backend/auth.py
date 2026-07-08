"""Authentication: password hashing (PBKDF2) and JWT-style tokens (HS256).

Zero external dependencies — uses hashlib/hmac/secrets from the stdlib.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

import config


# ----------------------------- passwords -----------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = config.PBKDF2_ITERATIONS
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode(),
        base64.b64encode(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ------------------------------- tokens -------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(signing_input: bytes) -> str:
    sig = hmac.new(config.SECRET.encode(), signing_input, hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_token(user_id: int, role: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": user_id, "role": role, "iat": now, "exp": now + config.TOKEN_TTL}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    return f"{h}.{p}.{_sign(signing_input)}"


def decode_token(token: str):
    """Return payload dict if valid & unexpired, else None."""
    try:
        h, p, sig = token.split(".")
        signing_input = f"{h}.{p}".encode()
        if not hmac.compare_digest(sig, _sign(signing_input)):
            return None
        payload = json.loads(_b64url_decode(p))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
