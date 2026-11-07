
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from ..core.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from ..core.dependencies import require_login
from ..core.database import get_connection
from ..services.document_service import get_document, can_access, visible_documents
from ..services.audit_service import log_event

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------
# MY DOCUMENTS
# ---------------------------------------------------------

@router.get('/documents')
def documents(request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    all_documents = visible_documents(user)

    docs = [
        doc for doc in all_documents
        if doc['owner_username'] == user['username']
    ]

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={"user": user, "documents": docs}
    )


# ---------------------------------------------------------
# SHARED DOCUMENTS
# ---------------------------------------------------------

@router.get('/shared')
def shared_documents(request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT d.*, p.access AS shared_access
        FROM documents d
        JOIN permissions p ON p.document_id = d.id
        WHERE p.username = ?
          AND d.owner_username != ?
        ORDER BY d.id DESC
        """,
        (user['username'], user['username'])
    ).fetchall()

    connection.close()

    return templates.TemplateResponse(
        request=request,
        name="shared.html",
        context={
            "user": user,
            "documents": [dict(row) for row in rows]
        }
    )


# ---------------------------------------------------------
# UPLOAD PAGE
# ---------------------------------------------------------

@router.get('/upload')
def upload_page(request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    if user['role'] == 'viewer':
        return JSONResponse(
            {"detail": "Only document owners and administrators can upload"},
            status_code=403
        )

    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"user": user}
    )


# ---------------------------------------------------------
# UPLOAD DOCUMENT
# ---------------------------------------------------------

@router.post('/upload')
async def upload(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form('General')
):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    if user['role'] == 'viewer':
        return JSONResponse(
            {"detail": "Only document owners and administrators can upload"},
            status_code=403
        )

    if not file.filename:
        return JSONResponse({"detail": "Choose a file"}, status_code=400)

    suffix = Path(file.filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"detail": "File type not allowed"},
            status_code=400
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        return JSONResponse(
            {"detail": "File too large"},
            status_code=400
        )

    stored_name = uuid4().hex + suffix

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored_name).write_bytes(content)

    uploaded_at = datetime.utcnow().isoformat()

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO documents
        (name, owner_username, category, stored_name, uploaded_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            Path(file.filename).name,
            user['username'],
            category,
            stored_name,
            uploaded_at,
            'Active'
        )
    )

    document_id = cursor.lastrowid

    # Store original upload as version 1.
    connection.execute(
        """
        INSERT INTO document_versions
        (document_id, version_number, stored_name, edited_by, created_at)
        VALUES (?, 1, ?, ?, ?)
        """,
        (
            document_id,
            stored_name,
            user['username'],
            uploaded_at
        )
    )

    connection.commit()
    connection.close()

    log_event(
        user['username'],
        'UPLOAD',
        file.filename,
        f'Document ID {document_id}; version 1'
    )

    return RedirectResponse('/documents', status_code=303)


# ---------------------------------------------------------
# OPEN DOCUMENT
# ---------------------------------------------------------

@router.get('/documents/{document_id}')
def open_document(document_id: int, request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    document = get_document(document_id)

    if not document:
        return JSONResponse(
            {"detail": "Document not found"},
            status_code=404
        )

    if not can_access(user, document_id, 'READ'):
        log_event(
            user['username'],
            'ACCESS_DENIED',
            document['name'],
            'Document access denied'
        )
        return JSONResponse({"detail": "Access denied"}, status_code=403)

    document['owner'] = document['owner_username']
    document['date'] = document['uploaded_at']
    document['file_url'] = f"/documents/{document_id}/preview"

    # Check whether the current user can edit.
    document['can_edit'] = can_access(user, document_id, 'EDIT')

    # Get the latest version and the username of its creator/editor.
    connection = get_connection()

    version = connection.execute(
        """
        SELECT version_number, edited_by
        FROM document_versions
        WHERE document_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id,)
    ).fetchone()

    connection.close()

    document['version_number'] = version['version_number'] if version else 1

    document['modified_by'] = (
        version['edited_by']
        if version else document['owner_username']
    )

    # Version 1 is the original upload.
    document['modification_label'] = (
        'Uploaded by'
        if document['version_number'] == 1
        else 'Modified by'
    )

    log_event(
        user['username'],
        'DOCUMENT_VIEW',
        document['name'],
        'Document opened'
    )

    return templates.TemplateResponse(
        request=request,
        name="document_details.html",
        context={"user": user, "document": document}
    )


# ---------------------------------------------------------
# EDIT DOCUMENT PAGE - TXT AND CSV ONLY
# ---------------------------------------------------------

