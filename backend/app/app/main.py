import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .core.database import init_db
from .routes.auth import router as auth_router
from .routes.dashboard import router as dashboard_router
from .routes.documents import router as documents_router
from .routes.permissions import router as permissions_router
from .routes.audit import router as audit_router
from .routes.profile import router as profile_router
from .routes.admin import router as admin_router


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")


SECRET_KEY = os.getenv("TRUSTVAULT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "TRUSTVAULT_SECRET_KEY is missing from .env"
    )


# ---------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------

app = FastAPI(title="TrustVault")


# ---------------------------------------------------------
# SESSION
# ---------------------------------------------------------

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY
)


# ---------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------

STATIC_DIR = BASE_DIR / "frontend" / "static"

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

init_db()


# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(documents_router)
app.include_router(permissions_router)
app.include_router(audit_router)
app.include_router(profile_router)
app.include_router(admin_router)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "application": "TrustVault"
    }