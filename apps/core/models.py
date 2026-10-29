from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('IMPORT', 'Data Import'),
        ('REPLACE', 'Data Replacement'),
        ('EDIT', 'Record Edit'),
        ('NORMALIZE', 'Category Normalization'),
        ('METRIC_CHANGE', 'Metric Definition Change'),
        ('REVIEW', 'Quality Issue Review'),
        ('EXPORT', 'Report Export'),
        ('TARGET_UPDATE', 'RM Target Update'),
        ('LOGIN', 'User Login'),
        ('USER_CREATE', 'User Account Created'),
        ('USER_EDIT', 'User Account Updated'),
        ('USER_STATUS', 'User Status Toggled'),
        ('PERMISSION_UPDATE', 'Permissions Updated'),
        ('ROLE_CREATE', 'Role Created'),
        ('ROLE_UPDATE', 'Role Updated'),
        ('ROLE_DELETE', 'Role Deleted'),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} by {user_str}"


class Role(models.Model):
    """
    Role defining a functional template of module-level permissions.
    Predefined system roles: SUPER_ADMIN, MANAGEMENT, MIS_EXECUTIVE, ANALYST.
    Administrators can create unlimited custom roles.
    """
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False, help_text="System default roles cannot be deleted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    Extended profile for Django User storing role assignment and custom permission overrides.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    use_custom_permissions = models.BooleanField(
        default=False,
        help_text="When True, the user's specific ModulePermission records override their assigned Role template"
    )
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        role_name = self.role.name if self.role else ("Super Admin" if self.user.is_superuser else "No Role")
        return f"{self.user.username} ({role_name})"


class AppModule(models.Model):
    """
    Centralized, database-backed registry of all sidebar application modules.
    """
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='bi-app')
    url_name = models.CharField(max_length=100, blank=True)
    supported_actions = models.JSONField(default=list, help_text="List of applicable actions e.g. ['view', 'upload', 'export']")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Application Module'
        verbose_name_plural = 'Application Modules'

    def __str__(self):
        return f"{self.name} ({self.group})"


class RolePermission(models.Model):
    """
    Role-level default permissions configured per module.
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    module = models.ForeignKey(AppModule, on_delete=models.CASCADE, related_name='role_permissions')

    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_upload = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    can_manage = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'module')
        verbose_name = 'Role Default Permission'
        verbose_name_plural = 'Role Default Permissions'

    def __str__(self):
        return f"{self.role.name} - {self.module.name}"


class UserPermissionOverride(models.Model):
    """
    Explicit user-level overrides over role defaults.
    Each action can be:
      - INHERIT: Follow role default
      - ALLOW: Explicitly grant permission
      - DENY: Explicitly block permission
    """
    OVERRIDE_CHOICES = [
        ('INHERIT', 'Inherit Role Default'),
        ('ALLOW', 'Explicitly Allow (Grant)'),
        ('DENY', 'Explicitly Deny (Block)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_overrides')
    module = models.ForeignKey(AppModule, on_delete=models.CASCADE, related_name='user_overrides')

    view_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')
    add_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')
    edit_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')
    delete_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')
    upload_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')
    export_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')
    manage_override = models.CharField(max_length=10, choices=OVERRIDE_CHOICES, default='INHERIT')

    class Meta:
        unique_together = ('user', 'module')
        verbose_name = 'User Permission Override'
        verbose_name_plural = 'User Permission Overrides'

    def __str__(self):
        return f"Override: {self.user.username} - {self.module.name}"


class ModulePermission(models.Model):
    """
    Legacy granular permission record maintained for backward compatibility.
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='custom_permissions')
    module_code = models.CharField(max_length=50, db_index=True)
    
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_upload = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    can_manage = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Module Permission'
        verbose_name_plural = 'Module Permissions'
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'module_code'],
                name='unique_role_module_perm',
                condition=models.Q(role__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['user', 'module_code'],
                name='unique_user_module_perm',
                condition=models.Q(user__isnull=False)
            ),
        ]

    def __str__(self):
        owner = self.role.name if self.role else (self.user.username if self.user else "Unassigned")
        return f"{owner} - {self.module_code} [View:{self.can_view}, Edit:{self.can_edit}, Upload:{self.can_upload}, Export:{self.can_export}]"



class MetricDefinition(models.Model):
    FORMULA_TYPES = [
        ('SOURCE_COLUMN', 'Use Source Column As-Is (Default)'),
        ('BILLING_MINUS_PAID', 'Formula: Billing Amount - Amount Paid'),
        ('CUSTOM', 'Custom Formula Expression'),
    ]

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    formula_type = models.CharField(max_length=50, choices=FORMULA_TYPES, default='SOURCE_COLUMN')
    formula_expression = models.CharField(max_length=255, blank=True, help_text="Configured mathematical formula when type is CUSTOM")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Metric Definition'
        verbose_name_plural = 'Metric Definitions'

    def __str__(self):
        return f"{self.name} ({self.get_formula_type_display()})"


class MonthlyRMTarget(models.Model):
    rm_name = models.CharField(max_length=100, db_index=True)
    month_label = models.CharField(max_length=50, db_index=True, help_text="e.g. Apr`26 or Jun`26")
    target_billing = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    target_story = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    target_deals = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('rm_name', 'month_label')
        ordering = ['month_label', 'rm_name']
        verbose_name = 'Monthly RM Target'
        verbose_name_plural = 'Monthly RM Targets'

    def __str__(self):
        return f"{self.rm_name} - {self.month_label} (Target: ₹{self.target_billing:,.2f})"
