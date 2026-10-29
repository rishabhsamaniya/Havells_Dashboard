"""
Core RBAC constants and module definitions for Havells Billing MIS.
"""

AVAILABLE_MODULES = [
    # --- Overview ---
    {
        'code': 'dashboard',
        'name': 'Executive Dashboard',
        'group': 'Overview',
        'icon': 'bi-speedometer2',
        'actions': ['view', 'export'],
        'default_route': 'analytics:dashboard',
        'description': 'Main executive summary with 12 KPIs, MoM trends, and macro visualizations.'
    },

    # --- Data Pipeline ---
    {
        'code': 'upload',
        'name': 'Upload Excel',
        'group': 'Data Pipeline',
        'icon': 'bi-cloud-arrow-up',
        'actions': ['view', 'upload'],
        'default_route': 'imports:upload',
        'description': 'Excel workbook intake, worksheet discovery, and transactional import execution.'
    },
    {
        'code': 'history',
        'name': 'Import History',
        'group': 'Data Pipeline',
        'icon': 'bi-clock-history',
        'actions': ['view', 'export', 'delete'],
        'default_route': 'imports:history',
        'description': 'Audit trail of past file batches, reconciliation variance logs, and rejected rows.'
    },

    # --- Business Analytics ---
    {
        'code': 'rm',
        'name': 'RM Performance',
        'group': 'Business Analytics',
        'icon': 'bi-people-fill',
        'actions': ['view', 'export'],
        'default_route': 'analytics:rm',
        'description': 'Sales personnel performance, target vs achievement, and average ticket size.'
    },
    {
        'code': 'monthly',
        'name': 'Monthly Billing',
        'group': 'Business Analytics',
        'icon': 'bi-calendar3',
        'actions': ['view', 'export'],
        'default_route': 'analytics:monthly',
        'description': 'Chronological monthly billing progressions, MoM momentum rates, and heatmaps.'
    },
    {
        'code': 'story',
        'name': 'STORY Analysis',
        'group': 'Business Analytics',
        'icon': 'bi-pie-chart-fill',
        'actions': ['view', 'export'],
        'default_route': 'analytics:story',
        'description': 'STORY margin distribution, yield analysis, positive vs negative exceptions.'
    },
    {
        'code': 'payment',
        'name': 'Payment Reconcile',
        'group': 'Business Analytics',
        'icon': 'bi-cash-stack',
        'actions': ['view', 'export'],
        'default_route': 'analytics:payment',
        'description': 'Invoiced vs realized payment audit, outstanding dues, and dealer balances.'
    },
    {
        'code': 'category',
        'name': 'Categories',
        'group': 'Business Analytics',
        'icon': 'bi-tags-fill',
        'actions': ['view', 'export'],
        'default_route': 'analytics:category',
        'description': 'Experience category share, grouped category mix (<9% into Others), and billing margins.'
    },
    {
        'code': 'spoc',
        'name': 'Payment SPOC',
        'group': 'Business Analytics',
        'icon': 'bi-person-check-fill',
        'actions': ['view', 'export'],
        'default_route': 'analytics:spoc',
        'description': 'Payment coordinator workload distribution and realization tracking.'
    },
    {
        'code': 'dealers',
        'name': 'Dealers & Firms',
        'group': 'Business Analytics',
        'icon': 'bi-building',
        'actions': ['view', 'export'],
        'default_route': 'analytics:dealers',
        'description': 'Top dealer rankings, revenue contribution, zero-margin, and negative-yield accounts.'
    },
    {
        'code': 'pnl',
        'name': 'Profit & Loss (P&L)',
        'group': 'Business Analytics',
        'icon': 'bi-graph-up-arrow',
        'actions': ['view', 'export'],
        'default_route': 'analytics:pnl',
        'description': 'Financial P&L statements, Gross Revenue vs Cost vs Net Profit waterfall bridge.'
    },

    # --- Data Quality & Reports ---
    {
        'code': 'quality',
        'name': 'Data Quality',
        'group': 'Data Quality & Reports',
        'icon': 'bi-shield-exclamation',
        'actions': ['view', 'edit', 'delete'],
        'default_route': 'quality:issues',
        'description': 'Data quality exception flags, duplicate candidates, and review workflows.'
    },
    {
        'code': 'category_mapping',
        'name': 'Category Mapping',
        'group': 'Data Quality & Reports',
        'icon': 'bi-sliders',
        'actions': ['view', 'add', 'edit', 'delete'],
        'default_route': 'quality:categories',
        'description': 'Raw category text normalization and standardized experience definitions.'
    },
    {
        'code': 'transactions',
        'name': 'Transaction Explorer',
        'group': 'Data Quality & Reports',
        'icon': 'bi-table',
        'actions': ['view', 'edit', 'delete', 'export'],
        'default_route': 'analytics:transactions',
        'description': 'Server-side paginated transaction ledger with row-level raw audit inspect modals.'
    },
    {
        'code': 'export',
        'name': 'Export & MIS Reports',
        'group': 'Data Quality & Reports',
        'icon': 'bi-file-earmark-spreadsheet',
        'actions': ['view', 'export'],
        'default_route': 'analytics:export_centre',
        'description': 'Consolidated 8-tab stylized MIS Excel workbook generator.'
    },

    # --- System & Governance ---
    {
        'code': 'audit',
        'name': 'Audit Trail',
        'group': 'System & Governance',
        'icon': 'bi-journal-text',
        'actions': ['view', 'export'],
        'default_route': 'core:audit_logs',
        'description': 'Immutable tracking of user actions, file imports, normalizations, and logins.'
    },
    {
        'code': 'settings',
        'name': 'Settings & Definitions',
        'group': 'System & Governance',
        'icon': 'bi-gear-fill',
        'actions': ['view', 'edit'],
        'default_route': 'core:settings',
        'description': 'STORY metric calculation definitions and monthly RM sales targets.'
    },
    {
        'code': 'rbac',
        'name': 'User & Role Access Control',
        'group': 'System & Governance',
        'icon': 'bi-person-lock',
        'actions': ['view', 'add', 'edit', 'delete', 'manage'],
        'default_route': 'core:rbac_users',
        'description': 'Granular permission matrix, user account management, and role templates.'
    },
]

