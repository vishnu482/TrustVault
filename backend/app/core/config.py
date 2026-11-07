
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# Use Render's persistent disk when configured.
# Otherwise, use local backend storage.
DATA_DIR = Path(
    os.getenv("TRUSTVAULT_DATA_DIR", str(BASE_DIR))
)

UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_FILE = DATA_DIR / "data" / "trustvault.db"

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
