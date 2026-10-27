from django.db import models
from apps.imports.models import ImportBatch

class BillingTransaction(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Fully Paid'),
        ('PARTIAL', 'Partially Paid'),
        ('UNPAID', 'Unpaid / Pending'),
        ('OVERPAID', 'Overpaid / Credit Balance'),
    ]

    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='transactions')
    source_row_number = models.IntegerField(help_text="1-based row number from original Excel file for audit reconciliation")
    
    # Core Dimension Fields
    month_label = models.CharField(max_length=50, db_index=True, help_text="e.g. Apr`26")
    transaction_date = models.DateField(null=True, blank=True, db_index=True)
    financial_year = models.CharField(max_length=20, default='2026-27', db_index=True)
    
    rm = models.CharField(max_length=100, db_index=True, verbose_name="Relationship Manager")
    dealer_code = models.CharField(max_length=100, db_index=True)
    firm_name = models.CharField(max_length=255, db_index=True)
    dealer_name = models.CharField(max_length=255, blank=True)
    
    raw_category = models.CharField(max_length=150, help_text="Original category text exactly as in Excel")
    standardized_category = models.CharField(max_length=150, db_index=True, help_text="Standardized category after normalization")
    payment_spoc = models.CharField(max_length=100, db_index=True, verbose_name="Payment SPOC")
    
    # Financial Measures (Explicit DecimalFields to eliminate binary floating point imprecision)
    billing_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_index=True)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_index=True)
    story_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_index=True)
    calculated_difference = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Billing Amount - Amount Paid")
    
    # Additional Context
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='PAID', db_index=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    city_state = models.CharField(max_length=150, blank=True)
    venue_name = models.CharField(max_length=255, blank=True, help_text="Hotel/Salon/Restaurant/Concert name if present")
    
    # Auditable complete raw row
    raw_source_data = models.JSONField(default=dict, help_text="Original source cell values for audit purposes")
    
    # Quality flags
    is_flagged = models.BooleanField(default=False, db_index=True)
    flag_reason = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['month_label', 'rm']),
            models.Index(fields=['rm', 'standardized_category']),
            models.Index(fields=['dealer_code', 'month_label']),
            models.Index(fields=['payment_spoc', 'month_label']),
            models.Index(fields=['import_batch', 'source_row_number']),
        ]
        verbose_name = 'Billing Transaction'
        verbose_name_plural = 'Billing Transactions'

    def __str__(self):
        return f"{self.month_label} | {self.dealer_code} - {self.firm_name} | ₹{self.billing_amount:,.2f}"

    def save(self, *args, **kwargs):
        # Always maintain calculated difference without hardcoding business assumption
        self.calculated_difference = self.billing_amount - self.amount_paid
        
        # Payment status categorization based on mathematical difference
        if self.amount_paid == 0 and self.billing_amount > 0:
            self.payment_status = 'UNPAID'
        elif self.amount_paid < self.billing_amount:
            self.payment_status = 'PARTIAL'
        elif self.amount_paid > self.billing_amount:
            self.payment_status = 'OVERPAID'
        else:
            self.payment_status = 'PAID'
            
        super().save(*args, **kwargs)
