
from ..core.database import get_connection
from ..core.security import verify_password
from passlib.context import CryptContext

bcrypt_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def authenticate(username, password):
    c = get_connection()

    try:
        user = c.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
    finally:
        c.close()

    if not user:
        return None

    user = dict(user)
    stored_password = user["password_hash"]

    # Support existing PBKDF2 user passwords
    if "$" in stored_password:
        valid = verify_password(password, stored_password)

    # Support the existing administrator bcrypt password
    else:
        try:
            valid = bcrypt_context.verify(
                password,
                stored_password
            )
        except Exception:
            valid = False

    return user if valid else None
