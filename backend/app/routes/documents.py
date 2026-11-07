from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pymupdf

from docx import Document as DocxDocument

from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    Form,
    HTTPException
)

from fastapi.responses import (
    RedirectResponse,
    JSONResponse,
    FileResponse
)

from fastapi.templating import Jinja2Templates

from ..core.config import (
    UPLOAD_DIR,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)

from ..core.dependencies import require_login
from ..core.database import get_connection

from ..services.document_service import (
    get_document,
    can_access,
    visible_documents
)

from ..services.audit_service import log_event
from ..services import pdf_editor_service


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]

templates = Jinja2Templates(
    directory=str(BASE_DIR / "frontend" / "templates")
)


# ==================================================
# VERSION MANAGEMENT
# ==================================================

def get_latest_version(document_id):

    connection = get_connection()

    try:
        version = connection.execute(
            """
            SELECT *
            FROM document_versions
            WHERE document_id = ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (document_id,)
        ).fetchone()

        return dict(version) if version else None

    finally:
        connection.close()


def save_new_version(document, new_file_path, username):

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        latest = connection.execute(
            """
            SELECT MAX(version_number) AS version_number
            FROM document_versions
            WHERE document_id = ?
            """,
            (document["id"],)
        ).fetchone()

        new_version = (latest["version_number"] or 0) + 1

        stored_name = Path(new_file_path).name

        connection.execute(
            """
            INSERT INTO document_versions
            (document_id, version_number, stored_name, edited_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document["id"],
                new_version,
                stored_name,
                username,
                datetime.utcnow().isoformat()
            )
        )

        connection.execute(
            """
            UPDATE documents
            SET stored_name = ?
            WHERE id = ?
            """,
            (stored_name, document["id"])
        )

        connection.commit()

        return new_version

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==================================================
# DOCUMENT LIST
# ==================================================

@router.get("/documents")
async def documents_page(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    documents = visible_documents(user)

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={
            "user": user,
            "documents": documents
        }
    )


# ==================================================
# SHARED DOCUMENTS
# ==================================================

