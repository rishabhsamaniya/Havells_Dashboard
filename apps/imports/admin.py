from django.contrib import admin
from apps.imports.models import ImportBatch, ColumnMappingTemplate, RejectedRecord

@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'sheet_name', 'uploaded_at', 'successful_records', 'rejected_records', 'total_billing_amount', 'status', 'is_active')
    list_filter = ('status', 'is_active', 'uploaded_at')

@admin.register(ColumnMappingTemplate)
class ColumnMappingTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'updated_at')

@admin.register(RejectedRecord)
class RejectedRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'import_batch', 'source_row_number', 'rejection_reason', 'created_at')
    list_filter = ('import_batch',)
