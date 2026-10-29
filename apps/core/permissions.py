"""
Core RBAC Permission Engine for Havells Billing MIS.
Evaluates granular role-based and user-specific module permissions with request-level caching.
"""

from functools import wraps
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from apps.core.constants import AVAILABLE_MODULES, MODULE_DICT


def get_user_effective_permissions(user, request=None):
    """
    Computes and returns the complete permission map for a given user.
    Uses request-level memoization to avoid redundant database hits during a single request cycle.
    
    Returns:
        dict: {
            'dashboard': {'can_view': True, 'can_add': False, ...},
            'upload': {'can_view': True, 'can_upload': True, ...},
            ...
        }
    """
    if request and hasattr(request, '_effective_perms_cache'):
        return request._effective_perms_cache

    # Initialize full default dictionary with all permissions as False
    perm_dict = {}
    for m in AVAILABLE_MODULES:
        perm_dict[m['code']] = {
            'can_view': False,
            'can_add': False,
            'can_edit': False,
            'can_delete': False,
            'can_upload': False,
            'can_export': False,
            'can_manage': False,
        }

    # 1. Unauthenticated or inactive users have no access
    if not user or not user.is_authenticated or not user.is_active:
        if request:
            request._effective_perms_cache = perm_dict
        return perm_dict

    # 2. Super Admin has unrestricted access to everything
    if user.is_superuser:
        for m in AVAILABLE_MODULES:
            perm_dict[m['code']] = {
                'can_view': True,
                'can_add': True,
                'can_edit': True,
                'can_delete': True,
                'can_upload': True,
                'can_export': True,
                'can_manage': True,
            }
        if request:
            request._effective_perms_cache = perm_dict
        return perm_dict

    # 3. Retrieve user profile and permissions
    from apps.core.models import UserProfile, ModulePermission

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.use_custom_permissions:
        # User has explicit custom overrides configured
        perms_qs = user.custom_permissions.all()
    elif profile.role:
        # User inherits permissions from their assigned functional Role template
        perms_qs = profile.role.permissions.all()
    else:
        perms_qs = []

    for p in perms_qs:
        if p.module_code in perm_dict:
            perm_dict[p.module_code] = {
                'can_view': p.can_view,
                'can_add': p.can_add,
                'can_edit': p.can_edit,
                'can_delete': p.can_delete,
                'can_upload': p.can_upload,
                'can_export': p.can_export,
                'can_manage': p.can_manage,
            }

    if request:
        request._effective_perms_cache = perm_dict

    return perm_dict


def has_module_perm(user, module_code, action='view', request=None):
    """
    Evaluates whether a user has permission to perform `action` on `module_code`.
    Actions: 'view', 'add', 'edit', 'delete', 'upload', 'export', 'manage'.
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
    Decorator for views that checks whether the user has the required permission
    for a specific module before allowing execution.
    
    If unauthorized:
      - API / AJAX requests receive an HTTP 403 JSON error.
      - Web navigation receives an HTTP 403 Forbidden branded error page.
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
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
