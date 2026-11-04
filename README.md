# TrustVault

## Secure Document Management System

TrustVault is a web-based document management application designed to provide centralized document storage, access control, document sharing, version management, and PDF editing capabilities.

The application allows users to upload, manage, preview, download, and edit documents through a simple web interface.

## Key Features

- **User Authentication:** User registration, login, and logout.
- **Role-Based Access Control:** Access permissions based on user roles.
- **Document Upload:** Upload PDF, DOC, DOCX, TXT, and CSV files.
- **Document Management:** View and manage uploaded documents.
- **Document Sharing:** Share documents with authorized users.
- **Version Management:** Maintain document versions and modification history.
- **PDF Editing:** Add text, comments, highlights, signatures, shapes, and images to PDF documents.
- **Document Preview:** Preview supported documents within the application.
- **Document Download:** Download original and latest document versions.
- **Audit Logging:** Record important user and document activities.

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

### Authentication and Security
- Session-based authentication
- Password hashing
- Role-based access control

## Project Structure

```text
TrustVault/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── routes/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── data/
│   ├── uploads/
│   └── requirements.txt
│
├── frontend/
│   ├── templates/
│   └── static/
│
├── README.md
├── PROMPTS.md
└── THREATS.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd TrustVault
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Start the Application

Run the following command from the project root:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

### 5. Open the Application

Visit:

```text
http://127.0.0.1:8000
```

## Supported File Formats

- PDF
- DOC
- DOCX
- TXT
- CSV

Maximum upload size: 10 MB (as configured in the backend).

## Security Considerations

- Protect user credentials and session information.
- Validate uploaded file types and sizes.
- Enforce authorization before document access and modification.
- Do not expose database files, uploaded documents, or secret configuration values in public repositories.
- Review the threat model in `THREATS.md`.

## Future Enhancements

- Multi-factor authentication.
- Stronger document encryption and key management.
- Cloud-based document storage.
- Advanced document search.
- Improved activity monitoring.
- Automated security testing.

## License

Specify the license applicable to this project before distributing it.