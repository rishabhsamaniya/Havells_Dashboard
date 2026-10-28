# Havells Billing Intelligence & MIS Analytics Dashboard
## Complete Technical Specification, Architecture & Deep Features Guide

---

## 📑 Table of Contents
1. [Executive Summary & System Objectives](#1-executive-summary--system-objectives)
2. [Technology Stack & Architectural Architecture](#2-technology-stack--architectural-architecture)
3. [End-to-End System Architecture & Data Flow](#3-end-to-end-system-architecture--data-flow)
4. [Database Schema & Data Dictionary](#4-database-schema--data-dictionary)
5. [Deep Feature Engineering & Algorithms](#5-deep-feature-engineering--algorithms)
   - [5.1 Intelligent 2-Pass Header Auto-Mapping & Resilient Column Resolver](#51-intelligent-2-pass-header-auto-mapping--resilient-column-resolver)
   - [5.2 Context-Aware Month & Period Auto-Detection Engine](#52-context-aware-month--period-auto-detection-engine)
   - [5.3 Mathematical Proof of Zero-Variance Reconciliation Engine](#53-mathematical-proof-of-zero-variance-reconciliation-engine)
   - [5.4 Self-Healing / Auto-Repair Transaction Engine](#54-self-healing--auto-repair-transaction-engine)
   - [5.5 Dynamic Experience Category Mix & 9% Grouping Engine](#55-dynamic-experience-category-mix--9-grouping-engine)
   - [5.6 Profit & Loss (P&L) Financial Intelligence Suite](#56-profit--loss-pl-financial-intelligence-suite)
   - [5.7 High-Precision Decimal Arithmetic & Indian Currency Engine](#57-high-precision-decimal-arithmetic--indian-currency-engine)
6. [Business Analytics Modules Breakdown](#6-business-analytics-modules-breakdown)
   - [6.1 Executive MIS Dashboard](#61-executive-mis-dashboard)
   - [6.2 RM Performance Analytics](#62-rm-performance-analytics)
   - [6.3 Monthly Billing & MoM Growth Momentum](#63-monthly-billing--mom-growth-momentum)
   - [6.4 STORY Analysis & Outlier Detection](#64-story-analysis--outlier-detection)
   - [6.5 Payment Reconciliation & SPOC Balancing](#65-payment-reconciliation--spoc-balancing)
   - [6.6 Dealers & Firms Strategic Matrix](#66-dealers--firms-strategic-matrix)
   - [6.7 Transaction Explorer & Row Audit Inspector](#67-transaction-explorer--row-audit-inspector)
7. [Governance, Quality Control & Audit Trail](#7-governance-quality-control--audit-trail)
8. [Automated Multi-Tab MIS Export Centre](#8-automated-multi-tab-mis-export-centre)
9. [Complete URL Routing & View Reference](#9-complete-url-routing--view-reference)
10. [Local Development, Installation & Verification Guide](#10-local-development-installation--verification-guide)
11. [Production Deployment Architecture (Render & PostgreSQL)](#11-production-deployment-architecture-render--postgresql)

---

## 1. Executive Summary & System Objectives

The **Havells Billing Intelligence & MIS Automation Suite** is an enterprise-grade Django web application designed to automate, streamline, and govern the complex billing intake, financial reconciliation, Relationship Manager (RM) performance tracking, and executive MIS reporting for Havells partner billing operations.

### Core Problems Solved
1. **Manual Ingestion Errors**: Eliminates tedious manual entry and cross-verification of multi-thousand row Excel workbooks.
2. **Reconciliation Variances**: Provides mathematical proof of zero variance down to the exact paisa (`₹0.00` discrepancy) between raw Excel source files and database entries.
3. **Complex Header & Taxonomical Discrepancies**: Overcomes formatting variations, multi-line headers, missing month columns, and non-standardized category names.
4. **Dispersed Financial Visibility**: Replaces fragmented spreadsheets with an interactive, unified executive dashboard, comprehensive Profit & Loss (P&L) statements, and automated multi-tab Excel reporting.

---

## 2. Technology Stack & Architectural Architecture

| Layer | Technologies Used | Key Responsibilities |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.10 – 3.14, Django 5.x / 6.x | Application routing, business logic, ORM, transactional imports, security. |
| **Data Processing** | Pandas, NumPy, OpenPyXL | Excel parsing, high-speed vector transformations, multi-sheet workbook generation. |
| **Primary Database** | PostgreSQL (Render Production) / SQLite (Local) | ACID-compliant storage with database-level indexes on months, RMs, categories, and dealers. |
| **Frontend Framework** | HTML5, Vanilla CSS3 Custom Design System, Bootstrap 5.3, Bootstrap Icons | Responsive responsive UI, dark/light accents, mobile responsiveness. |
| **Visual Analytics** | Plotly.js | Interactive charts, financial waterfall bridges, donuts, combo bars, and area trends. |
| **Production Server** | Gunicorn 22.x, WhiteNoise 6.x | Multi-worker WSGI server with compressed static asset serving. |
| **Hosting & CI/CD** | Render PaaS, GitHub Webhook Automation | Continuous deployment on git push to the `main` branch. |

---

## 3. End-to-End System Architecture & Data Flow

```mermaid
flowchart TD
    A["Raw Excel Billing Workbook (.xlsx)"] --> B["Upload & Multi-Worksheet Discovery"]
    B --> C["SHA-256 Checksum & Duplicate Audit"]
    C --> D["Intelligent 2-Pass Column Auto-Mapper"]
    D --> E["Worksheet Header Confirmation UI"]
    E --> F["Transactional Ingestion Engine (process_import)"]
    
    subgraph Processing & Normalization
        F --> G["Summary / Total Footer Row Filter"]
        F --> H["Context-Aware Month Detector"]
        F --> I["Category Standardization & Mapping Cache"]
        F --> J["Strict Decimal Validator (parse_decimal_safe)"]
    end

    J --> K["PostgreSQL Database (ACID Transaction)"]
    K --> L["BillingTransaction Table"]
    K --> M["DataQualityIssue Table"]
    K --> N["RejectedRecord Table"]
    K --> O["AuditLog Table"]

    subgraph Analytics & Presentation
        L --> P["Zero-Variance Reconciliation View"]
        L --> Q["Executive MIS Dashboard"]
        L --> R["P&L Financial Intelligence Suite"]
        L --> S["RM & Category Analytics"]
        L --> T["Multi-Tab OpenPyXL MIS Exporter"]
    end
```

---

## 4. Database Schema & Data Dictionary

The database is built on Django's ORM and structured into four specialized applications: `apps.core`, `apps.imports`, `apps.analytics`, and `apps.quality`.

### 4.1 `BillingTransaction` (`apps/analytics/models.py`)
The central transaction entity recording every line item at paisa-level precision.

| Field Name | Type | Key Constraints / Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `BigAutoField` | Primary Key | Unique transaction identifier. |
| `import_batch` | `ForeignKey(ImportBatch)` | `on_delete=CASCADE` | Associated ingestion batch. |
| `source_row_number` | `IntegerField` | Required | 1-based source row index in the raw Excel sheet. |
| `month_label` | `CharField(50)` | Indexed | Formatted month string (e.g. `Apr'26`). |
| `transaction_date`| `DateField` | Indexed, Nullable | Derived first-of-month calendar date. |
| `financial_year` | `CharField(20)` | Default: `'2026-27'` | Indian Financial Year (April–March). |
| `rm` | `CharField(100)` | Indexed | Relationship Manager assigned to the account. |
| `dealer_code` | `CharField(100)` | Indexed | DMS / Partner unique identifier. |
| `firm_name` | `CharField(255)` | Indexed | Business firm or partner agency name. |
| `dealer_name` | `CharField(255)` | Blank=True | Proprietor or contact partner name. |
| `raw_category` | `CharField(150)` | Blank=True | Exact un-altered category string from Excel. |
| `standardized_category`| `CharField(150)` | Indexed | Normalized taxonomy (e.g., `Dine-Out`, `Salon`, `Spa`). |
| `payment_spoc` | `CharField(100)` | Indexed | Assigned payment coordinator. |
| `billing_amount` | `DecimalField(14, 2)` | Indexed, Default: `0.00` | Invoiced client gross transaction value. |
| `amount_paid` | `DecimalField(14, 2)` | Indexed, Default: `0.00` | Actual fulfillment cost / amount paid out. |
| `story_amount` | `DecimalField(14, 2)` | Indexed, Default: `0.00` | STORY margin revenue generated. |
| `calculated_difference`| `DecimalField(14, 2)`| Default: `0.00` | `billing_amount - amount_paid`. |
| `payment_status` | `CharField(30)` | Indexed, Choices | `PAID`, `PARTIAL`, `UNPAID`, `OVERPAID`. |
| `raw_source_data`| `JSONField` | Default: `dict` | Complete row audit snapshot for self-healing & audits. |

### 4.2 `ImportBatch` (`apps/imports/models.py`)
Tracks file ingestions, duplicate hashes, mapping schemas, and reconciliation sums.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `file_name` | `CharField(255)` | Original uploaded filename. |
| `file_hash` | `CharField(64)` | SHA-256 cryptographic hash of file content. |
| `uploaded_file` | `FileField` | Stored physical file in `media/uploads/`. |
| `sheet_name` | `CharField(100)` | Target worksheet selected for ingestion. |
| `total_source_rows`| `IntegerField` | Total row count in the worksheet. |
| `successful_records`| `IntegerField` | Validated records imported into the database. |
| `rejected_records` | `IntegerField` | Rows rejected due to validation errors. |
| `total_billing_amount` | `DecimalField(16, 2)` | Reconciled total billing amount. |
| `total_paid_amount`| `DecimalField(16, 2)` | Reconciled total payment amount. |
| `total_story_amount`| `DecimalField(16, 2)` | Reconciled total STORY margin amount. |
| `status` | `CharField(30)` | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `REPLACED`. |
| `is_active` | `BooleanField` | Active status (false if replaced by a newer import). |

---

## 5. Deep Feature Engineering & Algorithms

### 5.1 Intelligent 2-Pass Header Auto-Mapping & Resilient Column Resolver

#### The Engineering Challenge
In enterprise billing operations, Excel workbooks arrive from multiple field branches with unpredictable variations:
- Header names differ: `Dealer Code`, `DealerCode`, `DMS Code`, `Party Code`.
- Multi-line headers contain line breaks: `Dine-Out/Salon/Spa/\nPhotoshoot/Concert`.
- Naive substring matching (e.g. `cand in col`) causes disastrous false positives:
  - Checking `'rm' in col` mistakenly matches `'Firm Name'` (`fi-RM name`), mapping the Relationship Manager to company titles.
  - Checking `'payment' in col` mistakenly matches `'PAYMENT SPOC'` before `'Amount Paid'`, mapping monetary amounts to coordinator names (`"Himanshu"`), causing numeric parse crashes.
- Browsers submitting HTML form data normalize Unix newlines (`\n`) to CRLF (`\r\n`), breaking dictionary key lookups against Pandas DataFrames.

#### The 2-Pass Matching Algorithm
Implemented in `apps/imports/services/excel_service.py`:

```python
def clean_alpha(s):
    """Strips all whitespace and non-alphanumeric characters for deterministic matching."""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

# Pass 1: Strict Alphanumeric Normalized Match
for canonical, candidates in CANONICAL_FIELD_CANDIDATES.items():
    for raw_col in df.columns:
        if raw_col in assigned_cols:
            continue
        if clean_alpha(raw_col) in [clean_alpha(c) for c in candidates]:
            mapping[canonical] = raw_col
            assigned_cols.add(raw_col)
            break

# Pass 2: Word-Boundary Regex Match for Unassigned Fields
for canonical, candidates in CANONICAL_FIELD_CANDIDATES.items():
    if canonical in mapping:
        continue
    for raw_col in df.columns:
        if raw_col in assigned_cols:
            continue
        for cand in candidates:
            pattern = r'(?:^|[\s/_\-])' + re.escape(cand.lower().strip()) + r'(?:$|[\s/_\-])'
            if re.search(pattern, str(raw_col).lower()):
                mapping[canonical] = raw_col
                assigned_cols.add(raw_col)
                break
```

#### Resilient Ingestion Resolution (`resolved_col_map`)
When executing `process_import`, the system decouples browser-submitted keys from pandas column representations by building an intelligent lookup map that resolves strings regardless of `\r\n`, spaces, or capitalization.

---

### 5.2 Context-Aware Month & Period Auto-Detection Engine

When monthly working workbooks (e.g., `Final - Havells April Billing Working.xlsx`) are uploaded, they frequently lack a dedicated `Months` column because the entire file represents one period.

The `detect_month_from_context` engine uses a 3-tier hierarchical resolution:
1. **Tier 1 (Row Date Inspection)**: Checks row date fields (`Avail Date`, `Payment Date`). If valid timestamps are found, formats them as `MMM'YY` (e.g., `Apr'26`).
2. **Tier 2 (Worksheet & Filename Regex)**: Inspects `combined_text = f"{sheet_name} {file_name}".lower()` using word boundary regex (`\bapr\b`, `\bmay\b`, etc.) and extracts year indicators (`2026`, `'26`) $\rightarrow$ generates `Apr'26`.
3. **Tier 3 (Safe Fallback)**: Defaults gracefully to current fiscal active month without halting import execution.

---

### 5.3 Mathematical Proof of Zero-Variance Reconciliation Engine

Located in `apps/analytics/services/analytics_service.py` (`get_source_reconciliation`):
To guarantee complete trust from C-level executives and finance teams, every import batch undergoes mathematical reconciliation against the raw source file.

```python
# Automatic Footer & Grand Total Row Filtration
valid_mask = []
for _, r in df.iterrows():
    d_val = str(r.get(d_col, '') or '').strip()
    rm_val = str(r.get(rm_col, '') or '').strip()
    f_val = str(r.get(f_col, '') or '').strip()
    
    # Exclude empty rows and summary totals where primary identifiers are absent
    if (not d_val or d_val.lower() == 'nan') and \
       (not rm_val or rm_val.lower() == 'nan') and \
       (not f_val or f_val.lower() == 'nan'):
        valid_mask.append(False)
    else:
        valid_mask.append(True)

df_data = df[valid_mask] if valid_mask else df
```

#### Reconciliation Variance Metrics Audited
- **Total Record Count**: Excel source data rows vs DB rows (`diff_rows == 0`).
- **Total Gross Billing**: Raw Excel sum vs SQL `SUM(billing_amount)` (`diff_billing == 0.00`).
- **Total Amount Paid**: Raw Excel sum vs SQL `SUM(amount_paid)` (`diff_paid == 0.00`).
- **Total STORY Margin**: Raw Excel sum vs SQL `SUM(story_amount)` (`diff_story == 0.00`).
- **Status Flag**: `is_perfect_match: True` $\rightarrow$ Displays green "Exact Match" badge.

---

### 5.4 Self-Healing / Auto-Repair Transaction Engine

In the event that legacy data was imported under unmapped taxonomy or modified configurations, the system features an autonomous repair mechanism (`auto_repair_uncategorized_transactions`).

- Scans `BillingTransaction` objects where `standardized_category == 'Uncategorized'`.
- Leverages the preserved `raw_source_data` JSON payload.
- Detects original category values from raw keys.
- Normalizes them through `suggest_standardized_category`.
- Executes bulk database updates in 500-record chunks without requiring users to delete or re-upload batches.

---

### 5.5 Dynamic Experience Category Mix & 9% Grouping Engine

Located in `get_grouped_category_mix` (`analytics_service.py`):
Executive reporting requires charts to stay uncluttered while preserving granularity for key revenue drivers.

#### Dynamic Grouping Rules
1. Categories representing **$\ge 9.0\%$** of total billing volume are displayed individually (e.g., `Dine-Out` 62.6%, `Salon` 12.09%, `Spa` 11.52%, `Gym` 9.09%).
2. All categories contributing **$< 9.0\%$** (`Kids Activity`, `Photoshoot`, `Concert`, `Yoga`, `Mammography`, `Health Check-up`, `Staycation`) are combined into a single unified category named **`Others`** (4.70%).
3. Chart labels and legends automatically reflect this grouping with high-contrast text formatting for readability.

---

### 5.6 Profit & Loss (P&L) Financial Intelligence Suite

Located at route `/pnl/`, this module converts transactional billing data into a financial accounting statement.

```mermaid
graph LR
    A["Gross Invoiced Revenue (₹88,77,840.46)"] -->|Less Fulfillment Cost| B["Vendor / Partner Payouts (₹77,73,524.70)"]
    B --> C["Net Gross Profit / STORY Margin (₹11,04,315.76)"]
    C --> D["Profit Margin % (12.44%)"]
    B --> E["Cost-to-Income Ratio (87.56%)"]
```

#### Financial Visualizations Included
- **Waterfall Bridge**: Explains margin realization from Gross Invoiced Volume to Direct Cost to Net Story Profit.
- **Monthly Financial Ledger**: Chronological table showing Revenue, Direct Cost, Net Profit, Margin %, and MoM profit momentum.
- **Category Profitability Matrix**: Ranks categories by gross profit contribution and margin efficiency.
- **Quarterly Summary**: Compares Q1 (Apr–Jun) vs Q2 (Jul–Sep) financial metrics.

---

### 5.7 High-Precision Decimal Arithmetic & Indian Currency Engine

#### Avoiding Floating Point Errors
Billing systems that use standard floating-point numbers (`float`) suffer from rounding inaccuracies (e.g. `0.1 + 0.2 = 0.30000000000000004`).
- All financial fields in the database use `DecimalField(max_digits=14, decimal_places=2)`.
- Python logic utilizes Python's `decimal.Decimal` with explicit `.quantize(Decimal('0.01'))`.

#### Standardized Indian Currency Formatting (`|inr`, `|inr_num`)
Indian accounting standard requires comma placement in the format `₹XX,XX,XXX.XX` (Lakhs and Crores), unlike Western formatting (`₹XXX,XXX,XXX.XX` Millions/Billions).

Custom Django template filters (`apps/core/templatetags/mis_tags.py`) format values cleanly:
- `8877840.46` $\rightarrow$ `₹88,77,840.46`
- Negative values format cleanly as `-₹5,000.00`.

---

## 6. Business Analytics Modules Breakdown

### 6.1 Executive MIS Dashboard (`/`)
- **12 Dynamic Headline KPIs**: Total Billing, Total Paid, Total STORY, STORY %, Total Transactions, Unique Dealers, Unique Firms, Average Ticket Size, Average Billing per Dealer, Highest Billing Month, Top Revenue RM, Top STORY RM.
- **Global Filter Bar**: Filters by Month, RM, Payment SPOC, Experience Category, Payment Status, and text search.
- **Synchronized Charts**: Monthly Billing vs Margin trends, RM Volume comparison, Category Share Donut.

### 6.2 RM Performance Analytics (`/rm/`)
- Evaluates sales executives across Total Billing, Collected Payments, STORY Margin, Deal Count, Dealer Reach, and Average Ticket Size.
- **Target Tracking**: Compares actual achievement against monthly goals configured in `MonthlyRMTarget`.

### 6.3 Monthly Billing & MoM Growth Momentum (`/monthly/`)
- Chronological revenue and margin trajectory across billing periods.
- Calculates month-on-month velocity (`+15.2%`, `-4.8%`) and RM participation heatmaps.

### 6.4 STORY Analysis & Outlier Detection (`/story/`)
- Evaluates STORY margin health.
- Identifies Positive Margin transactions, Zero Margin transactions, and Negative Margin business exceptions for management review.

### 6.5 Payment Reconciliation & SPOC Balancing (`/reconcile/`, `/spoc/`)
- Monitors accounts receivable vs payouts across payment coordinators (`Himanshu`, `Supriya`, `Rishabh`).
- Identifies uncollected balances, partial payments, and dealer credit balances.

### 6.6 Dealers & Firms Strategic Matrix (`/dealers/`)
- Ranks the top 50 revenue-generating firms and dealerships.
- Highlights low-margin or loss-making accounts requiring renegotiation.

### 6.7 Transaction Explorer & Row Audit Inspector (`/transactions/`)
- Server-side paginated ledger (50 records/page) with full-text search across dealer codes, firm names, and invoice numbers.
- **Inspect Source Data Modal**: Inspects the immutable original row JSON payload directly from the raw Excel spreadsheet.

---

## 7. Governance, Quality Control & Audit Trail

### 7.1 Data Quality & Exception Management (`/quality/`)
The system detects 4 automated business exceptions:
1. `POTENTIAL_DUPLICATE`: Flagged when matching Dealer Code, Month, Billing Amount, and Category occur.
2. `BUSINESS_EXCEPTION`: Triggered on negative billing amounts or negative STORY margins.
3. `DATA_INTEGRITY`: Missing mandatory values or invalid dates.
4. `UNRESOLVED_TAXONOMY`: Unmapped categories requiring standardization.

### 7.2 Category Normalization Studio (`/quality/categories/`)
Enables administrators to map regional variations (e.g., `Dine Out`, `Dine-out`, `Buffet/Ala-Carte`) to standard categories (`Dine-Out`) while preserving original cell text in `raw_category`.

### 7.3 Immutable Audit Trail (`/audit/`)
Tracks all system actions:
- `IMPORT`: Batch uploads, rows processed, and filenames.
- `REPLACE`: Batch deactivations.
- `NORMALIZE`: Category taxonomy modifications.
- `TARGET_UPDATE`: Monthly quota adjustments.
- Records timestamp, acting user, IP address, and JSON before/after state diffs.

---

## 8. Automated Multi-Tab MIS Export Centre

Located at route `/export/`, powered by `apps/analytics/services/export_service.py`:
Generates formatted Excel workbooks (`.xlsx`) containing 8 styled tabs:
1. **Executive Summary**: High-level KPI summary with Indian accounting formatting.
2. **Monthly Trends**: Chronological MoM metrics.
3. **RM Performance**: Sales representative leaderboard and rankings.
4. **Category Breakdown**: Experience category revenues and margins.
5. **SPOC Performance**: Payment coordinator collections.
6. **Dealer Analytics**: Top dealer accounts.
7. **Quality Audit**: Flagged issues and resolution status.
8. **Detailed Transactions**: Complete transactional record with Excel formulas.

---

## 9. Complete URL Routing & View Reference

| URL Pattern | View Name | Module / View Function | Description |
| :--- | :--- | :--- | :--- |
| `/` | `analytics:dashboard` | `apps.analytics.views.dashboard_view` | Executive MIS Dashboard with KPIs and charts. |
| `/pnl/` | `analytics:pnl` | `apps.analytics.views.pnl_dashboard_view` | Profit & Loss Statement & Waterfall Suite. |
| `/pnl/export/` | `analytics:export_pnl` | `apps.analytics.views.export_pnl_excel` | Dedicated P&L multi-sheet Excel report. |
| `/rm/` | `analytics:rm` | `apps.analytics.views.rm_analytics_view` | Relationship Manager analytics & rankings. |
| `/monthly/` | `analytics:monthly` | `apps.analytics.views.monthly_analytics_view` | Monthly billing trajectories & MoM growth. |
| `/story/` | `analytics:story` | `apps.analytics.views.story_analytics_view` | STORY margin analysis & outlier detection. |
| `/reconcile/` | `analytics:reconcile` | `apps.analytics.views.payment_analytics_view` | Payment reconciliation & variance report. |
| `/category/` | `analytics:category` | `apps.analytics.views.category_analytics_view` | Experience category mix & grouped analysis. |
| `/spoc/` | `analytics:spoc` | `apps.analytics.views.spoc_analytics_view` | Payment SPOC workload & balancing. |
| `/dealers/` | `analytics:dealers` | `apps.analytics.views.dealer_analytics_view` | Dealer & firm performance rankings. |
| `/transactions/`| `analytics:transactions`| `apps.analytics.views.transaction_explorer_view`| Server-side paginated transaction ledger. |
| `/export/` | `analytics:export_centre`| `apps.analytics.views.export_centre_view` | Centralized reporting export hub. |
| `/export/download/`| `analytics:download_excel`| `apps.analytics.views.download_complete_mis_excel`| 8-Tab consolidated MIS workbook download. |
| `/imports/upload/`| `imports:upload` | `apps.imports.views.upload_file_view` | Excel file upload & worksheet discovery. |
| `/imports/<id>/mapping/`| `imports:mapping` | `apps.imports.views.column_mapping_view` | 2-Pass column mapping & confirmation. |
| `/imports/<id>/reconcile/`| `imports:reconcile`| `apps.imports.views.reconcile_batch_view` | Zero-variance proof & verification. |
| `/imports/history/`| `imports:history` | `apps.imports.views.import_history_view` | Ingestion batch history & audit logs. |
| `/quality/` | `quality:dashboard` | `apps.quality.views.quality_dashboard_view` | Data quality issues & exception sign-off. |
| `/audit/` | `core:audit_trail` | `apps.core.views.audit_trail_view` | Immutable system audit log explorer. |

---

## 10. Local Development, Installation & Verification Guide

### 10.1 Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git
- Virtual Environment tool (`venv`)

### 10.2 Installation Steps
```bash
# 1. Clone the repository
git clone https://github.com/rishabhsamaniya/Havells_Dashboard.git
cd Havells_Dashboard

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations
python manage.py migrate

# 5. Create superuser account (if needed)
python manage.py createsuperuser

# 6. Start development server
python manage.py runserver 127.0.0.1:8000
```

### 10.3 1-Click Startup Scripts
- **macOS / Linux**: Run `./run_server.sh`
- **Windows**: Double-click `run_server.bat`

---

## 11. Production Deployment Architecture (Render & PostgreSQL)

### 11.1 Infrastructure Setup
The application is deployed on **Render** as a Python Web Service connected to a managed **Render PostgreSQL** database.

```text
[Client Web Browser]
       │ (HTTPS / TLS 1.3)
       ▼
[Render Load Balancer / Reverse Proxy]
       │
       ▼
[Gunicorn WSGI Server (2-4 Workers)]
       │
       ├──► [WhiteNoise] ──► Serves Compressed Static CSS / JS
       │
       ▼
[Django Application Layer (Python 3.14)]
       │
       ├──► [Render PostgreSQL Instance] (Primary Relational Store)
       └──► [Persistent Media Storage]   (Uploaded Excel Workbooks)
```

### 11.2 Environment Variables Configured on Render
| Variable | Description | Example / Production Value |
| :--- | :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | Active Django settings module | `havells_billing_project.settings` |
| `SECRET_KEY` | Cryptographic secret for signing | `django-insecure-production-secret-key...` |
| `DEBUG` | Debug mode switch | `False` |
| `DATABASE_URL` | PostgreSQL connection URI | `postgres://user:password@hostname:5432/dbname` |
| `ALLOWED_HOSTS` | Authorized host domains | `havells-dashboard.onrender.com,localhost` |
| `WEB_CONCURRENCY` | Gunicorn worker process count | `2` |

### 11.3 Production Build & Start Commands
- **Build Command**:
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
  ```
- **Start Command**:
  ```bash
  gunicorn havells_billing_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```

---

*Documentation maintained by Antigravity AI Engineering for Havells MIS Analytics.*
