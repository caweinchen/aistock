import hashlib
import hmac
import secrets


HASH_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"{HASH_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def is_password_hash(value: str) -> bool:
    return value.startswith(f"{HASH_ALGORITHM}$")


def verify_password(password: str, stored_password: str) -> bool:
    if not is_password_hash(stored_password):
        return hmac.compare_digest(stored_password, password)

    try:
        algorithm, iterations, salt, expected_digest = stored_password.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected_digest)
    except (ValueError, TypeError):
        return False


def generate_auth_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_password_strength(password: str) -> dict:
    """Validate password strength."""
    messages = []
    score = 0

    if len(password) >= 8:
        score += 1
    else:
        messages.append("Password must be at least 8 characters long")

    if any(c.isupper() for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one uppercase letter")

    if any(c.islower() for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one lowercase letter")

    if any(c.isdigit() for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one number")

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(c in special_chars for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one special character (!@#$%^&* etc.)")

    return {
        "valid": score >= 5,
        "score": score,
        "messages": messages if messages else ["Password is strong"]
    }
