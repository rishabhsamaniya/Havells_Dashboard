from django.contrib import admin
from apps.quality.models import CategoryMapping, DataQualityIssue

@admin.register(CategoryMapping)
class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('raw_category', 'standardized_category', 'is_reviewed', 'updated_at')
    list_filter = ('is_reviewed',)
    search_fields = ('raw_category', 'standardized_category')

@admin.register(DataQualityIssue)
class DataQualityIssueAdmin(admin.ModelAdmin):
    list_display = ('id', 'import_batch', 'field_name', 'issue_type', 'severity', 'review_status', 'created_at')
    list_filter = ('severity', 'issue_type', 'review_status')
    search_fields = ('description', 'field_name')
