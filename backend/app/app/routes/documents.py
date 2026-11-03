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


@router.get('/documents')
def documents(request: Request):
    user = require_login(request)

    if not user:
        return RedirectResponse('/login', status_code=303)

    all_documents = visible_documents(user)

    # My documents shows documents owned by the logged-in user.
    docs = [
        doc for doc in all_documents
        if doc['owner_username'] == user['username']
    ]

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={"user": user, "documents": docs}
    )


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
            datetime.utcnow().isoformat(),
            'Active'
        )
    )

    connection.commit()
    document_id = cursor.lastrowid
    connection.close()

    log_event(
        user['username'],
        'UPLOAD',
        file.filename,
        f'Document ID {document_id}'
    )

    return RedirectResponse('/documents', status_code=303)


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
    else:
        media_type = 'text/plain'

    return FileResponse(
        file_path,
        media_type=media_type,
        content_disposition_type='inline'
    )


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