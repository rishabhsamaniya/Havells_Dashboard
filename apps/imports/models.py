import hashlib
from django.db import models
from django.contrib.auth.models import User

class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Preview'),
        ('PROCESSING', 'Processing Import'),
        ('COMPLETED', 'Completed Successfully'),
        ('FAILED', 'Import Failed / Rolled Back'),
        ('REPLACED', 'Replaced by Newer Import'),
    ]

    file_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, db_index=True, help_text="SHA-256 hash of file content to detect duplicates")
    uploaded_file = models.FileField(upload_to='uploads/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='import_batches')
    sheet_name = models.CharField(max_length=100)
    detected_sheets = models.JSONField(default=list)
    reporting_period = models.CharField(max_length=100, blank=True)
    
    # Row counts
    total_source_rows = models.IntegerField(default=0)
    successful_records = models.IntegerField(default=0)
    rejected_records = models.IntegerField(default=0)
    duplicate_records = models.IntegerField(default=0)
    
    # Financial reconciliation totals recorded at import time
    total_billing_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_paid_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_story_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    column_mapping = models.JSONField(default=dict, help_text="Mapping from Excel headers to canonical model fields")
    error_log = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Import Batch'
        verbose_name_plural = 'Import Batches'

    def __str__(self):
        return f"{self.file_name} [{self.sheet_name}] - {self.status} ({self.uploaded_at:%Y-%m-%d %H:%M})"

    @staticmethod
    def calculate_file_hash(file_obj):
        hasher = hashlib.sha256()
        for chunk in file_obj.chunks():
            hasher.update(chunk)
        file_obj.seek(0)
        return hasher.hexdigest()


class ColumnMappingTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    mapping_rules = models.JSONField(default=dict, help_text="Canonical field -> list of candidate Excel header names")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Column Mapping Template'
        verbose_name_plural = 'Column Mapping Templates'

    def __str__(self):
        return self.name


class RejectedRecord(models.Model):
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='rejected_rows')
    source_row_number = models.IntegerField()
    raw_data = models.JSONField(default=dict)
    rejection_reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['source_row_number']
        verbose_name = 'Rejected Record'
        verbose_name_plural = 'Rejected Records'

    def __str__(self):
        return f"Batch #{self.import_batch_id} Row #{self.source_row_number}: {self.rejection_reason[:50]}"
