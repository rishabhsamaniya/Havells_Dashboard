# Windows Setup & Execution Guide
## Havells Billing Intelligence & MIS Analytics Dashboard

This guide provides end-to-end instructions for running the application locally on **Windows 10 / Windows 11**.

---

### Prerequisites

1. **Python 3.10+ (Recommended: Python 3.11, 3.12, or 3.14)**
   - Download from [python.org](https://www.python.org/downloads/)
   - **Important**: During installation, check the box: **"Add Python to PATH"**.

2. **Database Choice**:
   - **Option A (Zero-Setup, Instant)**: SQLite is built into Python. No installation required. Runs out of the box.
   - **Option B (Production Primary)**: PostgreSQL 14, 15, or 16 installed locally or accessed via network.

---

### Step 1: Open PowerShell or Command Prompt

Open Windows Terminal, PowerShell, or Command Prompt (`cmd.exe`) and navigate to the project directory:

```powershell
cd C:\path\to\Havells_Billing
```

---

### Step 2: Create and Activate Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# (Or if using Command Prompt CMD):
# venv\Scripts\activate.bat
```

> *Note for PowerShell users*: If script execution is restricted, run:  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

### Step 3: Install Required Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Environment & Database Configuration

Copy the example environment file:

```powershell
copy .env.example .env
```

#### Database Option A: SQLite (Default, Zero-Configuration)
Leave `DB_ENGINE=` empty in your `.env` file. The application will automatically initialize and use `db.sqlite3`.

#### Database Option B: PostgreSQL
If using PostgreSQL, install PostgreSQL for Windows from [postgresql.org](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads), create a database:

```sql
CREATE DATABASE havells_billing_db;
```

Then edit `.env` with your PostgreSQL credentials:
```ini
DB_ENGINE=django.db.backends.postgresql
DB_NAME=havells_billing_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

---

### Step 5: Run Database Migrations

```powershell
python manage.py migrate
```

---

### Step 6: Bootstrap Superuser & Import Reference Dataset

Run the automated bootstrapping command:

```powershell
python manage.py setup_havells_data
```

This single command will:
1. Create the default administrator:
   - **Username**: `admin`
   - **Password**: `admin123`
2. Configure default STORY business metric definitions.
3. Ingest the reference file `sample_data/Havells Billing Apr to Aug-2026.xlsx`.
4. Perform an instant penny-to-penny mathematical reconciliation check against the raw Excel file.

---

### Step 7: Launch the Application

```powershell
python manage.py runserver 127.0.0.1:8000
```

Open your web browser and navigate to:  
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Log in using:
- **Username**: `admin`
- **Password**: `admin123`

---

### Step 8: Running Automated Tests

To verify all reconciliation tests, KPI calculations, and exports:

```powershell
python manage.py test apps.analytics
```

---

### Troubleshooting on Windows

1. **`psycopg` binary issues**:  
   `requirements.txt` specifies `psycopg[binary]>=3.1.18`, which includes pre-compiled binary wheels for Windows. No Visual C++ build tools are required.
2. **File permissions**:  
   Ensure the `media/` and `static/` directories have read/write access.
3. **Port 8000 already in use**:  
   Run on a different port:  
   `python manage.py runserver 127.0.0.1:8080`