@router.get("/shared")
async def shared_page(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT d.*, p.access AS shared_access
            FROM documents d
            JOIN permissions p ON p.document_id = d.id
            WHERE p.username = ?
            ORDER BY d.id DESC
            """,
            (user["username"],)
        ).fetchall()

    finally:
        connection.close()

    return templates.TemplateResponse(
        request=request,
        name="shared.html",
        context={
            "user": user,
            "documents": [dict(row) for row in rows]
        }
    )


# ==================================================
# UPLOAD PAGE
# ==================================================

@router.get("/upload")
async def upload_page(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"user": user}
    )


# ==================================================
# UPLOAD DOCUMENT
# ==================================================

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...)
):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    # Normalize the role before checking permissions.
    role = str(user.get("role", "")).strip().lower()

    if role not in ("administrator", "admin", "document_owner"):
        return JSONResponse(
            {"error": "You are not allowed to upload documents."},
            status_code=403
        )

    if not file.filename:
        return JSONResponse(
            {"error": "Filename is required."},
            status_code=400
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": "Unsupported file type."},
            status_code=400
        )

    contents = await file.read()

    if not contents:
        return JSONResponse(
            {"error": "The uploaded file is empty."},
            status_code=400
        )

    if len(contents) > MAX_FILE_SIZE:
        return JSONResponse(
            {"error": "File exceeds the 10 MB limit."},
            status_code=400
        )

    stored_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_name

    file_path.write_bytes(contents)

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO documents
            (name, stored_name, owner_username, category, status, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file.filename,
                stored_name,
                user["username"],
                "General",
                "Active",
                datetime.utcnow().isoformat()
            )
        )

        document_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO document_versions
            (document_id, version_number, stored_name, edited_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document_id,
                1,
                stored_name,
                user["username"],
                datetime.utcnow().isoformat()
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        file_path.unlink(missing_ok=True)
        raise

    finally:
        connection.close()

    log_event(
        user["username"],
        "DOCUMENT_UPLOAD",
        str(document_id),
        f"Uploaded {file.filename}"
    )

    return RedirectResponse(
        f"/documents/{document_id}",
        status_code=303
    )


# ==================================================
# DOCUMENT DETAILS
# ==================================================

@router.get("/documents/{document_id}")
async def document_details(request: Request, document_id: int):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "READ"):
        return JSONResponse(
            {"error": "Document not found or access denied."},
            status_code=404
        )

    latest = get_latest_version(document_id)

    document["file_url"] = (
        f"/documents/{document_id}/preview"
    )

    document["can_edit"] = can_access(
        user,
        document_id,
        "EDIT"
    )

    if latest:

        document["version_number"] = latest["version_number"]
        document["modified_by"] = latest["edited_by"]

        document["modification_label"] = (
            "Uploaded by"
            if latest["version_number"] == 1
            else "Modified by"
        )

    else:

        document["version_number"] = 1
        document["modified_by"] = document["owner_username"]
        document["modification_label"] = "Uploaded by"

    log_event(
        user["username"],
        "DOCUMENT_VIEW",
        str(document_id),
        "Viewed document"
    )

    return templates.TemplateResponse(
        request=request,
        name="document_details.html",
        context={
            "user": user,
            "document": document
        }
    )


# ==================================================
# EDIT DOCUMENT PAGE
# ==================================================

@router.get("/documents/{document_id}/edit")
async def edit_document_page(request: Request, document_id: int):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "EDIT"):
        return JSONResponse(
            {"error": "You do not have edit permission."},
            status_code=403
        )

    extension = Path(document["name"]).suffix.lower()

    file_path = UPLOAD_DIR / document["stored_name"]

    if not file_path.exists():
        return JSONResponse(
            {"error": "Document file not found."},
            status_code=404
        )

    latest = get_latest_version(document_id)

    version_number = (
        latest["version_number"] if latest else 1
    )

    if extension in (".txt", ".csv"):

        content = file_path.read_text(encoding="utf-8")

        return templates.TemplateResponse(
            request=request,
            name="edit_document.html",
            context={
                "user": user,
                "document": document,
                "content": content,
                "version_number": version_number
            }
        )

    if extension == ".docx":

        doc = DocxDocument(str(file_path))

        paragraphs = [
            paragraph.text
            for paragraph in doc.paragraphs
        ]

        return templates.TemplateResponse(
            request=request,
            name="edit_document.html",
            context={
                "user": user,
                "document": document,
                "content": "\n".join(paragraphs),
                "version_number": version_number,
                "is_docx": True
            }
        )

    if extension == ".pdf":

        return templates.TemplateResponse(
            request=request,
            name="pdf_editor.html",
            context={
                "user": user,
                "document": document,
                "version_number": version_number,
                "preview_url": (
                    f"/documents/{document_id}/preview"
                )
            }
        )

    return JSONResponse(
        {"error": "This file type cannot be edited."},
        status_code=400
    )


# ==================================================
# SAVE TXT, CSV AND DOCX
# ==================================================

@router.post("/documents/{document_id}/save")
async def save_document(
    request: Request,
    document_id: int,
    content: str = Form(...)
):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "EDIT"):
        return JSONResponse(
            {"error": "You do not have edit permission."},
            status_code=403
        )

    extension = Path(document["name"]).suffix.lower()

    if extension not in (".txt", ".csv", ".docx"):
        return JSONResponse(
            {"error": "This file type cannot use this editor."},
            status_code=400
        )

    current_path = UPLOAD_DIR / document["stored_name"]

    new_path = UPLOAD_DIR / f"{uuid4().hex}{extension}"

    try:

        if extension in (".txt", ".csv"):

            new_path.write_text(
                content,
                encoding="utf-8"
            )

        else:

            doc = DocxDocument(str(current_path))

            edited_lines = content.splitlines()

            for index, paragraph in enumerate(doc.paragraphs):

                new_text = (
                    edited_lines[index]
                    if index < len(edited_lines)
                    else ""
                )

                if paragraph.runs:

                    paragraph.runs[0].text = new_text

                    for run in paragraph.runs[1:]:
                        run.text = ""

                else:
                    paragraph.add_run(new_text)

            for line in edited_lines[len(doc.paragraphs):]:
                doc.add_paragraph(line)

            doc.save(str(new_path))

        version = save_new_version(
            document,
            new_path,
            user["username"]
        )

    except Exception:
        new_path.unlink(missing_ok=True)
        raise

    log_event(
        user["username"],
        "DOCUMENT_EDIT",
        str(document_id),
        f"Saved version {version}"
    )

    return RedirectResponse(
        f"/documents/{document_id}",
        status_code=303
    )


# ==================================================
# OLD PDF ANNOTATION ROUTE
# ==================================================

@router.post("/documents/{document_id}/pdf-annotations")
async def save_pdf_annotations(
    request: Request,
    document_id: int
):

    user = require_login(request)

    if not user:
        return JSONResponse(
            {"error": "Login required."},
            status_code=401
        )

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "EDIT"):
        return JSONResponse(
            {"error": "You do not have edit permission."},
            status_code=403
        )

    if Path(document["name"]).suffix.lower() != ".pdf":
        return JSONResponse(
            {"error": "This is not a PDF document."},
            status_code=400
        )

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid annotation data."},
            status_code=400
        )

    annotations = data.get("annotations", [])

    if not isinstance(annotations, list) or not annotations:
        return JSONResponse(
            {"error": "No annotations were provided."},
            status_code=400
        )

    current_path = UPLOAD_DIR / document["stored_name"]

    if not current_path.exists():
        return JSONResponse(
            {"error": "PDF file not found."},
            status_code=404
        )

    new_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"

    pdf = None

    try:

        pdf = pymupdf.open(str(current_path))

        for item in annotations:

            page_number = int(item.get("page", 1)) - 1

            if page_number < 0 or page_number >= len(pdf):
                raise ValueError("Invalid PDF page number.")

            page = pdf[page_number]

            annotation_type = item.get("type")
            text = str(item.get("text", ""))

            if annotation_type == "comment":

                page.add_text_annot(
                    (
                        float(item.get("x", 100)),
                        float(item.get("y", 100))
                    ),
                    text
                )

            elif annotation_type == "highlight":

                rect = pymupdf.Rect(
                    float(item["x1"]),
                    float(item["y1"]),
                    float(item["x2"]),
                    float(item["y2"])
                )

                page.add_highlight_annot(rect)

            elif annotation_type == "text":

                x = float(item.get("x", 100))
                y = float(item.get("y", 100))

                rect = pymupdf.Rect(
                    x, y, x + 180, y + 45
                )

                page.add_freetext_annot(rect, text)

            elif annotation_type == "signature":

                page.insert_text(
                    (
                        float(item.get("x", 100)),
                        float(item.get("y", 100))
                    ),
                    text,
                    fontsize=18
                )

            elif annotation_type == "rectangle":

                rect = pymupdf.Rect(
                    float(item["x1"]),
                    float(item["y1"]),
                    float(item["x2"]),
                    float(item["y2"])
                )

                page.add_rect_annot(rect)

            else:

                raise ValueError(
                    f"Unsupported annotation type: {annotation_type}"
                )

        pdf.save(
            str(new_path),
            garbage=4,
            deflate=True
        )

        pdf.close()
        pdf = None

        version = save_new_version(
            document,
            new_path,
            user["username"]
        )

    except Exception as error:

        if pdf is not None:
            pdf.close()

        new_path.unlink(missing_ok=True)

        return JSONResponse(
            {"error": str(error)},
            status_code=400
        )

    log_event(
        user["username"],
        "DOCUMENT_EDIT",
        str(document_id),
        f"PDF annotations saved as version {version}"
    )

    return JSONResponse({
        "message": "PDF annotations saved successfully.",
        "version": version
    })


# ==================================================
# PDF EDITOR ACCESS HELPERS
# ==================================================

def get_editable_pdf(request, document_id):

    user = require_login(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Login required."
        )

    document = get_document(document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    if not can_access(user, document_id, "EDIT"):
        raise HTTPException(
            status_code=403,
            detail="Edit permission required."
        )

    if Path(document["name"]).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="This is not a PDF."
        )

    current_path = UPLOAD_DIR / document["stored_name"]

    if not current_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found."
        )

    return user, document, current_path


# ==================================================
# CREATE NEW PDF VERSION
# ==================================================

def create_pdf_version(
    document,
    user,
    operation,
    arguments
):

    current_path = UPLOAD_DIR / document["stored_name"]

    new_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"

    operations = {

        "add_text": pdf_editor_service.add_text,

        "replace_text": pdf_editor_service.replace_text,

        "delete_text": pdf_editor_service.delete_text,

        "insert_image": pdf_editor_service.insert_image,

        "replace_image": pdf_editor_service.replace_image,

        "delete_image": pdf_editor_service.delete_image,

        "add_comment": pdf_editor_service.add_comment,

        "add_text_box": pdf_editor_service.add_text_box,

        "add_signature": pdf_editor_service.add_signature,

        "add_highlight": pdf_editor_service.add_highlight,

        "add_rectangle": pdf_editor_service.add_rectangle,

        "add_drawing": pdf_editor_service.add_drawing,

        "delete_annotation": pdf_editor_service.delete_annotation,

        "add_page": pdf_editor_service.add_page,

        "rotate_page": pdf_editor_service.rotate_page,

        "delete_page": pdf_editor_service.delete_page,

        "reorder_pages": pdf_editor_service.reorder_pages,

    }

    function = operations.get(operation)

    if function is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported PDF editing operation."
        )

    try:

        function(
            str(current_path),
            str(new_path),
            **arguments
        )

        version = save_new_version(
            document,
            new_path,
            user["username"]
        )

        log_event(
            user["username"],
            "PDF_EDIT",
            str(document["id"]),
            f"{operation}: saved version {version}"
        )

        return {
            "message": "PDF updated successfully.",
            "operation": operation,
            "version": version
        }

    except HTTPException:
        new_path.unlink(missing_ok=True)
        raise

    except Exception as error:

        new_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# ==================================================
# PDF STUDIO BATCH SAVE
# ==================================================

@router.post("/documents/{document_id}/pdf-editor/save")
async def save_pdf_studio_changes(
    request: Request,
    document_id: int
):

    user, document, current_path = get_editable_pdf(
        request,
        document_id
    )

    new_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"
    working_path = current_path
    temporary_paths = []

    try:

        data = await request.json()

        operations_list = data.get("operations", [])

        if not isinstance(operations_list, list) or not operations_list:
            raise ValueError("No PDF changes were provided.")

        if len(operations_list) > 100:
            raise ValueError("Maximum 100 operations allowed per save.")

        operation_functions = {
            "text": pdf_editor_service.add_text,
            "add_text": pdf_editor_service.add_text,
            "comment": pdf_editor_service.add_comment,
            "add_comment": pdf_editor_service.add_comment,
            "signature": pdf_editor_service.add_signature,
            "add_signature": pdf_editor_service.add_signature,
            "highlight": pdf_editor_service.add_highlight,
            "add_highlight": pdf_editor_service.add_highlight,
            "rectangle": pdf_editor_service.add_rectangle,
            "add_rectangle": pdf_editor_service.add_rectangle,
        }

        for index, item in enumerate(operations_list):

            if not isinstance(item, dict):
                raise ValueError("Invalid PDF operation.")

            operation_type = item.get("type")

            function = operation_functions.get(operation_type)

            if function is None:
                raise ValueError(
                    f"Unsupported operation: {operation_type}"
                )

            page_number = int(item.get("page", 0))

            if page_number < 1:
                raise ValueError("Invalid page number.")

            x = float(item.get("x", 0))
            y = float(item.get("y", 0))

            if operation_type in ("text", "add_text"):

                text = str(item.get("text", "")).strip()

                if not text:
                    raise ValueError("Text cannot be empty.")

                if len(text) > 5000:
                    raise ValueError("Text is too long.")

                arguments = {
                    "page_number": page_number,
                    "x": x,
                    "y": y,
                    "text": text,
                    "font_size": float(item.get("fontSize", 14))
                }

            elif operation_type in ("signature", "add_signature"):

                text = str(item.get("text", "")).strip()

                if not text:
                    raise ValueError("Signature cannot be empty.")

                if len(text) > 500:
                    raise ValueError("Signature text is too long.")

                arguments = {
                    "page_number": page_number,
                    "x": x,
                    "y": y,
                    "signature_text": text
                }

            elif operation_type in ("comment", "add_comment"):

                text = str(item.get("text", "")).strip()

                if not text:
                    raise ValueError("Comment cannot be empty.")

                if len(text) > 5000:
                    raise ValueError("Comment is too long.")

                arguments = {
                    "page_number": page_number,
                    "x": x,
                    "y": y,
                    "text": text
                }

            else:

                width = float(item.get("width", 130))
                height = float(item.get("height", 24))

                if width <= 0 or height <= 0:
                    raise ValueError("Invalid shape dimensions.")

                arguments = {
                    "page_number": page_number,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height
                }

            if index == len(operations_list) - 1:
                output_path = new_path
            else:
                output_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"

            function(
                str(working_path),
                str(output_path),
                **arguments
            )

            if working_path != current_path:
                temporary_paths.append(working_path)

            working_path = output_path

        version = save_new_version(
            document,
            new_path,
            user["username"]
        )

    except HTTPException:
        new_path.unlink(missing_ok=True)
        raise

    except Exception as error:

        new_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    finally:

        for temporary_path in temporary_paths:
            temporary_path.unlink(missing_ok=True)

    log_event(
        user["username"],
        "PDF_EDIT",
        str(document_id),
        f"PDF Studio saved version {version}"
    )

    return JSONResponse({
        "message": "PDF changes saved successfully.",
        "version": version
    })


# ==================================================
# GET PDF INFORMATION
# ==================================================

@router.get("/documents/{document_id}/pdf-editor/info")
async def pdf_editor_info(
    request: Request,
    document_id: int
):

    user = require_login(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Login required."
        )

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "READ"):
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    if Path(document["name"]).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Not a PDF."
        )

    file_path = UPLOAD_DIR / document["stored_name"]

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found."
        )

    try:

        return pdf_editor_service.get_pdf_info(
            str(file_path)
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# ==================================================
# GENERIC PDF EDIT OPERATION
# ==================================================

@router.post("/documents/{document_id}/pdf-editor/{operation}")
async def pdf_editor_operation(
    request: Request,
    document_id: int,
    operation: str
):

    user, document, current_path = get_editable_pdf(
        request,
        document_id
    )

    try:

        data = await request.json()

        if not isinstance(data, dict):
            raise ValueError("Invalid request data.")

        if operation in ("insert_image", "replace_image"):

            image_name = data.pop("image_name", "")

            if (
                not image_name
                or Path(image_name).name != image_name
                or Path(image_name).suffix.lower()
                not in (".png", ".jpg", ".jpeg")
            ):
                raise ValueError("Invalid image filename.")

            image_path = (
                UPLOAD_DIR / image_name
            ).resolve()

            if image_path.parent != UPLOAD_DIR.resolve():
                raise ValueError("Invalid image path.")

            if not image_path.exists():
                raise ValueError("Image file not found.")

            if operation == "insert_image":
                data["image_path"] = str(image_path)

            else:
                data["new_image_path"] = str(image_path)

        return create_pdf_version(
            document,
            user,
            operation,
            data
        )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# ==================================================
# UPLOAD IMAGE FOR PDF EDITING
# ==================================================

@router.post("/documents/{document_id}/pdf-editor/upload-image")
async def upload_pdf_editor_image(
    request: Request,
    document_id: int,
    file: UploadFile = File(...)
):

    user, document, current_path = get_editable_pdf(
        request,
        document_id
    )

    extension = Path(file.filename or "").suffix.lower()

    if extension not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(
            status_code=400,
            detail="Only PNG and JPG images are supported."
        )

    contents = await file.read()

    if not contents or len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image must be between 1 byte and 5 MB."
        )

    image_name = f"{uuid4().hex}{extension}"

    image_path = UPLOAD_DIR / image_name

    try:

        file_type = "png" if extension == ".png" else "jpeg"

        image_document = pymupdf.open(
            stream=contents,
            filetype=file_type
        )

        image_document.close()

        image_path.write_bytes(contents)

    except Exception:

        image_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="Invalid image file."
        )

    log_event(
        user["username"],
        "PDF_IMAGE_UPLOAD",
        str(document_id),
        "Uploaded an image for PDF editing."
    )

    return {
        "message": "Image uploaded.",
        "image_name": image_name
    }


# ==================================================
# DOCUMENT PREVIEW
# ==================================================

@router.get("/documents/{document_id}/preview")
async def preview_document(
    request: Request,
    document_id: int
):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "READ"):
        return JSONResponse(
            {"error": "Document not found or access denied."},
            status_code=404
        )

    file_path = UPLOAD_DIR / document["stored_name"]

    if not file_path.exists():
        return JSONResponse(
            {"error": "Document file not found."},
            status_code=404
        )

    extension = file_path.suffix.lower()

    if extension == ".pdf":

        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline",
                "X-Content-Type-Options": "nosniff"
            }
        )

    if extension in (".txt", ".csv"):

        return FileResponse(
            path=file_path,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": "inline",
                "X-Content-Type-Options": "nosniff"
            }
        )

    return JSONResponse(
        {"error": "Preview is not available for this file type."},
        status_code=415
    )


# ==================================================
# DOWNLOAD ORIGINAL OR LATEST VERSION
# ==================================================

@router.get("/documents/{document_id}/download")
async def download_document(
    request: Request,
    document_id: int,
    version: str = None
):

    user = require_login(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    document = get_document(document_id)

    if not document or not can_access(user, document_id, "READ"):
        return JSONResponse(
            {"error": "Document not found or access denied."},
            status_code=404
        )

    if version not in ("original", "latest"):

        return templates.TemplateResponse(
            request=request,
            name="download_choice.html",
            context={
                "user": user,
                "document": document
            }
        )

    connection = get_connection()

    try:

        if version == "original":

            row = connection.execute(
                """
                SELECT *
                FROM document_versions
                WHERE document_id = ?
                ORDER BY version_number ASC
                LIMIT 1
                """,
                (document_id,)
            ).fetchone()

        else:

            row = connection.execute(
                """
                SELECT *
                FROM document_versions
                WHERE document_id = ?
                ORDER BY version_number DESC
                LIMIT 1
                """,
                (document_id,)
            ).fetchone()

    finally:
        connection.close()

    if not row:
        return JSONResponse(
            {"error": "Document version not found."},
            status_code=404
        )

    file_path = UPLOAD_DIR / row["stored_name"]

    if not file_path.exists():
        return JSONResponse(
            {"error": "Document file not found."},
            status_code=404
        )

    log_event(
        user["username"],
        "DOCUMENT_DOWNLOAD",
        str(document_id),
        f"Downloaded {version} version"
    )

    return FileResponse(
        path=file_path,
        filename=document["name"],
        media_type="application/octet-stream",
        content_disposition_type="attachment"
    )