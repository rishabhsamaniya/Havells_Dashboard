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
    }
}
