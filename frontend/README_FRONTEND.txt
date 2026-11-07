# TrustVault – Frontend Documentation

## 1. Project Overview

TrustVault is a secure document management and sharing platform. Its frontend provides interfaces for users and administrators to manage documents, control access permissions, and monitor document-related activities.

The frontend is built using HTML, CSS, JavaScript, and Jinja2 templates. It is integrated with the FastAPI backend to display application data and support user interactions.

## 2. Technologies Used

- **HTML5** – Structure of web pages.
- **CSS3** – Styling, layouts, and responsive design.
- **JavaScript** – Client-side interactions and interface functionality.
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

*This structure represents the frontend files; individual filenames may vary depending on the implementation.*

## 4. User Interface Modules

### Login and Registration
- User login interface.
- New user registration.
- Form validation and error messages.
- Authentication through the FastAPI backend.

### User Dashboard
- Displays document overview and relevant statistics.
- Shows document information.
- Provides navigation to workspace sections.

### Document Management
- Displays available documents.
- Shows document names, owners, categories, and upload dates.
- Provides document details and management options.
- Supports document preview and download based on permissions.

### Document Upload
- Provides an interface for uploading documents.
- Supports the application's configured file formats.
- Displays upload status and validation messages.

### Shared Documents
- Displays documents shared with the logged-in user.
- Provides access to shared resources according to assigned permissions.

### Permission Management
- Provides an interface for managing document access.
- Supports READ and EDIT permission concepts.
- Allows authorized users to manage sharing permissions.

### Audit Trail
- Displays recorded document and account activities.
- Helps track important user actions.

### Profile
- Displays user account information.

## 5. Administrator Interface

TrustVault provides a separate administrator interface with dedicated pages.

| Module | Description |
|---|---|
| Admin Dashboard | Displays platform statistics and recent activity. |
| User Management | Displays registered users and account information. |
| Document Management | Displays documents belonging to different users. |
| Permission Management | Allows authorized administrators to manage READ and EDIT access. |
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

The design uses a consistent blue-and-white visual theme across the user workspace and administrator pages.

## 7. Backend Integration

The frontend integrates with the FastAPI backend.

- Jinja2 templates receive dynamic information from backend routes.
- Template variables and loops display database information.
- CSS and JavaScript files are served through FastAPI static file mounting.
- Form submissions and document operations are handled through backend routes.
- Authentication and authorization are enforced on the server.

### Static File Configuration

The frontend static directory is served through FastAPI.

Example configuration:

```python
from fastapi.staticfiles import StaticFiles

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "frontend" / "static")),
    name="static"
)
```

### Template Rendering

FastAPI uses Jinja2 to render frontend pages.

Example:

```python
return templates.TemplateResponse(
    request=request,
    name="dashboard.html",
    context={}
)
```

## 8. Security Considerations

- Frontend validation improves user experience but does not replace server-side validation.
- Uploaded files must be validated on the FastAPI backend.
- Authorization must be checked before document viewing, editing, sharing, or downloading.
- Passwords and sensitive credentials must never be exposed in frontend code.
- The document storage directory must not be exposed through public static URLs.
- Protected documents must be delivered through authorized backend routes.

## 9. How to Run the Project

### 1. Open the Project Folder

Open the TrustVault project directory in a terminal.

### 2. Navigate to the Backend

```bash
cd backend
```

### 3. Start the FastAPI Application

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Open the Application

Open the following URL in your browser:

```text
http://127.0.0.1:8000
```

### 5. Administrator Login

Open the administrator login page:

```text
http://127.0.0.1:8000/admin/login
```

Administrator credentials are configured through environment variables. Demo-user credentials are documented in the main project README.

## 10. Development Guidelines

- Follow modular frontend architecture.
- Keep HTML templates organized.
- Maintain consistent styling across pages.
- Use JavaScript for client-side interactions.
- Pass dynamic data through Jinja2 template contexts.
- Validate all inputs on the backend.
- Enforce authorization for protected operations.
- Avoid exposing sensitive information.
- Test important user and administrator workflows.

## 11. Future Enhancements

- Improve responsive design for mobile devices.
- Add advanced document search and filtering.
- Improve accessibility.
- Enhance document preview functionality.
- Improve frontend loading and error states.
- Add additional user-interface improvements.

---

**Project Name:** TrustVault  
**Module:** Frontend Development  
**Technologies:** HTML5, CSS3, JavaScript, Jinja2, FastAPI