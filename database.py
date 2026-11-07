
import os
import sqlite3
from datetime import datetime

import fitz
from docx import Document as DocxDocument
from passlib.context import CryptContext

from .config import DATABASE_FILE, UPLOAD_DIR


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def create_demo_files():
    """Create real sample files used by the demo accounts."""

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    files = {}

    # PDF sample
    pdf_name = "demo_company_policy.pdf"
    pdf_path = UPLOAD_DIR / pdf_name

    if not pdf_path.exists():
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text(
            (72, 72),
            "TrustVault Demo - Company Policy\n\n"
            "1. Employees must protect confidential information.\n"
            "2. Documents must only be shared with authorized users.\n"
            "3. Report suspected security incidents immediately.\n"
            "4. Access permissions should follow least privilege.",
            fontsize=12
        )
        pdf.save(str(pdf_path))
        pdf.close()

    files["pdf"] = (
        "Demo Company Policy.pdf",
        pdf_name,
        "Policies"
    )

    # DOCX sample
    docx_name = "demo_project_report.docx"
    docx_path = UPLOAD_DIR / docx_name

    if not docx_path.exists():
        doc = DocxDocument()
        doc.add_heading("TrustVault Demo Project Report", 0)
        doc.add_paragraph(
            "This is a sample document for the TrustVault demonstration."
        )
        doc.add_heading("Project Overview", level=1)
        doc.add_paragraph(
            "TrustVault is a document management and secure sharing system."
        )
        doc.add_heading("Main Features", level=1)
        doc.add_paragraph(
            "User authentication, document upload, access permissions, "
            "document versioning, and audit logging."
        )
        doc.save(str(docx_path))

    files["docx"] = (
        "Demo Project Report.docx",
        docx_name,
        "Reports"
    )

    # TXT sample
    txt_name = "demo_readme.txt"
    txt_path = UPLOAD_DIR / txt_name

    if not txt_path.exists():
        txt_path.write_text(
            "TrustVault Demo Document\n\n"
            "This is a sample text file.\n"
            "It demonstrates document upload and sharing.\n"
            "The Demo Viewer has EDIT access to this file.\n",
            encoding="utf-8"
        )

    files["txt"] = (
        "Demo Readme.txt",
        txt_name,
        "General"
    )

    # CSV sample
    csv_name = "demo_employee_records.csv"
    csv_path = UPLOAD_DIR / csv_name

    if not csv_path.exists():
        csv_path.write_text(
            "Employee ID,Name,Department,Status\n"
            "101,Aarav,IT,Active\n"
            "102,Diya,HR,Active\n"
            "103,Kiran,Finance,Active\n",
            encoding="utf-8"
        )

    files["csv"] = (
        "Demo Employee Records.csv",
        csv_name,
        "Records"
    )

    return files


def seed_demo_data(connection):
    """Create demo accounts, documents, versions and permissions."""

    demo_accounts = [
        (
            "demo_admin",
            "DemoAdmin@123",
            "Admin",
            "administrator"
        ),
        (
            "demo_owner",
            "DemoOwner@123",
            "Vishal",
            "document_owner"
        ),
        (
            "demo_viewer",
            "DemoViewer@123",
            "Rahul",
            "viewer"
        )
    ]

    now = datetime.utcnow().isoformat()

    for username, password, name, role in demo_accounts:

        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            # Update display name and role without resetting the password.
            connection.execute(
                """
                UPDATE users
                SET name = ?, role = ?
                WHERE username = ?
                """,
                (name, role, username)
            )
        else:
            connection.execute(
                """
                INSERT INTO users (
                    username, password_hash, name, role, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    pwd_context.hash(password),
                    name,
                    role,
                    now
                )
            )

    sample_files = create_demo_files()
    demo_documents = {}

    for key, (display_name, stored_name, category) in sample_files.items():

        existing = connection.execute(
            """
            SELECT id
            FROM documents
            WHERE name = ? AND owner_username = ?
            """,
            (display_name, "demo_owner")
        ).fetchone()

        if existing:
            document_id = existing["id"]
        else:
            cursor = connection.execute(
                """
                INSERT INTO documents (
                    name,
                    owner_username,
                    category,
                    stored_name,
                    uploaded_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    display_name,
                    "demo_owner",
                    category,
                    stored_name,
                    now,
                    "Active"
                )
            )
            document_id = cursor.lastrowid

        demo_documents[key] = document_id

        version_exists = connection.execute(
            """
            SELECT id
            FROM document_versions
            WHERE document_id = ? AND version_number = 1
            """,
            (document_id,)
        ).fetchone()

        if not version_exists:
            connection.execute(
                """
                INSERT INTO document_versions (
                    document_id,
                    version_number,
                    stored_name,
                    edited_by,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    1,
                    stored_name,
                    "demo_owner",
                    now
                )
            )

    # Demo Viewer: READ access to PDF, EDIT access to TXT.
    demo_permissions = [
        ("pdf", "READ"),
        ("txt", "EDIT")
    ]

    for key, access in demo_permissions:

        document_id = demo_documents[key]

        connection.execute(
            """
            INSERT INTO permissions (
                document_id,
                username,
                access,
                granted_by,
                granted_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(document_id, username)
            DO UPDATE SET
                access = excluded.access,
                granted_by = excluded.granted_by,
                granted_at = excluded.granted_at
            """,
            (
                document_id,
                "demo_viewer",
                access,
                "demo_owner",
                now
            )
        )


def init_db():

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
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

        cursor.execute(
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

        cursor.execute(
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

        cursor.execute(
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

        cursor.execute(
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

        # Register existing documents as version 1 when needed.
        cursor.execute(
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

        # Create or update the real administrator from environment variables.
        admin_username = os.getenv(
            "TRUSTVAULT_ADMIN_USERNAME", "admin"
        ).strip()

        admin_password = os.getenv("TRUSTVAULT_ADMIN_PASSWORD")

        admin_name = os.getenv(
            "TRUSTVAULT_ADMIN_NAME", "Administrator"
        ).strip()

        if admin_password:
            existing_admin = cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (admin_username,)
            ).fetchone()

            if existing_admin:
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = ?,
                        name = ?,
                        role = 'administrator'
                    WHERE username = ?
                    """,
                    (
                        pwd_context.hash(admin_password),
                        admin_name,
                        admin_username
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, name, role, created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        admin_username,
                        pwd_context.hash(admin_password),
                        admin_name,
                        "administrator",
                        datetime.utcnow().isoformat()
                    )
                )

        # Create demo accounts, documents, and permissions.
        seed_demo_data(connection)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
