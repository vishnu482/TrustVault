from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="TrustVault")

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

if not TEMPLATES_DIR.exists():
    raise RuntimeError(f"Templates directory does not exist: {TEMPLATES_DIR}")
if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory does not exist: {STATIC_DIR}")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key="trustvault-development-secret-key-change-later"
)

# DEMO DATA ONLY: all data below is stored in memory and resets on restart.
USERS = {
    "vishnu": {"username": "vishnu", "password": "1234", "name": "Vishnu", "role": "document_owner"},
    "viewer": {"username": "viewer", "password": "1234", "name": "Viewer User", "role": "viewer"},
}
ADMIN = {"username": "admin", "password": "admin123", "name": "Administrator", "role": "administrator"}

DOCUMENTS = [
    {"id": 1, "name": "Employee Policy.pdf", "owner": "Vishnu", "owner_username": "vishnu", "category": "Policy", "date": "2026-10-20", "status": "Active"},
    {"id": 2, "name": "Project Documentation.docx", "owner": "Vishnu", "owner_username": "vishnu", "category": "Documentation", "date": "2026-10-22", "status": "Active"},
    {"id": 3, "name": "Security Guidelines.pdf", "owner": "Administrator", "owner_username": "admin", "category": "Security", "date": "2026-10-25", "status": "Active"},
]

# Each permission: document_id, username, access (READ or EDIT), granted_by.
PERMISSIONS = [
    {"document_id": 1, "username": "viewer", "access": "READ", "granted_by": "admin"}
]
AUDIT_LOGS = []


def log_event(actor, action, target, details=""):
    AUDIT_LOGS.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": actor,
        "action": action,
        "target": target,
        "details": details,
    })

def current_user(request: Request):
    return request.session.get("user")

def require_login(request: Request):
    user = current_user(request)
    if not user:
        return None
    return user

def require_admin(request: Request):
    user = current_user(request)
    if not user or user.get("role") != "administrator":
        return None
    return user

def visible_documents(user):
    if user["role"] == "administrator":
        return DOCUMENTS
    allowed_ids = {
        p["document_id"] for p in PERMISSIONS
        if p["username"] == user["username"]
    }
    return [
        d for d in DOCUMENTS
        if d["owner_username"] == user["username"] or d["id"] in allowed_ids
    ]

def user_document_counts(username):
    owned = sum(1 for d in DOCUMENTS if d["owner_username"] == username)
    shared = sum(1 for p in PERMISSIONS if p["username"] == username)
    return owned, shared

@app.get("/")
def home():
    return RedirectResponse("/login", status_code=303)

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", "")).strip()
    user = USERS.get(username)
    if user and user["password"] == password:
        request.session["user"] = {
            "username": user["username"], "name": user["name"], "role": user["role"]
        }
        log_event(username, "LOGIN", "Account", "User signed in")
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html",
        context={"error": "Invalid username or password"}
    )

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/register")
async def register(request: Request):
    form = await request.form()
    name = str(form.get("name", "")).strip()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", "")).strip()
    if not name or not username or not password:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "Please fill in all fields", "name": name, "username": username}
        )
    if username in USERS or username == ADMIN["username"]:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "Username already exists", "name": name, "username": username}
        )
    USERS[username] = {
        "username": username, "password": password, "name": name, "role": "document_owner"
    }
    request.session["user"] = {"username": username, "name": name, "role": "document_owner"}
    log_event(username, "USER_REGISTERED", username, "New account created")
    return RedirectResponse("/dashboard", status_code=303)

@app.get("/admin/login")
def admin_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin_login.html")

@app.post("/admin/login")
async def admin_login(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", "")).strip()
    if username == ADMIN["username"] and password == ADMIN["password"]:
        request.session["user"] = {
            "username": ADMIN["username"], "name": ADMIN["name"], "role": ADMIN["role"]
        }
        log_event("admin", "ADMIN_LOGIN", "Admin account", "Administrator signed in")
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        request=request, name="admin_login.html",
        context={"error": "Invalid administrator username or password"}
    )

