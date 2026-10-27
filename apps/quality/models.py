from django.db import models
from django.contrib.auth.models import User
from apps.imports.models import ImportBatch
from apps.analytics.models import BillingTransaction

class CategoryMapping(models.Model):
    raw_category = models.CharField(max_length=150, unique=True, db_index=True)
    standardized_category = models.CharField(max_length=150, db_index=True)
    is_reviewed = models.BooleanField(default=False, help_text="True if confirmed by administrator")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['standardized_category', 'raw_category']
        verbose_name = 'Category Normalization Mapping'
        verbose_name_plural = 'Category Normalization Mappings'

    def __str__(self):
        return f"{self.raw_category} -> {self.standardized_category}"


class DataQualityIssue(models.Model):
    ISSUE_TYPES = [
        ('VALIDATION_ERROR', 'Validation Error'),
        ('POTENTIAL_DUPLICATE', 'Potential Duplicate Record'),
        ('BUSINESS_EXCEPTION', 'Business Exception'),
        ('WARNING', 'Warning / Anomaly'),
    ]

    SEVERITY_LEVELS = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INFO', 'Informational'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('REVIEWED', 'Reviewed & Accepted'),
        ('RESOLVED', 'Resolved'),
        ('DISMISSED', 'Dismissed / False Positive'),
    ]

    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='quality_issues')
    transaction = models.ForeignKey(BillingTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='quality_issues')
    source_row_number = models.IntegerField(null=True, blank=True)
    field_name = models.CharField(max_length=100)
    original_value = models.TextField(blank=True, null=True)
    
    issue_type = models.CharField(max_length=50, choices=ISSUE_TYPES, default='WARNING', db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='MEDIUM', db_index=True)
    description = models.TextField()
    
    review_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', 'source_row_number']
        verbose_name = 'Data Quality Issue'
        verbose_name_plural = 'Data Quality Issues'

    def __str__(self):
        return f"[{self.severity}] {self.issue_type} - {self.field_name}: {self.description[:40]}"
