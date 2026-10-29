from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import render, redirect, get_object_or_404

from apps.core.models import (
    AuditLog, MetricDefinition, MonthlyRMTarget,
    Role, UserProfile, AppModule, RolePermission, UserPermissionOverride
)
from apps.core.permissions import get_user_effective_permissions, clear_user_permission_cache

# ==========================================
# INLINES
# ==========================================

class UserPermissionOverrideInline(admin.TabularInline):
    model = UserPermissionOverride
    extra = 0
    fields = ('module', 'view_override', 'add_override', 'edit_override', 'delete_override', 'upload_override', 'export_override', 'manage_override')
    autocomplete_fields = ('module',)


# ==========================================
# APP MODULE ADMIN
# ==========================================

@admin.register(AppModule)
class AppModuleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'group', 'order', 'icon', 'url_name', 'is_active')
    list_display_links = ('code', 'name')
    list_editable = ('order', 'is_active')
    list_filter = ('group', 'is_active')
    search_fields = ('name', 'code', 'group')
    ordering = ('order', 'name')


# ==========================================
# ROLE ADMIN WITH DYNAMIC MATRIX
# ==========================================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_system_role', 'user_count', 'permissions_matrix_link')
    list_filter = ('is_system_role',)
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('matrix_shortcut', 'user_count')
    fields = ('matrix_shortcut', 'name', 'code', 'description', 'is_system_role', 'user_count')

    def user_count(self, obj):
        count = obj.users.count()
        return format_html('<strong>{}</strong> user(s)', count)
    user_count.short_description = 'Assigned Users'

    def permissions_matrix_link(self, obj):
        url = reverse('admin:core_role_matrix', args=[obj.id])
        return format_html(
            '<a class="button" style="background:#28a745; color:#fff; font-weight:bold; padding:4px 12px; border-radius:4px; text-decoration:none;" href="{}">&#x2714; Configure Matrix</a>', 
            url
        )
    permissions_matrix_link.short_description = 'Permissions Matrix'

    def matrix_shortcut(self, obj):
        if obj and obj.pk:
            url = reverse('admin:core_role_matrix', args=[obj.id])
            return format_html(
                '<div style="background:#eafaf1; border:2px solid #28a745; border-radius:6px; padding:12px 16px; margin-bottom:12px; max-width:700px;">'
                '<div style="font-size:1.05rem; font-weight:bold; color:#155724; margin-bottom:4px;">Configure Default Permissions Matrix for {}</div>'
                '<div style="color:#333; font-size:0.85rem; margin-bottom:10px;">Click below to open the dynamic module permission matrix. All users assigned this role inherit these permissions unless individually overridden.</div>'
                '<a class="button" style="background:#28a745; color:#fff; font-weight:bold; padding:8px 20px; font-size:0.95rem; text-decoration:none; border-radius:4px; display:inline-block;" href="{}">&#x2699; Open Role Permissions Matrix</a>'
                '</div>',
                obj.name, url
            )
        return "Save role first to configure permissions matrix."
    matrix_shortcut.short_description = "Role Permissions Matrix"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:role_id>/matrix/', self.admin_site.admin_view(self.role_matrix_view), name='core_role_matrix'),
        ]
        return custom_urls + urls

    def role_matrix_view(self, request, role_id):
        role = get_object_or_404(Role, id=role_id)
        modules = list(AppModule.objects.filter(is_active=True).order_by('order'))
        action_names = ['can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage']

        if request.method == 'POST':
            for mod in modules:
                allowed_actions = mod.supported_actions or ['view']
                perm_kwargs = {}
                for act in action_names:
                    short_act = act.replace('can_', '')
                    if short_act in allowed_actions:
                        perm_kwargs[act] = (request.POST.get(f"perm_{mod.code}_{act}") == 'on')
                    else:
                        perm_kwargs[act] = False

                RolePermission.objects.update_or_create(
                    role=role,
                    module=mod,
                    defaults=perm_kwargs
                )

            AuditLog.objects.create(
                action='ROLE_UPDATE',
                model_name='Role',
                object_id=str(role.id),
                user=request.user,
                details={'role_code': role.code, 'role_name': role.name}
            )
            clear_user_permission_cache(request)
            messages.success(request, f"Role default permissions for '{role.name}' were saved successfully.")
            return redirect(reverse('admin:core_role_matrix', args=[role.id]))

        # Prepare matrix data for GET
        role_perms_map = {
            rp.module.code: rp for rp in RolePermission.objects.filter(role=role).select_related('module')
        }

        matrix_rows = []
        for mod in modules:
            allowed = mod.supported_actions or ['view']
            rp = role_perms_map.get(mod.code)

            row_actions = {}
            for act in action_names:
                short_act = act.replace('can_', '')
                is_allowed = short_act in allowed
                is_checked = getattr(rp, act, False) if rp else (role.code == 'SUPER_ADMIN')

                row_actions[act] = {
                    'is_allowed': is_allowed,
                    'is_checked': is_checked,
                    'field_name': f"perm_{mod.code}_{act}",
                }

            matrix_rows.append({
                'code': mod.code,
                'name': mod.name,
                'group': mod.group,
                'icon': mod.icon,
                'actions': row_actions,
            })

        context = {
            **self.admin_site.each_context(request),
            'role': role,
            'matrix_rows': matrix_rows,
            'title': f"Permissions Matrix: {role.name}",
        }
        return render(request, 'admin/core/role_matrix.html', context)


