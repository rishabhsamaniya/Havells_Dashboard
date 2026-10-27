# Havells Billing Intelligence & MIS Analytics Dashboard

A production-quality Django web application that converts Excel billing sheets into an interactive executive MIS analytics dashboard with detailed business insights, Relationship Manager (RM) performance analytics, payment reconciliations, monthly comparisons, category analysis, full Profit & Loss (P&L) statements, and downloadable consolidated workbooks.

![Application Badge](https://img.shields.io/badge/Havells-Billing_MIS_Analytics-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django](https://img.shields.io/badge/Django-5.0%2B-green)
![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLite-indigo)
![Currency](https://img.shields.io/badge/Format-Indian_Currency_INR-success)
![Reconciliation](https://img.shields.io/badge/Reconciliation-100%25%20Match-success)

---

## 🌟 Key Application Features

### 1. Executive MIS Dashboard
- **12 Dynamic Financial KPIs**: Total Billing Amount, Total Amount Paid, Total STORY Margin, STORY % of Billing, Unique Dealers, Unique Firms, Average per Transaction, Average per Dealer, Highest Billing Month, Top Billing RM, Top STORY RM, MoM Growth %.
- **Standardized Indian Currency Formatting**: All numbers, sums, and transaction amounts are displayed in proper Indian Currency format (e.g. `₹88,77,840.46` with Lakhs/Crores commas and exact paisa).
- **Interactive Visualizations (Plotly.js)**:
  - RM Performance volume vs STORY margin combo chart.
  - Experience Category mix donut chart with threshold grouping (< 9% into "Others").
  - Monthly trajectory area chart (Billing vs Paid vs STORY).
  - Month-on-Month billing momentum growth chart.
- **Global Dynamic Filter Bar**: Multi-dimensional filtering by Month, RM, Payment SPOC, Experience Category, Payment Status, and text search across Dealer Code, Firm Name, and RM.

### 2. Profit & Loss (P&L) Financial Intelligence Dashboard (`/pnl/`)
- **Executive P&L Headline Cards**: Gross Billing Revenue, Direct Fulfillment Cost, Net Gross Profit (STORY), Cost-to-Income Ratio, Net Profit Margin %, and Annual Run-Rate Revenue & Profit projections.
- **Interactive Visual Analytics**:
  - Revenue vs Cost vs Net Profit monthly comparison (Grouped Bar Chart).
  - Profitability Margin % Trend across months (Line Chart).
  - Financial Waterfall Bridge (Gross Invoiced Revenue $\rightarrow$ Fulfillment Cost $\rightarrow$ Net Gross Profit).
  - Cumulative Net Profit Progression across periods (Area Chart).
- **Monthly P&L Ledger Statement**: Detailed ledger tracking month-by-month financial performance, MoM revenue growth %, MoM profit growth %, and dealer reach.
- **Quarterly Financial Summary**: Q1 vs Q2 comparison of revenue, direct fulfillment costs, and net margins.
- **Category & RM Profitability Matrices**: Margin contribution rankings identifying high-yield experiences and sales leaders.
- **Direct Excel Export**: Export dedicated P&L statements (`.xlsx`) with formatted Monthly and Annual/Quarterly sheets.

### 3. Dedicated Business Analytics Modules
- **RM Performance Analytics**: Evaluates team members across sales volume, collected payments, STORY margin, transactions, dealer reach, average ticket size, and target vs achievement tracking.
- **Monthly Billing & MoM Trends**: Chronological progression, MoM growth rates, RM contribution heatmaps, and category breakdowns.
- **STORY Analysis & Outlier Detection**: Deep dive into STORY margins, distributions (Positive, Zero, Negative records), top positive transactions, and negative margin exceptions.
- **Experience Category Analytics**: Dynamic grouping with $\ge 9\%$ displayed individually (Dine-Out, Salon, Spa, Gym) and $< 9\%$ combined into a single unified "Others" category (`4.70%`).
- **Payment Reconciliation**: Compares gross billing against amounts paid, analyzes net differences, monitors SPOC collection performance, and flags dealer variances.
- **Payment SPOC Analytics**: Workload monitoring and payment balancing by assigned coordinator.
- **Dealer & Firm Analytics**: Dealer billing frequency, top 50 partners, and dealers with negative or zero margins.
- **Transaction Explorer**: Server-side paginated ledger with column sorting, status badges, and source row audit inspect modals.

### 4. Excel Upload & Intelligent Intake Engine
- **Multi-Worksheet Discovery**: Automatically inspects `.xlsx` and `.xls` workbooks, discovers all available worksheets (e.g. `Master`, `Summary`), and previews the first 50 rows.
- **Flexible Column Mapping**: Intelligently auto-maps varying Excel headers (e.g., `DealerCode` vs `Dealer Code` vs `DMS Code`) to canonical internal fields.
- **Audit Source Preservation**: Preserves unmapped raw columns in structured JSON fields for audit compliance.
- **Duplicate Detection & Strategy Control**: SHA-256 file hashing prevents accidental double-counting, giving users the choice to either "Import as new period" or "Replace previous import".
- **Rejection Logging**: Invalid or malformed rows are never silently discarded; users can download rejected records with row numbers and exact rejection reasons.
- **Penny-to-Penny Source Reconciliation**: Dedicated reconciliation page comparing raw Excel worksheet sums directly against active database records down to the exact paisa (₹0.00 difference).

### 5. Governance, Quality, & Automated Reporting
- **Data Quality & Exception Management**: Detects duplicate candidates, negative billing amounts, negative STORY values, and missing mandatory fields with full review/sign-off workflows.
- **Editable Category Normalization**: Allows administrators to standardize spelling variations (e.g. `Dine-Out` / `Dine out`, `Spa` / `SPA`) while permanently preserving original source text.
- **Consolidated Multi-Sheet MIS Export**: Downloads formatted Excel workbooks containing 8 stylized tabs with Indian currency formatting (`[$₹-en-IN]#,##,##0.00`), summary KPIs, and audit detail.
- **Complete Audit Trail**: Tracks all imports, category normalizations, metric modifications, quality reviews, and user logins.

---

## 🏗️ Technology Architecture

- **Backend**: Python 3.10+, Django 5.x, Django REST Framework
- **Data Processing**: Pandas, NumPy, OpenPyXL
- **Database**: PostgreSQL as primary (with automatic zero-config fallback to SQLite for local development)
- **Frontend**: HTML5, Vanilla CSS3 Design System, Bootstrap 5, Bootstrap Icons
- **Visual Analytics**: Plotly.js for client-side interactive charts

---

## 📂 Project Structure

```text
Havells_Billing/
├── apps/
│   ├── analytics/          # Core analytics, P&L module, models, views, and services
│   │   ├── services/       # AnalyticsService (KPIs, Category Mix, P&L) & ExportService
│   │   ├── models.py       # BillingTransaction & Target models
│   │   └── views.py        # Dashboard, P&L, RM, Monthly, Category, SPOC, Export views
│   ├── core/               # Authentication, settings, audit logging, template tags
│   │   ├── templatetags/   # mis_tags (Indian currency |inr, |inr_num filter)
│   │   └── models.py       # StoryMetricDefinition, AuditLog
│   ├── imports/            # Intake engine, file upload, header mapping, validation
│   └── quality/            # Anomaly detection, category normalization, exception sign-off
├── havells_billing_project/ # Project settings, URL routing, WSGI/ASGI configuration
├── media/                  # Uploaded workbook storage
├── sample_data/            # Reference Excel billing workbooks
├── static/                 # CSS Design System (style.css), JS assets
├── templates/              # HTML templates & partials (Dashboard, P&L, Tables, Modals)
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── manage.py               # Django CLI management script
├── requirements.txt        # Python package dependencies
├── run_server.bat          # 1-click startup script for Windows
└── run_server.sh           # 1-click startup script for macOS/Linux
```

---

## 🚀 Quick Start (Single Command Setup)

### 1. Clone Project
```bash
git clone https://github.com/rishabhsamaniya/Havells_Dashboard.git
cd Havells_Dashboard
```

### 2. Setup Virtual Environment & Install Dependencies
```bash
# On Windows:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Initialize Database, Superuser, and Ingest Reference Data
```bash
python manage.py migrate
python manage.py setup_havells_data
```

This single management command:
1. Creates the administrator account (`admin` / `admin123`)
2. Configures default STORY metric definitions
3. Ingests `sample_data/Havells Billing Apr to Aug-2026.xlsx`
4. Reconciles 923 rows and ₹88,77,840.46 billing total to the exact penny!

### 4. Start Local Development Server
```bash
python manage.py runserver
```

Open your browser at: **http://127.0.0.1:8000/**  
Log in with credentials:
- **Username**: `admin`
- **Password**: `admin123`

---

## 🧪 Running Automated Tests

```bash
python manage.py test apps.analytics
```

---

## 📄 License & Ownership
Havells Billing Intelligence & MIS Dashboard © 2026. All rights reserved.
