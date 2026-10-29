"""
Idempotent Seeder for Dynamic RBAC System.
Ensures that all 18 Application Modules and 5 Predefined Roles exist in the database.
Can be safely called from migrations, management commands, views, or admin.
"""

from apps.core.constants import AVAILABLE_MODULES, DEFAULT_ROLE_TEMPLATES

def ensure_rbac_seeded(force_reset=False):
    from apps.core.models import AppModule, Role, RolePermission, UserProfile, ModulePermission
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # 1. Seed or Sync AppModule Registry (18 Modules)
    module_instances = {}
    for idx, mod_info in enumerate(AVAILABLE_MODULES):
        app_mod, created = AppModule.objects.update_or_create(
            code=mod_info['code'],
            defaults={
                'name': mod_info['name'],
                'group': mod_info['group'],
                'icon': mod_info.get('icon', 'bi-app'),
                'url_name': mod_info.get('default_route', ''),
                'supported_actions': mod_info.get('actions', ['view']),
                'order': idx,
                'is_active': True,
            }
        )
        module_instances[mod_info['code']] = app_mod

    # 2. Seed 5 Predefined Roles & Defaults
    for role_code, role_data in DEFAULT_ROLE_TEMPLATES.items():
        role, created = Role.objects.get_or_create(
            code=role_code,
            defaults={
                "name": role_data["name"],
                "description": role_data["description"],
                "is_system_role": True,
            }
        )
        if not created and role.name != role_data["name"]:
            role.name = role_data["name"]
            role.description = role_data["description"]
            role.save()

        # Seed role default permissions
        role_modules_dict = role_data.get("modules", {})
        for mod_code, app_mod in module_instances.items():
            flags = role_modules_dict.get(mod_code, {})
            allowed = app_mod.supported_actions

            defaults_payload = {
                "can_view": flags.get("can_view", False) if 'view' in allowed else False,
                "can_add": flags.get("can_add", False) if 'add' in allowed else False,
                "can_edit": flags.get("can_edit", False) if 'edit' in allowed else False,
                "can_delete": flags.get("can_delete", False) if 'delete' in allowed else False,
                "can_upload": flags.get("can_upload", False) if 'upload' in allowed else False,
                "can_export": flags.get("can_export", False) if 'export' in allowed else False,
                "can_manage": flags.get("can_manage", False) if 'manage' in allowed else False,
            }

            if force_reset:
                RolePermission.objects.update_or_create(
                    role=role,
                    module=app_mod,
                    defaults=defaults_payload
                )
            else:
                RolePermission.objects.get_or_create(
                    role=role,
                    module=app_mod,
                    defaults=defaults_payload
                )

            # Sync legacy ModulePermission
            ModulePermission.objects.update_or_create(
                role=role,
                module_code=mod_code,
                defaults=defaults_payload
            )

    # 3. Ensure existing users have UserProfile and a Role assigned
    super_admin_role = Role.objects.filter(code="SUPER_ADMIN").first()
    mgmt_role = Role.objects.filter(code="MANAGEMENT").first()
    analyst_role = Role.objects.filter(code="ANALYST").first()
    custom_role = Role.objects.filter(code="CUSTOM_USER").first()
    fallback_role = mgmt_role or analyst_role or custom_role

    for user in User.objects.all():
        assigned_role = super_admin_role if user.is_superuser else fallback_role
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": assigned_role}
        )
        if not profile.role:
            profile.role = assigned_role
            profile.save()

    return True
