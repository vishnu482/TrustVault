from ..core.database import get_connection, pwd_context
from ..core.security import verify_password


def authenticate(username, password):

    c = get_connection()

    try:
        user = c.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    finally:
        c.close()

    if not user:
        return None

    user = dict(user)
    stored_password = user["password_hash"]

    # Bcrypt hashes start with these prefixes.
    if stored_password.startswith(("$2a$", "$2b$", "$2y$")):

        try:
            valid = pwd_context.verify(
                password,
                stored_password
            )
        except Exception:
            valid = False

    else:
        # Verify older PBKDF2 hashes.
        valid = verify_password(
            password,
            stored_password
        )

    return user if valid else None