MODULE_DICT = {m['code']: m for m in AVAILABLE_MODULES}

# Section hierarchy for organized sidebar rendering
MODULE_GROUPS = [
    'Overview',
    'Data Pipeline',
    'Business Analytics',
    'Data Quality & Reports',
    'System & Governance'
]

# Standard Role Templates
DEFAULT_ROLE_TEMPLATES = {
    'SUPER_ADMIN': {
        'name': 'Super Admin',
        'description': 'Unrestricted access to all dashboards, pipelines, settings, and user management.',
        'is_system_role': True,
        'modules': {
            m['code']: {f"can_{act}": True for act in ['view', 'add', 'edit', 'delete', 'upload', 'export', 'manage']}
            for m in AVAILABLE_MODULES
        }
    },
    'MANAGEMENT': {
        'name': 'Management',
        'description': 'Full visibility into all executive dashboards, financial P&L, reports, and export capabilities. No write/upload/admin access.',
        'is_system_role': True,
        'modules': {
            'dashboard': {'can_view': True, 'can_export': True},
            'rm': {'can_view': True, 'can_export': True},
            'monthly': {'can_view': True, 'can_export': True},
            'story': {'can_view': True, 'can_export': True},
            'payment': {'can_view': True, 'can_export': True},
            'category': {'can_view': True, 'can_export': True},
            'spoc': {'can_view': True, 'can_export': True},
            'dealers': {'can_view': True, 'can_export': True},
            'pnl': {'can_view': True, 'can_export': True},
            'transactions': {'can_view': True, 'can_export': True},
            'export': {'can_view': True, 'can_export': True},
            'audit': {'can_view': True, 'can_export': False},
        }
    },
    'MIS_EXECUTIVE': {
        'name': 'MIS Executive',
        'description': 'Operational access for uploading Excel sheets, managing imports, reviewing data quality, normalizing categories, and exporting reports.',
        'is_system_role': True,
        'modules': {
            'dashboard': {'can_view': True, 'can_export': True},
            'upload': {'can_view': True, 'can_upload': True},
            'history': {'can_view': True, 'can_export': True, 'can_delete': False},
            'rm': {'can_view': True, 'can_export': True},
            'monthly': {'can_view': True, 'can_export': True},
            'story': {'can_view': True, 'can_export': True},
            'payment': {'can_view': True, 'can_export': True},
            'category': {'can_view': True, 'can_export': True},
            'spoc': {'can_view': True, 'can_export': True},
            'dealers': {'can_view': True, 'can_export': True},
            'quality': {'can_view': True, 'can_edit': True, 'can_delete': False},
            'category_mapping': {'can_view': True, 'can_add': True, 'can_edit': True},
            'transactions': {'can_view': True, 'can_export': True},
            'export': {'can_view': True, 'can_export': True},
        }
    },
    'ANALYST': {
        'name': 'Analyst',
        'description': 'Read-only access to analytical views, business performance metrics, and data export. No upload or system configuration rights.',
        'is_system_role': True,
        'modules': {
            'dashboard': {'can_view': True, 'can_export': True},
            'rm': {'can_view': True, 'can_export': True},
            'monthly': {'can_view': True, 'can_export': True},
            'story': {'can_view': True, 'can_export': True},
            'payment': {'can_view': True, 'can_export': True},
            'category': {'can_view': True, 'can_export': True},
            'spoc': {'can_view': True, 'can_export': True},
            'dealers': {'can_view': True, 'can_export': True},
            'transactions': {'can_view': True, 'can_export': True},
            'export': {'can_view': True, 'can_export': True},
        }
    },
    'CUSTOM_USER': {
        'name': 'Custom User',
        'description': 'Flexible baseline role with no automatic business module access. Permissions are granted or denied manually by the Super Admin.',
        'is_system_role': True,
        'modules': {}
    }
}