# ==========================================
# CUSTOM USER FORMS WITH DIRECT ROLE SELECT
# ==========================================

class CustomUserCreationForm(UserCreationForm):
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=True,
        empty_label="-- Select RBAC Role --",
        help_text="Select one of the 5 predefined roles. Default permissions will automatically apply upon creation.",
    )
    department = forms.CharField(required=False, max_length=100, help_text="Optional department name")
    phone = forms.CharField(required=False, max_length=20, help_text="Optional contact number")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'role', 'department', 'phone')

    def save(self, commit=True):
        user = super().save(commit=commit)
        role = self.cleaned_data.get('role')
        dept = self.cleaned_data.get('department', '')
        phone = self.cleaned_data.get('phone', '')

        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.department = dept
            profile.phone = phone
            profile.save()

            if role and role.code == 'SUPER_ADMIN':
                user.is_superuser = True
                user.is_staff = True
                user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        empty_label="-- Select RBAC Role --",
        help_text="Select one of the 5 predefined roles. User inherits role default permissions unless individually overridden.",
    )
    department = forms.CharField(required=False, max_length=100)
    phone = forms.CharField(required=False, max_length=20)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, 'profile', None)
            if profile:
                self.fields['role'].initial = profile.role
                self.fields['department'].initial = profile.department
                self.fields['phone'].initial = profile.phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        role = self.cleaned_data.get('role')
        dept = self.cleaned_data.get('department', '')
        phone = self.cleaned_data.get('phone', '')

        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.department = dept
            profile.phone = phone
            profile.save()

            if role and role.code == 'SUPER_ADMIN':
                user.is_superuser = True
                user.is_staff = True
                user.save()
        return user


# ==========================================
# CUSTOM USER ADMIN WITH DYNAMIC OVERRIDES
# ==========================================

