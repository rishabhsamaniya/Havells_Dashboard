from django.contrib import admin
from apps.core.models import AuditLog, MetricDefinition, MonthlyRMTarget

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'model_name', 'object_id')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('action', 'model_name', 'object_id', 'user', 'timestamp', 'ip_address', 'details')

@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'formula_type', 'is_active', 'updated_at')

@admin.register(MonthlyRMTarget)
class MonthlyRMTargetAdmin(admin.ModelAdmin):
    list_display = ('rm_name', 'month_label', 'target_billing', 'target_story', 'updated_at')
    list_filter = ('month_label', 'rm_name')
