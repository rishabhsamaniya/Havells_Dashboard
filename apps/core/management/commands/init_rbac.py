from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import Role, ModulePermission, UserProfile
from apps.core.constants import DEFAULT_ROLE_TEMPLATES, AVAILABLE_MODULES

User = get_user_model()

class Command(BaseCommand):
    help = "Initializes default RBAC roles and module permissions, and associates existing users."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing RBAC Roles and Permissions..."))
        
        # 1. Seed Roles & Role Permissions
        for role_code, role_data in DEFAULT_ROLE_TEMPLATES.items():
            role, created = Role.objects.get_or_create(
                code=role_code,
                defaults={
                    "name": role_data["name"],
                    "description": role_data["description"],
                    "is_system_role": True,
                }
            )
            if not created:
                role.name = role_data["name"]
                role.description = role_data["description"]
                role.save()
            
            self.stdout.write(f"  - Configured Role: {role.name} ({role.code})")

            # Seed permissions for this role
            perms_dict = role_data.get("modules") or role_data.get("permissions", {})
            for mod_code, flags in perms_dict.items():
                ModulePermission.objects.update_or_create(
                    role=role,
                    module_code=mod_code,
                    defaults={
                        "can_view": flags.get("can_view", False),
                        "can_add": flags.get("can_add", False),
                        "can_edit": flags.get("can_edit", False),
                        "can_delete": flags.get("can_delete", False),
                        "can_upload": flags.get("can_upload", False),
                        "can_export": flags.get("can_export", False),
                        "can_manage": flags.get("can_manage", False),
                    }
                )

        # 2. Ensure Superusers and existing users have UserProfiles
        super_admin_role = Role.objects.filter(code="SUPER_ADMIN").first()
        analyst_role = Role.objects.filter(code="ANALYST").first()

        for user in User.objects.all():
            assigned_role = super_admin_role if user.is_superuser else analyst_role
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": assigned_role,
                    "use_custom_permissions": False,
                }
            )
            if not profile.role:
                profile.role = assigned_role
                profile.save()
            self.stdout.write(f"  - User '{user.username}' associated with Role: {profile.role.name if profile.role else 'None'}")

        self.stdout.write(self.style.SUCCESS("RBAC initialization completed successfully!"))