@app.get("/logout")
def logout(request: Request):
    user = current_user(request)
    if user:
        log_event(user["username"], "LOGOUT", "Account", "User signed out")
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

# ------------------------- USER ROUTES -------------------------

@app.get("/dashboard")
def dashboard(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin", status_code=303)
    docs = visible_documents(user)
    return templates.TemplateResponse(
        request=request, name="dashboard.html",
        context={"user": user, "documents": docs}
    )

@app.get("/documents")
def documents(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin/documents", status_code=303)
    return templates.TemplateResponse(
        request=request, name="documents.html",
        context={"user": user, "documents": visible_documents(user)}
    )

@app.get("/documents/{document_id}")
def open_document(document_id: int, request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    document = next((d for d in DOCUMENTS if d["id"] == document_id), None)
    if not document:
        return RedirectResponse("/documents", status_code=303)
    permitted = (
        user["role"] == "administrator"
        or document["owner_username"] == user["username"]
        or any(p["document_id"] == document_id and p["username"] == user["username"]
               for p in PERMISSIONS)
    )
    if not permitted:
        log_event(user["username"], "ACCESS_DENIED", document["name"], "Document access denied")
        return templates.TemplateResponse(
            request=request, name="error.html",
            context={"code": "403", "message": "You do not have permission to view this document."},
            status_code=403
        )
    log_event(user["username"], "DOCUMENT_VIEW", document["name"], "Document details opened")
    return templates.TemplateResponse(
        request=request, name="document_details.html",
        context={"user": user, "document": document}
    )

@app.get("/upload")
def upload(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin/documents", status_code=303)
    return templates.TemplateResponse(request=request, name="upload.html", context={"user": user})

@app.get("/permissions")
def permissions(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin/permissions", status_code=303)
    mine = [p for p in PERMISSIONS if p["username"] == user["username"]]
    return templates.TemplateResponse(
        request=request, name="permissions.html",
        context={"user": user, "documents": visible_documents(user), "permissions": mine}
    )

@app.get("/audit")
def audit(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin/audit", status_code=303)
    mine = [a for a in AUDIT_LOGS if a["actor"] == user["username"]]
    return templates.TemplateResponse(
        request=request, name="audit_logs.html",
        context={"user": user, "documents": visible_documents(user), "audit_logs": mine}
    )

@app.get("/profile")
def profile(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin/profile", status_code=303)
    return templates.TemplateResponse(request=request, name="profile.html", context={"user": user})

@app.get("/shared")
def shared(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] == "administrator":
        return RedirectResponse("/admin/documents", status_code=303)
    shared_docs = []
    for p in PERMISSIONS:
        if p["username"] == user["username"]:
            doc = next((d for d in DOCUMENTS if d["id"] == p["document_id"]), None)
            if doc:
                shared_docs.append(doc)
    return templates.TemplateResponse(
        request=request, name="shared.html",
        context={"user": user, "documents": shared_docs}
    )

# ------------------------- ADMIN ROUTES -------------------------

@app.get("/admin")
def admin_dashboard(request: Request):
    user = require_admin(request)
    if not user:
        return RedirectResponse("/admin/login", status_code=303)
    active_docs = sum(1 for d in DOCUMENTS if d["status"] == "Active")
    return templates.TemplateResponse(
        request=request, name="admin.html",
        context={
            "user": user, "documents": DOCUMENTS,
            "total_users": len(USERS) + 1,
            "total_documents": len(DOCUMENTS),
            "active_documents": active_docs,
            "total_permissions": len(PERMISSIONS),
            "security_events": len(AUDIT_LOGS),
            "recent_activity": AUDIT_LOGS[:8],
        }
    )

@app.get("/admin/users")
def admin_users(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    user_rows = []
    all_users = list(USERS.values()) + [ADMIN]
    for item in all_users:
        owned, shared_count = user_document_counts(item["username"])
        user_rows.append({
            "username": item["username"], "name": item["name"], "role": item["role"],
            "owned_count": owned, "shared_count": shared_count,
            "is_admin": item["role"] == "administrator"
        })
    return templates.TemplateResponse(
        request=request, name="admin_users.html",
        context={"user": admin, "users": user_rows, "total_users": len(user_rows)}
    )

@app.post("/admin/users/{username}/delete")
def admin_delete_user(username: str, request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    if username == ADMIN["username"] or username not in USERS:
        return RedirectResponse("/admin/users?error=Cannot+delete+this+account", status_code=303)
    removed_docs = [d for d in DOCUMENTS if d["owner_username"] == username]
    removed_ids = {d["id"] for d in removed_docs}
    DOCUMENTS[:] = [d for d in DOCUMENTS if d["owner_username"] != username]
    PERMISSIONS[:] = [
        p for p in PERMISSIONS
        if p["username"] != username and p["document_id"] not in removed_ids
    ]
    del USERS[username]
    log_event(admin["username"], "USER_DELETED", username,
              f"User deleted; {len(removed_docs)} owned document(s) also deleted")
    return RedirectResponse("/admin/users", status_code=303)

@app.get("/admin/documents")
def admin_documents(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    docs = []
    for d in DOCUMENTS:
        docs.append({**d, "permission_count": sum(1 for p in PERMISSIONS if p["document_id"] == d["id"])})
    return templates.TemplateResponse(
        request=request, name="admin_documents.html",
        context={"user": admin, "documents": docs}
    )

@app.post("/admin/documents/{document_id}/delete")
def admin_delete_document(document_id: int, request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    document = next((d for d in DOCUMENTS if d["id"] == document_id), None)
    if document:
        DOCUMENTS.remove(document)
        PERMISSIONS[:] = [p for p in PERMISSIONS if p["document_id"] != document_id]
        log_event(admin["username"], "DOCUMENT_DELETED", document["name"], "Document and its permissions deleted")
    return RedirectResponse("/admin/documents", status_code=303)

@app.get("/admin/permissions")
def admin_permissions(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    permission_rows = []
    for p in PERMISSIONS:
        doc = next((d for d in DOCUMENTS if d["id"] == p["document_id"]), None)
        permission_rows.append({
            **p,
            "document_name": doc["name"] if doc else "Deleted document",
            "user_name": USERS.get(p["username"], {}).get("name", p["username"])
        })
    return templates.TemplateResponse(
        request=request, name="admin_permissions.html",
        context={"user": admin, "documents": DOCUMENTS, "users": list(USERS.values()),
                 "permissions": permission_rows}
    )

@app.post("/admin/permissions/grant")
def admin_grant_permission(
    request: Request,
    document_id: int = Form(...),
    username: str = Form(...),
    access: str = Form(...)
):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    doc = next((d for d in DOCUMENTS if d["id"] == document_id), None)
    if not doc or username not in USERS or access not in ("READ", "EDIT"):
        return RedirectResponse("/admin/permissions?error=Invalid+permission+details", status_code=303)
    existing = next((p for p in PERMISSIONS
                     if p["document_id"] == document_id and p["username"] == username), None)
    if existing:
        existing["access"] = access
        existing["granted_by"] = admin["username"]
        action = "PERMISSION_UPDATED"
    else:
        PERMISSIONS.append({
            "document_id": document_id, "username": username,
            "access": access, "granted_by": admin["username"]
        })
        action = "PERMISSION_GRANTED"
    log_event(admin["username"], action, doc["name"], f"{access} access granted to {username}")
    return RedirectResponse("/admin/permissions", status_code=303)

@app.post("/admin/permissions/{document_id}/{username}/revoke")
def admin_revoke_permission(document_id: int, username: str, request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    before = len(PERMISSIONS)
    PERMISSIONS[:] = [
        p for p in PERMISSIONS
        if not (p["document_id"] == document_id and p["username"] == username)
    ]
    if len(PERMISSIONS) != before:
        log_event(admin["username"], "PERMISSION_REVOKED",
                  f"Document {document_id}", f"Access revoked from {username}")
    return RedirectResponse("/admin/permissions", status_code=303)

@app.get("/admin/audit")
def admin_audit(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="admin_audit.html",
        context={"user": admin, "audit_logs": AUDIT_LOGS}
    )

@app.get("/admin/profile")
def admin_profile(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="admin_profile.html", context={"user": admin}
    )
