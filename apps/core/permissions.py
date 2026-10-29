"""
Core RBAC Permission Engine for Havells Billing MIS.
Evaluates granular role-based default permissions and user-specific 3-state overrides (INHERIT, ALLOW, DENY).
Features request-level memoization for zero redundant DB queries.
"""

from functools import wraps
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings

from apps.core.constants import AVAILABLE_MODULES, MODULE_DICT


def clear_user_permission_cache(request=None):
    """Invalidates request-level memoized permission cache."""
    if request and hasattr(request, '_effective_perms_cache'):
        delattr(request, '_effective_perms_cache')


def get_user_effective_permissions(user, request=None):
    """
    Computes and returns the complete permission map for a given user.
    Evaluates:
      1. Super Admin full access bypass.
      2. Inactive account blocking.
      3. Role default permissions (from RolePermission).
      4. Individual user overrides (from UserPermissionOverride):
         - 'ALLOW' grants access even if role denies it.
         - 'DENY' blocks access even if role grants it.
         - 'INHERIT' follows the role default.
    """
    if request and hasattr(request, '_effective_perms_cache'):
        return request._effective_perms_cache

    from apps.core.models import AppModule, RolePermission, UserPermissionOverride, UserProfile

    # 1. Fetch registered modules from database or fallback to constants
    try:
        if AppModule.objects.filter(is_active=True).count() < len(AVAILABLE_MODULES):
            from apps.core.seeder import ensure_rbac_seeded
            ensure_rbac_seeded()
        modules = list(AppModule.objects.filter(is_active=True).order_by('order'))
    except Exception:
        modules = []

    if not modules:
        mod_codes = [m['code'] for m in AVAILABLE_MODULES]
    else:
        mod_codes = [m.code for m in modules]

    actions = ['can_view', 'can_add', 'can_edit', 'can_delete', 'can_upload', 'can_export', 'can_manage']
    perm_dict = {}
    for code in mod_codes:
        perm_dict[code] = {act: False for act in actions}
        perm_dict[code]['sources'] = {act: 'DEFAULT_DENY' for act in actions}

    # 2. Unauthenticated or inactive users have zero access
    if not user or not user.is_authenticated or not user.is_active:
        if request:
            request._effective_perms_cache = perm_dict
        return perm_dict

    # 3. Super Admin has unrestricted access to every module and action
    if user.is_superuser:
        for code in mod_codes:
            for act in actions:
                perm_dict[code][act] = True
                perm_dict[code]['sources'][act] = 'SUPER_ADMIN'
        if request:
            request._effective_perms_cache = perm_dict
        return perm_dict

    # 4. Resolve Role Defaults
    profile = getattr(user, 'profile', None)
    if profile is None:
        try:
            profile = UserProfile.objects.select_related('role').get(user=user)
        except UserProfile.DoesNotExist:
            profile = None

    role = profile.role if profile else None
    role_defaults = {}

    if role:
        if role.code == 'SUPER_ADMIN':
            for code in mod_codes:
                role_defaults[code] = {act: True for act in actions}
        else:
            role_perms = RolePermission.objects.filter(role=role).select_related('module')
            for rp in role_perms:
                m_code = rp.module.code
                role_defaults[m_code] = {
                    'can_view': rp.can_view,
                    'can_add': rp.can_add,
                    'can_edit': rp.can_edit,
                    'can_delete': rp.can_delete,
                    'can_upload': rp.can_upload,
                    'can_export': rp.can_export,
                    'can_manage': rp.can_manage,
                }
            # Fallback to legacy ModulePermission if RolePermission not yet populated
            if not role_defaults:
                from apps.core.models import ModulePermission
                for lp in ModulePermission.objects.filter(role=role):
                    role_defaults[lp.module_code] = {
                        'can_view': lp.can_view,
                        'can_add': lp.can_add,
                        'can_edit': lp.can_edit,
                        'can_delete': lp.can_delete,
                        'can_upload': lp.can_upload,
                        'can_export': lp.can_export,
                        'can_manage': lp.can_manage,
                    }

    # 5. Resolve Individual User Overrides (INHERIT / ALLOW / DENY)
    user_overrides_map = {}
    overrides = UserPermissionOverride.objects.filter(user=user).select_related('module')
    for ov in overrides:
        m_code = ov.module.code
        user_overrides_map[m_code] = {
            'can_view': ov.view_override,
            'can_add': ov.add_override,
            'can_edit': ov.edit_override,
            'can_delete': ov.delete_override,
            'can_upload': ov.upload_override,
            'can_export': ov.export_override,
            'can_manage': ov.manage_override,
        }

    # Legacy support: if profile.use_custom_permissions is True and no UserPermissionOverride records
    legacy_custom_perms = {}
    if profile and getattr(profile, 'use_custom_permissions', False) and not user_overrides_map:
        from apps.core.models import ModulePermission
        for lp in ModulePermission.objects.filter(user=user):
            legacy_custom_perms[lp.module_code] = {
                'can_view': lp.can_view,
                'can_add': lp.can_add,
                'can_edit': lp.can_edit,
                'can_delete': lp.can_delete,
                'can_upload': lp.can_upload,
                'can_export': lp.can_export,
                'can_manage': lp.can_manage,
            }

    # 6. Merge Permissions: Overrides take absolute precedence over Role defaults
    for code in mod_codes:
        mod_role = role_defaults.get(code, {})
        mod_override = user_overrides_map.get(code, {})
        mod_legacy = legacy_custom_perms.get(code, {})

        for act in actions:
            override_val = mod_override.get(act, 'INHERIT')

            if override_val == 'ALLOW':
                perm_dict[code][act] = True
                perm_dict[code]['sources'][act] = 'OVERRIDE_ALLOW'
            elif override_val == 'DENY':
                perm_dict[code][act] = False
                perm_dict[code]['sources'][act] = 'OVERRIDE_DENY'
            elif legacy_custom_perms and code in legacy_custom_perms:
                val = mod_legacy.get(act, False)
                perm_dict[code][act] = val
                perm_dict[code]['sources'][act] = 'LEGACY_CUSTOM'
            else:
                # INHERIT: Follow role default
                role_val = mod_role.get(act, False)
                perm_dict[code][act] = role_val
                perm_dict[code]['sources'][act] = f"ROLE_{role.code}" if (role and role_val) else "DEFAULT_DENY"

    if request:
        request._effective_perms_cache = perm_dict

    return perm_dict


