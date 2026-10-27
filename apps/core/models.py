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
