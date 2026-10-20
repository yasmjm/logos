import hashlib
import hmac
import secrets

# scrypt parameters (RFC 7914 interactive-login recommendation).
_N = 2**14
_R = 8
_P = 1
_DKLEN = 64


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != "scrypt":
        return False
    expected = bytes.fromhex(digest_hex)
    digest = hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt_hex),
        n=int(n),
        r=int(r),
        p=int(p),
        dklen=len(expected),
    )
    return hmac.compare_digest(digest, expected)


# Verified when the username does not exist, so the response time does not reveal
# whether an account exists.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))
