
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ..core.dependencies import require_login
from ..services.document_service import visible_documents

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get('/dashboard')
def dashboard(request: Request):

    u = require_login(request)

    if not u:
        return RedirectResponse('/login', status_code=303)

    if u['role'] == 'administrator':
        return RedirectResponse('/admin', status_code=303)

    docs = visible_documents(u)

    owned_documents = [
        d for d in docs
        if d['owner_username'] == u['username']
    ]

    shared_documents = [
        d for d in docs
        if d['owner_username'] != u['username']
    ]

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": u,
            "documents": docs,
            "owned_documents": owned_documents,
            "shared_documents": shared_documents
        }
    )
