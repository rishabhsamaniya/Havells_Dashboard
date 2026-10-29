from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.text import slugify

from apps.core.models import (
    Role, UserProfile, ModulePermission, AuditLog, MetricDefinition, MonthlyRMTarget,
    AppModule, RolePermission, UserPermissionOverride
)
from apps.core.constants import AVAILABLE_MODULES, MODULE_DICT, MODULE_GROUPS, DEFAULT_ROLE_TEMPLATES
from apps.core.permissions import (
    permission_required, has_module_perm, get_user_effective_permissions, clear_user_permission_cache
)
from apps.analytics.models import BillingTransaction

User = get_user_model()

def user_login(request):
    if request.user.is_authenticated:
        return redirect('analytics:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated. Please contact the Super Admin.')
                return render(request, 'core/login.html')
            login(request, user)
            AuditLog.objects.create(
                action='LOGIN',
                model_name='User',
                object_id=str(user.id),
                user=user,
                details={'username': username}
            )
            return redirect('analytics:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')

def user_logout(request):
    logout(request)
    return redirect('core:login')

@login_required
@permission_required('audit', 'can_view')
def audit_logs(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:200]
    return render(request, 'core/audit_logs.html', {'logs': logs})

@login_required
@permission_required('settings', 'can_view')
def settings_view(request):
    metric = MetricDefinition.objects.filter(code='STORY_DEFINITION').first()
    if not metric:
        metric = MetricDefinition.objects.create(
            code='STORY_DEFINITION',
            name='STORY Margin Definition',
            description='Preserves the dedicated STORY column from the source Excel file as the source of truth.',
            formula_type='SOURCE_COLUMN',
            notes='Do not assume STORY is Billing minus Paid unless confirmed by admin.'
        )

    targets = MonthlyRMTarget.objects.all().order_by('month_label', 'rm_name')
    rms = list(BillingTransaction.objects.filter(import_batch__is_active=True).values_list('rm', flat=True).distinct().order_by('rm'))
    months = list(BillingTransaction.objects.filter(import_batch__is_active=True).values_list('month_label', flat=True).distinct().order_by('month_label'))

    if request.method == 'POST':
        if not has_module_perm(request.user, 'settings', 'can_edit', request):
            return render(request, 'core/403.html', {
                'module_code': 'settings',
                'module_name': 'Settings & Definitions',
                'required_action': 'can_edit',
                'error_message': 'You do not have permission to modify settings or business metrics.'
            }, status=403)

        action = request.POST.get('action')
        if action == 'update_story_metric':
            metric.formula_type = request.POST.get('formula_type', 'SOURCE_COLUMN')
            metric.formula_expression = request.POST.get('formula_expression', '')
            metric.notes = request.POST.get('notes', '')
            metric.save()
            AuditLog.objects.create(
                action='METRIC_CHANGE',
                model_name='MetricDefinition',
                object_id=str(metric.id),
                user=request.user,
                details={'formula_type': metric.formula_type}
            )
            messages.success(request, 'STORY business metric definition updated successfully.')
        elif action == 'add_target':
            rm_name = request.POST.get('rm_name')
            month_label = request.POST.get('month_label')
            target_billing = request.POST.get('target_billing') or '0'
            target_story = request.POST.get('target_story') or '0'
            MonthlyRMTarget.objects.update_or_create(
                rm_name=rm_name,
                month_label=month_label,
                defaults={
                    'target_billing': target_billing,
                    'target_story': target_story
                }
            )
            AuditLog.objects.create(
                action='TARGET_UPDATE',
                model_name='MonthlyRMTarget',
                object_id=f"{rm_name}_{month_label}",
                user=request.user,
                details={'rm': rm_name, 'month': month_label, 'target_billing': target_billing}
            )
            messages.success(request, f'Target set for {rm_name} in {month_label}.')
        return redirect('core:settings')

    return render(request, 'core/settings.html', {
        'metric': metric,
        'targets': targets,
        'rms': rms,
        'months': months,
    })


# ==========================================
# RBAC & PERMISSION MANAGEMENT VIEWS
# ==========================================

@login_required
@permission_required('rbac', 'can_view')
def rbac_dashboard_view(request):
    """
    Overview of all Users and Role Templates with assignment stats.
    """
    users = User.objects.select_related('profile', 'profile__role').order_by('username')
    roles = Role.objects.prefetch_related('permissions').all().order_by('is_system_role', 'name')

    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    total_roles = roles.count()
    superadmins_count = users.filter(is_superuser=True).count()

    return render(request, 'core/rbac_dashboard.html', {
        'users': users,
        'roles': roles,
        'total_users': total_users,
        'active_users': active_users,
        'total_roles': total_roles,
        'superadmins_count': superadmins_count,
        'module_groups': MODULE_GROUPS,
    })