@router.get('/documents/{document_id}/edit')
def edit_document(document_id: int, request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    document = get_document(document_id)

    if not document:
        return JSONResponse(
            {"detail": "Document not found"},
            status_code=404
        )

    if not can_access(user, document_id, 'EDIT'):
        log_event(
            user['username'],
            'ACCESS_DENIED',
            document['name'],
            'Document editing denied'
        )
        return JSONResponse(
            {"detail": "EDIT permission required"},
            status_code=403
        )

    suffix = Path(document['name']).suffix.lower()

    if suffix not in ('.txt', '.csv'):
        return JSONResponse(
            {"detail": "The editor currently supports TXT and CSV files only"},
            status_code=415
        )

    file_path = UPLOAD_DIR / document['stored_name']

    if not file_path.is_file():
        return JSONResponse({"detail": "File not found"}, status_code=404)

    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return JSONResponse(
            {"detail": "This file is not valid UTF-8 text"},
            status_code=415
        )

    connection = get_connection()

    version = connection.execute(
        """
        SELECT version_number
        FROM document_versions
        WHERE document_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id,)
    ).fetchone()

    connection.close()

    return templates.TemplateResponse(
        request=request,
        name="edit_document.html",
        context={
            "user": user,
            "document": document,
            "content": content,
            "version_number": version['version_number'] if version else 1
        }
    )


# ---------------------------------------------------------
# SAVE NEW DOCUMENT VERSION - TXT AND CSV ONLY
# ---------------------------------------------------------

@router.post('/documents/{document_id}/save')
async def save_document(
    document_id: int,
    request: Request,
    content: str = Form(...)
):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    document = get_document(document_id)

    if not document:
        return JSONResponse(
            {"detail": "Document not found"},
            status_code=404
        )

    if not can_access(user, document_id, 'EDIT'):
        log_event(
            user['username'],
            'ACCESS_DENIED',
            document['name'],
            'Document save denied'
        )
        return JSONResponse(
            {"detail": "EDIT permission required"},
            status_code=403
        )

    suffix = Path(document['name']).suffix.lower()

    if suffix not in ('.txt', '.csv'):
        return JSONResponse(
            {"detail": "The editor currently supports TXT and CSV files only"},
            status_code=415
        )

    content_bytes = content.encode('utf-8')

    if len(content_bytes) > MAX_FILE_SIZE:
        return JSONResponse(
            {"detail": "Edited file is too large"},
            status_code=400
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    new_stored_name = uuid4().hex + suffix
    new_file_path = UPLOAD_DIR / new_stored_name
    new_file_path.write_bytes(content_bytes)

    connection = get_connection()

    try:
        # Lock the write transaction while choosing the next version.
        connection.execute("BEGIN IMMEDIATE")

        latest = connection.execute(
            """
            SELECT MAX(version_number) AS latest_version
            FROM document_versions
            WHERE document_id = ?
            """,
            (document_id,)
        ).fetchone()

        next_version = (latest['latest_version'] or 0) + 1
        saved_at = datetime.utcnow().isoformat()

        # Save the new version and record the logged-in username.
        connection.execute(
            """
            INSERT INTO document_versions
            (document_id, version_number, stored_name, edited_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document_id,
                next_version,
                new_stored_name,
                user['username'],
                saved_at
            )
        )

        # Make the new version the current document.
        connection.execute(
            """
            UPDATE documents
            SET stored_name = ?
            WHERE id = ?
            """,
            (new_stored_name, document_id)
        )

        connection.commit()

    except Exception:
        connection.rollback()

        if new_file_path.exists():
            new_file_path.unlink()

        raise

    finally:
        connection.close()

    log_event(
        user['username'],
        'DOCUMENT_EDIT',
        document['name'],
        f'Saved version {next_version}'
    )

    return RedirectResponse(
        f'/documents/{document_id}',
        status_code=303
    )


# ---------------------------------------------------------
# DOCUMENT PREVIEW
# ---------------------------------------------------------

@router.get('/documents/{document_id}/preview')
def preview_document(document_id: int, request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    document = get_document(document_id)

    if not document:
        return JSONResponse(
            {"detail": "Document not found"},
            status_code=404
        )

    if not can_access(user, document_id, 'READ'):
        log_event(
            user['username'],
            'ACCESS_DENIED',
            document['name'],
            'Document preview denied'
        )
        return JSONResponse({"detail": "Access denied"}, status_code=403)

    file_path = UPLOAD_DIR / document['stored_name']

    if not file_path.is_file():
        return JSONResponse(
            {"detail": "File not found"},
            status_code=404
        )

    suffix = Path(document['name']).suffix.lower()

    if suffix not in ('.pdf', '.txt', '.csv'):
        return JSONResponse(
            {"detail": "Preview is not available for this file type"},
            status_code=415
        )

    if suffix == '.pdf':
        media_type = 'application/pdf'
    elif suffix == '.csv':
        media_type = 'text/csv'
    else:
        media_type = 'text/plain'

    return FileResponse(
        file_path,
        media_type=media_type,
        content_disposition_type='inline'
    )


# ---------------------------------------------------------
# DOWNLOAD DOCUMENT
# ---------------------------------------------------------

@router.get('/documents/{document_id}/download')
def download(document_id: int, request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    document = get_document(document_id)

    if not document:
        return JSONResponse(
            {"detail": "Document not found"},
            status_code=404
        )

    if not can_access(user, document_id, 'READ'):
        log_event(
            user['username'],
            'ACCESS_DENIED',
            document['name'],
            'Download denied'
        )
        return JSONResponse({"detail": "Access denied"}, status_code=403)

    file_path = UPLOAD_DIR / document['stored_name']

    if not file_path.is_file():
        return JSONResponse(
            {"detail": "File not found"},
            status_code=404
        )

    log_event(
        user['username'],
        'DOWNLOAD',
        document['name'],
        'Document downloaded'
    )

    return FileResponse(
        file_path,
        filename=document['name']
    )