def has_module_perm(user, module_code, action='view', request=None):
    """
    Evaluates whether `user` is authorized to perform `action` on `module_code`.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    if user.is_superuser:
        return True

    perms = get_user_effective_permissions(user, request=request)
    mod_perms = perms.get(module_code, {})

    action_field = action if action.startswith('can_') else f"can_{action}"
    return mod_perms.get(action_field, False)


def permission_required(module_code, action='view'):
    """
    Decorator for views that enforces permission authorization.
    Rejects unauthorized access with HTTP 403 Forbidden.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if not has_module_perm(request.user, module_code, action, request=request):
                mod_meta = MODULE_DICT.get(module_code, {'name': module_code, 'group': 'System'})

                # Return JSON 403 for AJAX / programmatic requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or \
                   request.path.endswith(('.json', '/api/')) or \
                   'application/json' in request.headers.get('Accept', ''):
                    return JsonResponse({
                        'error': 'Permission Denied',
                        'detail': f"You do not have '{action}' permission for module '{mod_meta.get('name')}'.",
                        'module': module_code,
                        'required_action': action
                    }, status=403)

                # Return styled HTML 403 page
                return render(request, 'core/403.html', {
                    'module_name': mod_meta.get('name'),
                    'module_group': mod_meta.get('group'),
                    'module_code': module_code,
                    'required_action': action.capitalize(),
                    'error_message': f"You do not have '{action}' permission to access this module.",
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