@login_required
@permission_required('rbac', 'can_manage')
def rbac_user_create_view(request):
    """
    Create a new user account and assign role & profile.
    """
    roles = Role.objects.all().order_by('name')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role_id = request.POST.get('role_id')
        department = request.POST.get('department', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'core/rbac_user_form.html', {'roles': roles, 'action_title': 'Create New User'})

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists. Please choose a different username.")
            return render(request, 'core/rbac_user_form.html', {'roles': roles, 'action_title': 'Create New User'})

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        selected_role = Role.objects.filter(id=role_id).first() if role_id else None
        if not selected_role:
            selected_role = Role.objects.filter(code='ANALYST').first()

        UserProfile.objects.create(
            user=user,
            role=selected_role,
            department=department,
            phone=phone,
            use_custom_permissions=False
        )

        AuditLog.objects.create(
            action='USER_CREATE',
            model_name='User',
            object_id=str(user.id),
            user=request.user,
            details={'username': username, 'role': selected_role.name if selected_role else None}
        )

        messages.success(request, f"User '{username}' created successfully with role '{selected_role.name if selected_role else 'None'}'.")
        return redirect('core:rbac_dashboard')

    return render(request, 'core/rbac_user_form.html', {
        'roles': roles,
        'action_title': 'Create New User',
    })


@login_required
@permission_required('rbac', 'can_manage')
def rbac_user_edit_view(request, user_id):
    """
    Edit user profile, name, email, role, and optional password reset.
    """
    target_user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    roles = Role.objects.all().order_by('name')

    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', '').strip()
        target_user.last_name = request.POST.get('last_name', '').strip()
        target_user.email = request.POST.get('email', '').strip()

        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            target_user.set_password(new_password)

        role_id = request.POST.get('role_id')
        selected_role = Role.objects.filter(id=role_id).first() if role_id else None
        profile.role = selected_role
        profile.department = request.POST.get('department', '').strip()
        profile.phone = request.POST.get('phone', '').strip()

        # Update superuser flag if selected role is SUPER_ADMIN
        if selected_role and selected_role.code == 'SUPER_ADMIN':
            target_user.is_superuser = True
            target_user.is_staff = True
        elif not target_user.is_superuser:
            pass  # keep existing staff/superuser flags safe

        target_user.save()
        profile.save()

        AuditLog.objects.create(
            action='USER_UPDATE',
            model_name='User',
            object_id=str(target_user.id),
            user=request.user,
            details={'username': target_user.username, 'role': selected_role.name if selected_role else None}
        )

        messages.success(request, f"User '{target_user.username}' updated successfully.")
        return redirect('core:rbac_dashboard')

    return render(request, 'core/rbac_user_form.html', {
        'target_user': target_user,
        'profile': profile,
        'roles': roles,
        'action_title': f"Edit User: {target_user.username}",
    })


@login_required
@permission_required('rbac', 'can_manage')
def rbac_toggle_user_active_view(request, user_id):
    """
    Activate or deactivate a user account.
    """
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('core:rbac_dashboard')

    target_user.is_active = not target_user.is_active
    target_user.save()

    status_str = "activated" if target_user.is_active else "deactivated"
    AuditLog.objects.create(
        action='USER_UPDATE',
        model_name='User',
        object_id=str(target_user.id),
        user=request.user,
        details={'username': target_user.username, 'is_active': target_user.is_active}
    )
    messages.success(request, f"User '{target_user.username}' has been {status_str}.")
    return redirect('core:rbac_dashboard')


