from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import Role, AppModule, RolePermission, UserProfile, ModulePermission
from apps.core.constants import DEFAULT_ROLE_TEMPLATES, AVAILABLE_MODULES

User = get_user_model()

class Command(BaseCommand):
    help = "Initializes AppModule registry, 5 default RBAC roles, and role permissions."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-reset',
            action='store_true',
            help='Reset all role permissions to factory defaults',
        )

    def handle(self, *args, **options):
        force_reset = options.get('force_reset', False)
        self.stdout.write(self.style.NOTICE("Initializing Dynamic AppModule Registry and 5 Predefined Roles..."))
        
        # 1. Seed or Sync AppModule Registry
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
            status_str = "Created" if created else "Synced"
            self.stdout.write(f"  [{status_str}] Module: {app_mod.name} ({app_mod.code})")

        # 2. Seed 5 Predefined Roles
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
            
            self.stdout.write(f"  - Configured Role: {role.name} ({role.code})")

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
                    # Do not overwrite if admin already customized permissions
                    RolePermission.objects.get_or_create(
                        role=role,
                        module=app_mod,
                        defaults=defaults_payload
                    )

                # Legacy ModulePermission sync
                ModulePermission.objects.update_or_create(
                    role=role,
                    module_code=mod_code,
                    defaults=defaults_payload
                )

        # 3. Ensure Superusers and existing users have UserProfiles
        super_admin_role = Role.objects.filter(code="SUPER_ADMIN").first()
        custom_user_role = Role.objects.filter(code="CUSTOM_USER").first() or Role.objects.filter(code="ANALYST").first()

        for user in User.objects.all():
            assigned_role = super_admin_role if user.is_superuser else custom_user_role
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": assigned_role,
                }
            )
            if not profile.role:
                profile.role = assigned_role
                profile.save()
            self.stdout.write(f"  - User '{user.username}' associated with Role: {profile.role.name if profile.role else 'None'}")

        self.stdout.write(self.style.SUCCESS("Dynamic RBAC initialization completed successfully!"))
