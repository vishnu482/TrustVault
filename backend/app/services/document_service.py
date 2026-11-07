
from ..core.database import get_connection


def get_document(document_id):
    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


def has_shared_permission(document_id, username, required):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT access
            FROM permissions
            WHERE document_id = ? AND username = ?
            """,
            (document_id, username)
        ).fetchone()

        if not row:
            return False

        access = str(row["access"]).upper()

        if required == "EDIT":
            return access == "EDIT"

        if required == "READ":
            return access in ("READ", "EDIT")

        return False

    finally:
        connection.close()


def visible_documents(user):
    role = str(user.get("role", "")).strip().lower()
    username = user["username"]

    connection = get_connection()

    try:
        if role in ("administrator", "admin"):
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY id DESC"
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT DISTINCT d.*
                FROM documents d
                LEFT JOIN permissions p
                    ON p.document_id = d.id
                    AND p.username = ?
                WHERE d.owner_username = ?
                   OR p.access IN ('READ', 'EDIT')
                ORDER BY d.id DESC
                """,
                (username, username)
            ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def can_access(user, document_id, required="READ"):
    document = get_document(document_id)

    if not document:
        return False

    role = str(user.get("role", "")).strip().lower()
    username = user["username"]
    required = required.upper()

    # Administrator can access everything.
    if role in ("administrator", "admin"):
        return True

    # Viewer can only read.
    if role == "viewer":
        if required != "READ":
            return False

        return (
            document["owner_username"] == username
            or has_shared_permission(document_id, username, "READ")
        )

    # Document owner can edit their own documents.
    if role == "document_owner":
        if document["owner_username"] == username:
            return required in ("READ", "EDIT")

        return has_shared_permission(document_id, username, required)

    return False