@login_required
@permission_required('rbac', 'can_manage')
def rbac_user_permissions_view(request, user_id):
    """
    Dynamic Matrix UI to configure individual granular permission overrides (INHERIT / ALLOW / DENY).
    """
    target_user = get_object_or_404(User.objects.select_related('profile', 'profile__role'), id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    all_roles = Role.objects.all().order_by('name')
    modules = list(AppModule.objects.filter(is_active=True).order_by('order'))
    action_fields = ['can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage']

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'save_overrides')

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
            messages.success(request, f"Permissions for '{target_user.username}' were reset to role defaults.")
            return redirect('core:rbac_user_permissions', user_id=target_user.id)

        # Update role assignment if submitted
        new_role_id = request.POST.get('role_id')
        if new_role_id:
            new_role = Role.objects.filter(id=new_role_id).first()
            if new_role and profile.role != new_role:
                profile.role = new_role
                profile.save()
                if new_role.code == 'SUPER_ADMIN':
                    target_user.is_superuser = True
                    target_user.is_staff = True
                    target_user.save()

        # Save 3-state overrides
        for mod in modules:
            allowed = mod.supported_actions or ['view']
            override_payload = {}
            has_non_inherit = False

            for act in action_fields:
                short_act = act.replace('can_', '')
                field_name = f"override_{mod.code}_{act}"
                override_val = request.POST.get(field_name, 'INHERIT')

                if short_act in allowed:
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
            details={'target_user': target_user.username, 'role': profile.role.name if profile.role else None}
        )
        clear_user_permission_cache(request)

        messages.success(request, f"Individual permission overrides for '{target_user.username}' updated successfully.")
        return redirect('core:rbac_user_permissions', user_id=target_user.id)

    # Prepare matrix rows
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
        for act in action_fields:
            short_act = act.replace('can_', '')
            is_allowed = short_act in allowed
            role_def = getattr(rp, act, False) if rp else (profile.role and profile.role.code == 'SUPER_ADMIN')
            current_ov = getattr(ov, f"{short_act}_override", 'INHERIT') if ov else 'INHERIT'
            effective_val = eff_mod.get(act, False)

            row_actions[act] = {
                'is_allowed': is_allowed,
                'role_default': role_def,
                'current_override': current_ov,
                'effective_value': effective_val,
                'field_name': f"override_{mod.code}_{act}",
            }

        matrix_rows.append({
            'code': mod.code,
            'name': mod.name,
            'group': mod.group,
            'icon': mod.icon,
            'actions': row_actions,
        })

    return render(request, 'core/rbac_matrix.html', {
        'target_user': target_user,
        'profile': profile,
        'roles': all_roles,
        'matrix_rows': matrix_rows,
        'action_fields': action_fields,
        'mode': 'user',
        'page_title': f"Configure Permissions: {target_user.username}",
    })


@login_required
@permission_required('rbac', 'can_manage')
def rbac_role_permissions_view(request, role_id):
    """
    Matrix UI to configure permissions for a Role template.
    """
    role = get_object_or_404(Role, id=role_id)
    modules = list(AppModule.objects.filter(is_active=True).order_by('order'))
    action_fields = ['can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage']

    if request.method == 'POST':
        for mod in modules:
            allowed = mod.supported_actions or ['view']
            perm_vals = {}
            for act in action_fields:
                short_act = act.replace('can_', '')
                if short_act in allowed:
                    field_name = f"perm_{mod.code}_{act}"
                    perm_vals[act] = (request.POST.get(field_name) == 'on')
                else:
                    perm_vals[act] = False

            RolePermission.objects.update_or_create(
                role=role,
                module=mod,
                defaults=perm_vals
            )

        AuditLog.objects.create(
            action='ROLE_UPDATE',
            model_name='Role',
            object_id=str(role.id),
            user=request.user,
            details={'role_code': role.code, 'role_name': role.name}
        )
        clear_user_permission_cache(request)

        messages.success(request, f"Role template '{role.name}' default permissions updated successfully.")
        return redirect('core:rbac_role_permissions', role_id=role.id)

    role_perms_map = {
        rp.module.code: rp for rp in RolePermission.objects.filter(role=role).select_related('module')
    }

    matrix_rows = []
    for mod in modules:
        allowed = mod.supported_actions or ['view']
        rp = role_perms_map.get(mod.code)

        row_actions = {}
        for act in action_fields:
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

    return render(request, 'core/rbac_matrix.html', {
        'role': role,
        'matrix_rows': matrix_rows,
        'action_fields': action_fields,
        'mode': 'role',
        'page_title': f"Configure Role Permissions: {role.name}",
    })


@login_required
@permission_required('rbac', 'can_manage')
def rbac_role_create_view(request):
    """
    Create a new custom Role template.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        code = slugify(name).upper().replace('-', '_')

        if not name:
            messages.error(request, 'Role name is required.')
            return redirect('core:rbac_dashboard')

        if Role.objects.filter(code=code).exists():
            messages.error(request, f"A role with code '{code}' already exists.")
            return redirect('core:rbac_dashboard')

        role = Role.objects.create(
            name=name,
            code=code,
            description=description,
            is_system_role=False
        )

        AuditLog.objects.create(
            action='ROLE_CREATE',
            model_name='Role',
            object_id=str(role.id),
            user=request.user,
            details={'role_name': name, 'role_code': code}
        )

        messages.success(request, f"Role '{name}' created. You can now configure its permissions.")
        return redirect('core:rbac_role_permissions', role_id=role.id)

    return redirect('core:rbac_dashboard')
