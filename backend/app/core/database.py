
import os
import sqlite3
from datetime import datetime

from passlib.context import CryptContext

from .config import DATABASE_FILE


# ---------------------------------------------------------
# PASSWORD HASHING
# ---------------------------------------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def get_connection():
    c = sqlite3.connect(DATABASE_FILE)
    c.row_factory = sqlite3.Row
    return c


# ---------------------------------------------------------
# INITIALIZE DATABASE
# ---------------------------------------------------------

def init_db():

    c = get_connection()
    x = c.cursor()

    try:

        # -------------------------------------------------
        # USERS TABLE
        # -------------------------------------------------

        x.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL
            )
            """
        )

        # -------------------------------------------------
        # DOCUMENTS TABLE
        # -------------------------------------------------

        x.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_username TEXT NOT NULL,
                category TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active'
            )
            """
        )

        # -------------------------------------------------
        # PERMISSIONS TABLE
        # -------------------------------------------------

        x.execute(
            """
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                access TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                UNIQUE(document_id, username)
            )
            """
        )

        # -------------------------------------------------
        # AUDIT LOGS TABLE
        # -------------------------------------------------

        x.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )

        # -------------------------------------------------
        # DOCUMENT VERSIONS TABLE
        # -------------------------------------------------

        x.execute(
            """
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                stored_name TEXT NOT NULL,
                edited_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(document_id, version_number)
            )
            """
        )

        # -------------------------------------------------
        # REGISTER EXISTING DOCUMENTS AS VERSION 1
        # -------------------------------------------------

        x.execute(
            """
            INSERT INTO document_versions (
                document_id,
                version_number,
                stored_name,
                edited_by,
                created_at
            )
            SELECT
                d.id,
                1,
                d.stored_name,
                d.owner_username,
                d.uploaded_at
            FROM documents d
            WHERE NOT EXISTS (
                SELECT 1
                FROM document_versions v
                WHERE v.document_id = d.id
            )
            """
        )

        c.commit()

        # -------------------------------------------------
        # CREATE OR UPDATE ADMINISTRATOR
        # -------------------------------------------------

        admin_username = os.getenv(
            "TRUSTVAULT_ADMIN_USERNAME",
            "admin"
        ).strip()

        admin_password = os.getenv(
            "TRUSTVAULT_ADMIN_PASSWORD"
        )

        admin_name = os.getenv(
            "TRUSTVAULT_ADMIN_NAME",
            "Administrator"
        ).strip()

        if admin_password:

            existing_admin = x.execute(
                """
                SELECT id
                FROM users
                WHERE username = ?
                """,
                (admin_username,)
            ).fetchone()

            password_hash = pwd_context.hash(
                admin_password
            )

            if existing_admin:

                x.execute(
                    """
                    UPDATE users
                    SET password_hash = ?,
                        name = ?,
                        role = 'administrator'
                    WHERE username = ?
                    """,
                    (
                        password_hash,
                        admin_name,
                        admin_username
                    )
                )

            else:

                x.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash,
                        name,
                        role,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        admin_username,
                        password_hash,
                        admin_name,
                        "administrator",
                        datetime.utcnow().isoformat()
                    )
                )

            c.commit()

    except Exception:
        c.rollback()
        raise

    finally:
        c.close()
