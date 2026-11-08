# TrustVault – Secure Document Management System

TrustVault is a secure document management application that allows users to upload, store, manage, share, and access documents based on role-based permissions.

The application provides separate access for administrators, document owners, and viewers. It also supports document versioning, audit logging, and permission-based document operations.

## Features

- User registration and login
- Administrator login and dashboard
- Role-Based Access Control (RBAC)
- Secure document upload and storage
- Document sharing between users
- Read and Edit permissions
- Document preview and download
- Document version management
- PDF document editing
- Audit logs to track user activities
- Separate access for administrators, document owners, and viewers

## Technology Stack

### Frontend
- HTML
- CSS
- JavaScript
- Jinja2 Templates

### Backend
- Python
- FastAPI

### Database
- SQLite

### Document Processing
- PyMuPDF
- python-docx

## Project Structure

```text
TrustVault/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── main.py
│   │   └── database.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── templates/
│   └── static/
│
├── README.md
└── ...
```

*This is a simplified overview of the project structure.*

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/vishnu482/TrustVault.git
```

### 2. Navigate to the Project Folder

```bash
cd TrustVault
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv
```

### 4. Activate the Virtual Environment

**Windows:**

```powershell
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

## Administrator Login
Administrator Login
| Field | Value |
|---|---|
| Username | `admin` |
| Password | `Admin@12345` |
| Role | Administrator |

Configure the administrator credentials before starting the application.

**Windows PowerShell:**

```powershell
$env:TRUSTVAULT_ADMIN_USERNAME="admin"
$env:TRUSTVAULT_ADMIN_PASSWORD="your_admin_password"
$env:TRUSTVAULT_ADMIN_NAME="Administrator"
```

**Linux / macOS:**

```bash
export TRUSTVAULT_ADMIN_USERNAME="admin"
export TRUSTVAULT_ADMIN_PASSWORD="your_admin_password"
export TRUSTVAULT_ADMIN_NAME="Administrator"
```

For deployment, configure these variables in your hosting platform's environment settings.

**Security note:** Do not commit the actual administrator password to GitHub. The password should remain private.

## Demo User Credentials

The following demo accounts are available for testing.

| Username | Password | Role |
|---|---|---|
| `demo_owner` | `DemoOwner@123` | Document Owner |
| `demo_viewer` | `DemoViewer@123` | Viewer |


**Note:** Demo accounts are intended for testing purposes only.

## Login Credentials

The following table contains the administrator and demo-user login details.

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@12345` | Administrator |
| `demo_owner` | `DemoOwner@123` | Document Owner |
| `demo_viewer` | `DemoViewer@123` | Viewer |

## User Roles and Permissions

TrustVault uses Role-Based Access Control (RBAC) to manage document access.

| Role | Permissions |
|---|---|
| Administrator | Manage users, documents, permissions, and application activities |
| Document Owner | Upload, manage, edit, and share owned documents |
| Viewer | View and download documents when permission is granted |

### Demo Document Permissions

| Document Type | Permission |
|---|---|
| PDF | Read |
| TXT | Edit |
| DOCX | No access |
| CSV | No access |

Access depends on the permissions assigned to each user and document.

## Running the Application

From the project root directory, run:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open the application in your browser:

```text
http://127.0.0.1:8000
```

## Security

- Passwords are stored as hashes rather than plain text.
- Role-based permissions control document access.
- Users can access documents according to their assigned permissions.
- Audit logs help track important user activities.
- Administrator credentials are configured through environment variables.
- Use HTTPS in production.
- Configure persistent storage for the database and uploaded documents.
- Change default demo passwords or disable demo accounts when they are not needed.

## Future Enhancements

- Cloud-based document storage
- Multi-factor authentication
- Advanced document search
- Improved document activity reports
- Additional file format support
- Enhanced security and monitoring

## Author

**Vishnu Kanigelpula**

GitHub: https://github.com/vishnu482

## License

This project is developed for educational and demonstration purposes.