TRUSTVAULT FRONTEND

Files:
- templates/: Jinja2 HTML pages
- static/css/style.css: website styling
- static/js/app.js: menu, search, upload demo validation and demo messages

IMPORTANT:
This is a frontend starter with sample data. Forms and permission actions are not connected to real backend endpoints.
The browser-side file checks are for user experience only. Repeat all validation and authorization on the FastAPI server.
Do not expose the storage folder using StaticFiles or public URLs.

FastAPI configuration example (in backend/app/main.py):
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend" / "static")), name="static")

Template responses should pass request and any page data, for example:
return templates.TemplateResponse(
    request=request,
    name="dashboard.html",
    context={}
)

Create backend routes for /login, /register, /dashboard, /documents, /shared,
 /permissions, /audit, /admin, /profile, /upload, and /logout.
# TrustVault – Frontend

## 1. Project Overview

TrustVault is a secure document-sharing platform designed to help users upload, organize, manage and share documents.

The frontend provides separate interfaces for normal users and administrators. It allows users to manage their documents and access permissions, while administrators can monitor users, documents, permissions and security activities.

## 2. Technologies Used

- **HTML5** – Structure of web pages.
- **CSS3** – Styling, layouts and responsive design.
- **JavaScript** – Client-side interactions.
- **Jinja2** – Dynamic HTML rendering using backend data.
- **FastAPI** – Backend integration and page routing.

## 3. Frontend Folder Structure

```text
frontend/
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── documents.html
│   ├── document_details.html
│   ├── upload.html
│   ├── shared.html
│   ├── permissions.html
│   ├── audit_logs.html
│   ├── profile.html
│   ├── admin_login.html
│   ├── admin.html
│   ├── admin_users.html
│   ├── admin_documents.html
│   ├── admin_permissions.html
│   ├── admin_audit.html
│   └── admin_profile.html
│
└── static/
    ├── css/
    │   └── style.css
    │
    └── js/
        └── app.js
```

## 4. User Interface Modules

### Login and Registration
- User login interface.
- New user registration.
- Form validation and error messages.
- Authentication through the backend.

### User Dashboard
- Displays document overview.
- Shows document information.
- Provides navigation to other workspace sections.

### Document Management
- Displays available documents.
- Shows document names, owners, categories and dates.
- Provides document details and management navigation.

### Shared Documents
- Displays documents shared with the logged-in user.
- Helps users access shared resources.

### Permission Management
- Provides an interface for managing document access.
- Supports READ and EDIT permission concepts.

### Audit Trail
- Displays document and account activity information.

### Profile
- Displays user account information.

## 5. Administrator Interface

TrustVault provides a separate administrator interface with dedicated pages.

| Module | Description |
|---|---|
| Admin Dashboard | Displays overall platform statistics and recent activity. |
| User Management | Displays registered users and their document counts. |
| Document Management | Displays documents belonging to different users. |
| Permission Management | Allows administrators to grant and revoke READ and EDIT access. |
| Audit Logs | Displays recorded security and administrative activities. |
| Admin Profile | Displays administrator account information. |

## 6. Styling and Responsiveness

The frontend uses CSS3 for:

- Sidebar navigation.
- Dashboard layouts.
- Statistics cards.
- Tables and forms.
- Buttons and status indicators.
- Responsive layouts for different screen sizes.

The design uses a blue and white theme with a consistent visual style across the workspace and administrator pages.

## 7. Backend Integration

The frontend is integrated with the FastAPI backend.

Jinja2 templates receive dynamic information from backend routes and display it using template variables and loops.

Static CSS and JavaScript files are served through the backend static directory.

## 8. How to Run the Project

1. Open the TrustVault project folder.
2. Start the backend using the terminal:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

3. Open the application in a browser:

```text
http://127.0.0.1:8000
```

4. For administrator login, open:

```text
http://127.0.0.1:8000/admin/login
```

## 9. Important Notes

- The frontend uses Jinja2 templates rendered by FastAPI.
- The administrator interface is separated from the normal user interface.
- Access control must be enforced by backend authorization checks.
- The current project prototype uses in-memory data, so changes are not persistent after a server restart.
- Actual document storage and secure file downloads require further backend implementation.

## 10. Future Enhancements

- Improve responsive design for mobile devices.
- Add document preview functionality.
- Improve frontend form validation.
- Add search and filtering capabilities.
- Integrate persistent database storage.
- Improve accessibility and user experience.

---

**Project Name:** TrustVault  
**Module:** Frontend Development  
**Technologies:** HTML,