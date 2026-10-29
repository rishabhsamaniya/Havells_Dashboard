from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from apps.core.models import (
    AuditLog, MetricDefinition, MonthlyRMTarget,
    Role, UserProfile, ModulePermission
)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile & RBAC Role'
    fk_name = 'user'
    extra = 0

class ModulePermissionInline(admin.TabularInline):
    model = ModulePermission
    extra = 0
    fields = ('module_code', 'can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage')

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, ModulePermissionInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'profile__role')

    def get_role(self, obj):
        return obj.profile.role.name if hasattr(obj, 'profile') and obj.profile.role else ('Super Admin' if obj.is_superuser else '-')
    get_role.short_description = 'RBAC Role'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_system_role', 'user_count')
    list_filter = ('is_system_role',)
    search_fields = ('name', 'code', 'description')
    inlines = [ModulePermissionInline]

    def user_count(self, obj):
        return obj.userprofile_set.count()
    user_count.short_description = 'Assigned Users'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'phone', 'use_custom_permissions')
    list_filter = ('role', 'use_custom_permissions')
    search_fields = ('user__username', 'department', 'phone')

@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ('module_code', 'role', 'user', 'can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage')
    list_filter = ('module_code', 'role', 'can_view', 'can_upload', 'can_export')
    search_fields = ('module_code', 'user__username', 'role__name')

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