MODULE_SUMMARY_MAP = {
    'dashboard': {
        'title': 'Executive Dashboard',
        'summary_hi': 'Total Billing Revenue, 12 Core KPIs, Monthly Growth Trends, Target vs Achievement %',
        'summary_en': 'Total Billing Revenue, 12 Core KPIs, Monthly Growth Trends, Target vs Achievement %',
        'type': 'Executive Dashboard',
        'badge_color': 'primary',
    },
    'rm': {
        'title': 'RM Performance',
        'summary_hi': 'Regional Managers (RM) ki Sales, Targets vs Achievement, Ticket Size aur Rankings',
        'summary_en': 'Regional Managers Sales, Targets vs Achievement, Ticket Size and Rankings',
        'type': 'Sales Analytics',
        'badge_color': 'info',
    },
    'monthly': {
        'title': 'Monthly Billing',
        'summary_hi': 'Month-wise Billing Trends, Month-over-Month Growth, Heatmaps aur Channel Mix',
        'summary_en': 'Month-wise Billing Trends, Month-over-Month Growth, Heatmaps and Channel Mix',
        'type': 'Billing Analytics',
        'badge_color': 'info',
    },
    'story': {
        'title': 'STORY Analysis',
        'summary_hi': 'STORY Division Margins, Product Group Yields, Positive vs Negative Margin Exceptions',
        'summary_en': 'STORY Division Margins, Product Group Yields, Positive vs Negative Margin Exceptions',
        'type': 'Margin Analytics',
        'badge_color': 'info',
    },
    'payment': {
        'title': 'Payment Reconcile',
        'summary_hi': 'Invoiced vs Realized Collections, Pending Dealer Balances aur Payment Status',
        'summary_en': 'Invoiced vs Realized Collections, Pending Dealer Balances and Payment Status',
        'type': 'Financial Audit',
        'badge_color': 'warning',
    },
    'category': {
        'title': 'Categories',
        'summary_hi': 'Product Category Revenue Share, Category Group Mix aur Category Margins',
        'summary_en': 'Product Category Revenue Share, Category Group Mix and Category Margins',
        'type': 'Category Analytics',
        'badge_color': 'info',
    },
    'spoc': {
        'title': 'Payment SPOC',
        'summary_hi': 'Payment Coordinator (SPOC) Recovery Tracking, Outstanding Balance aur Workload',
        'summary_en': 'Payment Coordinator (SPOC) Recovery Tracking, Outstanding Balance and Workload',
        'type': 'Recovery Tracking',
        'badge_color': 'warning',
    },
    'dealers': {
        'title': 'Dealers & Firms',
        'summary_hi': 'Top Dealer Billing Rankings, Dealer Contribution, Zero & Negative Margin Firms',
        'summary_en': 'Top Dealer Billing Rankings, Dealer Contribution, Zero & Negative Margin Firms',
        'type': 'Dealer Analytics',
        'badge_color': 'info',
    },
    'pnl': {
        'title': 'Profit & Loss (P&L)',
        'summary_hi': 'Financial P&L Statements, Gross Revenue vs Product Cost vs Net Profit Margins Waterfall',
        'summary_en': 'Financial P&L Statements, Gross Revenue vs Product Cost vs Net Profit Margins Waterfall',
        'type': 'Financial P&L',
        'badge_color': 'danger',
    },
    'upload': {
        'title': 'Upload Excel',
        'summary_hi': 'New Monthly Billing Excel Sheets Upload Karna aur System Me Sync Karna',
        'summary_en': 'Upload New Monthly Billing Excel Sheets and Sync to System Database',
        'type': 'Data Pipeline',
        'badge_color': 'success',
    },
    'history': {
        'title': 'Import History',
        'summary_hi': 'Pichli Upload Ki Gayi Files Ki History, Batch Logs, Row Counts aur Variances',
        'summary_en': 'Past Uploaded Files History, Batch Logs, Row Counts and Variances',
        'type': 'Audit Logs',
        'badge_color': 'secondary',
    },
    'quality': {
        'title': 'Data Quality',
        'summary_hi': 'Data Validation Flags, Missing Records, Duplicate Bills aur Review Exceptions',
        'summary_en': 'Data Validation Flags, Missing Records, Duplicate Bills and Review Exceptions',
        'type': 'Data Quality',
        'badge_color': 'warning',
    },
    'category_mapping': {
        'title': 'Category Mapping',
        'summary_hi': 'Raw Category Texts Ko Standard Havells Experience Categories Me Map Karna',
        'summary_en': 'Normalize Raw Category Texts to Standard Havells Categories',
        'type': 'Data Quality',
        'badge_color': 'secondary',
    },
    'transactions': {
        'title': 'Transaction Explorer',
        'summary_hi': 'Complete Billing Transactions Ledger, Line-by-Line Invoices aur Search/Filter',
        'summary_en': 'Complete Billing Transactions Ledger, Line-by-Line Invoices and Search/Filter',
        'type': 'Ledger Explorer',
        'badge_color': 'dark',
    },
    'export': {
        'title': 'Export & MIS Reports',
        'summary_hi': 'Stylized Multi-Tab Excel MIS Reports Download Karna (Executive, RM, Monthly, STORY)',
        'summary_en': 'Download Stylized Multi-Tab Excel MIS Reports (Executive, RM, Monthly, STORY)',
        'type': 'MIS Export Centre',
        'badge_color': 'success',
    },
    'audit': {
        'title': 'Audit Trail',
        'summary_hi': 'User Activity Logs, Login History, File Uploads, Record Edits aur Permission Changes',
        'summary_en': 'User Activity Logs, Login History, File Uploads, Record Edits and Permission Changes',
        'type': 'System Security',
        'badge_color': 'secondary',
    },
    'settings': {
        'title': 'Settings & Definitions',
        'summary_hi': 'Fiscal Year Definitions, Target Thresholds aur System Constants Config',
        'summary_en': 'Fiscal Year Definitions, Target Thresholds and System Constants Config',
        'type': 'System Settings',
        'badge_color': 'secondary',
    },
    'rbac': {
        'title': 'User & Role Access Control',
        'summary_hi': 'User Accounts Banana, Roles Assign Karna aur Access Permissions Matrix Set Karna',
        'summary_en': 'Manage User Accounts, Assign Roles and Configure Permission Matrices',
        'type': 'Security Admin',
        'badge_color': 'danger',
    },
}