class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'is_superuser', 'permissions_matrix_link')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'profile__role')

    fieldsets = (
        ("Account Credentials", {"fields": ("username", "password")}),
        ("RBAC Role & Profile Assignment", {"fields": ("role", "overrides_matrix_shortcut", "department", "phone")}),
        ("Personal Information", {"fields": ("first_name", "last_name", "email")}),
        ("Account Status & System Flags", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important Dates", {"fields": ("last_login", "date_joined"), "classes": ("collapse",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "role", "password1", "password2", "department", "phone"),
        }),
    )

    readonly_fields = ('overrides_matrix_shortcut',)

    def get_role(self, obj):
        role_name = obj.profile.role.name if hasattr(obj, 'profile') and obj.profile.role else ('Super Admin' if obj.is_superuser else 'No Role')
        color = '#205067'
        if role_name == 'Super Admin':
            color = '#b7791f'
        elif role_name == 'Management':
            color = '#2b6cb0'
        elif role_name == 'MIS Executive':
            color = '#2f855a'
        elif role_name == 'Analyst':
            color = '#4c51bf'
        return format_html('<span style="background:{}; color:#fff; font-weight:600; padding:3px 8px; border-radius:4px; font-size:0.8rem;">{}</span>', color, role_name)
    get_role.short_description = 'RBAC Role'

    def permissions_matrix_link(self, obj):
        url = reverse('admin:core_user_matrix', args=[obj.id])
        return format_html(
            '<a class="button" style="background:#205067; color:#fff; font-weight:600; padding:4px 10px; border-radius:4px; text-decoration:none;" href="{}">&#x2699; Overrides Matrix</a>', 
            url
        )
    permissions_matrix_link.short_description = 'Individual Overrides'

    def overrides_matrix_shortcut(self, obj):
        if obj and obj.pk:
            url = reverse('admin:core_user_matrix', args=[obj.id])
            role_name = obj.profile.role.name if hasattr(obj, 'profile') and obj.profile.role else 'No Role'
            return format_html(
                '<div style="background:#eef6f9; border:2px solid #205067; border-radius:6px; padding:12px 16px; margin:4px 0 10px 0; max-width:700px;">'
                '<div style="font-size:1rem; font-weight:bold; color:#205067; margin-bottom:4px;">Current Role: {}</div>'
                '<div style="color:#444; font-size:0.85rem; margin-bottom:10px;">Want to grant additional permissions or explicitly deny inherited permissions for this specific user?</div>'
                '<a class="button" style="background:#205067; color:#fff; font-weight:bold; padding:8px 18px; font-size:0.95rem; text-decoration:none; border-radius:4px; display:inline-block;" href="{}">&#x2699; Open Individual Overrides Matrix (ALLOW / DENY)</a>'
                '</div>',
                role_name, url
            )
        return "Save user first to configure individual permission overrides."
    overrides_matrix_shortcut.short_description = "Dynamic Overrides Matrix"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:user_id>/matrix/', self.admin_site.admin_view(self.user_matrix_view), name='core_user_matrix'),
        ]
        return custom_urls + urls

    def user_matrix_view(self, request, user_id):
        target_user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        all_roles = Role.objects.all().order_by('name')
        modules = list(AppModule.objects.filter(is_active=True).order_by('order'))
        action_names = ['can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage']

        if request.method == 'POST':
            action_type = request.POST.get('action_type', 'save_overrides')

            # Handle Reset to Role Defaults
            if action_type == 'reset_defaults':
                UserPermissionOverride.objects.filter(user=target_user).delete()
                AuditLog.objects.create(
                    action='PERMISSION_UPDATE',
                    model_name='UserPermissionOverride',
                    object_id=str(target_user.id),
                    user=request.user,
                    details={'action': 'RESET_TO_ROLE_DEFAULTS', 'target_user': target_user.username}
                )
                clear_user_permission_cache(request)
                messages.success(request, f"All individual overrides for '{target_user.username}' were reset to role defaults.")
                return redirect(reverse('admin:core_user_matrix', args=[target_user.id]))

            # Handle Role change if submitted
            role_id = request.POST.get('assigned_role_id')
            if role_id:
                new_role = Role.objects.filter(id=role_id).first()
                if new_role and profile.role != new_role:
                    profile.role = new_role
                    profile.save()
                    if new_role.code == 'SUPER_ADMIN':
                        target_user.is_superuser = True
                        target_user.is_staff = True
                        target_user.save()

            # Save individual overrides
            for mod in modules:
                allowed_actions = mod.supported_actions or ['view']
                override_payload = {}
                has_non_inherit = False

                for act in action_names:
                    short_act = act.replace('can_', '')
                    field_name = f"override_{mod.code}_{act}"
                    override_val = request.POST.get(field_name, 'INHERIT')

                    if short_act in allowed_actions:
                        override_payload[f"{short_act}_override"] = override_val
                        if override_val != 'INHERIT':
                            has_non_inherit = True
                    else:
                        override_payload[f"{short_act}_override"] = 'INHERIT'

                if has_non_inherit:
                    UserPermissionOverride.objects.update_or_create(
                        user=target_user,
                        module=mod,
                        defaults=override_payload
                    )
                else:
                    UserPermissionOverride.objects.filter(user=target_user, module=mod).delete()

            AuditLog.objects.create(
                action='PERMISSION_UPDATE',
                model_name='UserPermissionOverride',
                object_id=str(target_user.id),
                user=request.user,
                details={'action': 'SAVE_OVERRIDES', 'target_user': target_user.username, 'role': profile.role.name if profile.role else None}
            )
            clear_user_permission_cache(request)
            messages.success(request, f"Individual permission overrides for '{target_user.username}' were saved successfully.")
            return redirect(reverse('admin:core_user_matrix', args=[target_user.id]))

        # GET: Prepare matrix data
        role_perms_map = {}
        if profile.role:
            role_perms_map = {
                rp.module.code: rp for rp in RolePermission.objects.filter(role=profile.role).select_related('module')
            }

        user_overrides_map = {
            ov.module.code: ov for ov in UserPermissionOverride.objects.filter(user=target_user).select_related('module')
        }

        effective_map = get_user_effective_permissions(target_user)

        matrix_rows = []
        for mod in modules:
            allowed = mod.supported_actions or ['view']
            rp = role_perms_map.get(mod.code)
            ov = user_overrides_map.get(mod.code)
            eff_mod = effective_map.get(mod.code, {})

            row_actions = {}
            for act in action_names:
                short_act = act.replace('can_', '')
                is_allowed = short_act in allowed

                # Role default
                role_default_val = getattr(rp, act, False) if rp else (profile.role and profile.role.code == 'SUPER_ADMIN')

                # User override
                override_val = getattr(ov, f"{short_act}_override", 'INHERIT') if ov else 'INHERIT'

                # Effective final status
                effective_val = eff_mod.get(act, False)

                row_actions[act] = {
                    'is_allowed': is_allowed,
                    'role_default': role_default_val,
                    'override_val': override_val,
                    'effective_val': effective_val,
                    'field_name': f"override_{mod.code}_{act}",
                }

            matrix_rows.append({
                'code': mod.code,
                'name': mod.name,
                'group': mod.group,
                'icon': mod.icon,
                'actions': row_actions,
            })

        context = {
            **self.admin_site.each_context(request),
            'target_user': target_user,
            'profile': profile,
            'all_roles': all_roles,
            'user_role_name': profile.role.name if profile.role else ('Super Admin' if target_user.is_superuser else 'No Role'),
            'matrix_rows': matrix_rows,
            'title': f"Permission Overrides: {target_user.username}",
        }
        return render(request, 'admin/core/user_matrix.html', context)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ==========================================
# OTHER CORE ADMIN REGISTRATIONS
# ==========================================

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
