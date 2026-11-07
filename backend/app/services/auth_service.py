
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

    # Check whether the stored password is a bcrypt hash
    if stored_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            valid = bcrypt_context.verify(
                password,
                stored_password
            )
        except Exception:
            valid = False

    # Otherwise, verify it as a PBKDF2 hash
    else:
        valid = verify_password(password, stored_password)

    return user if valid else None
