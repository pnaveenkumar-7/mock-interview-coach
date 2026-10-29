# Adaptive AI Mock Interview Coach (BCA Final Year Project)

An adaptive mock interview preparation web application for students and placement officers, powered by Flask and AI.

---

## Project Structure

```text
finalyear project/
├── .env                  # Local environment configuration (secret keys, not committed)
├── .env.example          # Template for environment variables
├── .gitignore            # Git exclusion rules (.env, database, virtual environment)
├── config.py             # Configuration loader from environment variables
├── PROJECT_CONTEXT.md    # High-level project specifications and architectural guidelines
├── requirements.txt      # Python dependencies
├── run.py                # Application entry point
├── README.md             # Setup and usage documentation
└── app/
    ├── __init__.py       # Application factory (`create_app`) and /health endpoint
    ├── routes/           # Blueprints for modular route management
    │   ├── admin.py      # Admin / Placement officer routes
    │   ├── auth.py       # Authentication routes (login, register)
    │   ├── dashboard.py  # Student performance metrics routes
    │   └── interview.py  # Interview execution routes
    ├── static/           # Static assets (CSS, JS, images)
    │   ├── css/
    │   ├── js/
    │   └── images/
    └── templates/        # Jinja2 HTML templates
```

---

## Setup & Running (Windows PowerShell)

Follow these steps to set up and run the application locally:

### 1. Open PowerShell and Navigate to the Project Directory
```powershell
cd "c:\Users\navee\OneDrive\Desktop\finalyear project"
```

### 2. Create a Virtual Environment
```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```
> *Note: If PowerShell displays a script execution policy restriction error, run:*
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then run the activation script again.

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Verify Environment Variables
A default `.env` file with a pre-generated secret key is already created for immediate local development. You can customize keys as needed:
```powershell
# Copy .env.example if creating a new environment from scratch
Copy-Item .env.example .env
```

### 6. Run the Application
```powershell
python run.py
```

### 7. Test the Application
Open your browser or run in PowerShell:
- **Health check:** [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health) &rarr; `{"status": "ok"}`
- **Home:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Auth module:** [http://127.0.0.1:5000/auth/](http://127.0.0.1:5000/auth/)
- **Interview module:** [http://127.0.0.1:5000/interview/](http://127.0.0.1:5000/interview/)
- **Dashboard module:** [http://127.0.0.1:5000/dashboard/](http://127.0.0.1:5000/dashboard/)
- **Admin module:** [http://127.0.0.1:5000/admin/](http://127.0.0.1:5000/admin/)

