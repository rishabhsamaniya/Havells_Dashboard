from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.models import Role, UserProfile, ModulePermission, AuditLog
from apps.core.constants import AVAILABLE_MODULES, DEFAULT_ROLE_TEMPLATES
from apps.core.permissions import has_module_perm, get_user_effective_permissions

User = get_user_model()

class RBACSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Seed roles & permissions
        for role_code, role_data in DEFAULT_ROLE_TEMPLATES.items():
            role = Role.objects.create(
                code=role_code,
                name=role_data["name"],
                description=role_data["description"],
                is_system_role=True,
            )
            modules_dict = role_data.get("modules") or role_data.get("permissions", {})
            for mod_code, flags in modules_dict.items():
                ModulePermission.objects.create(
                    role=role,
                    module_code=mod_code,
                    can_view=flags.get("can_view", False),
                    can_add=flags.get("can_add", False),
                    can_edit=flags.get("can_edit", False),
                    can_delete=flags.get("can_delete", False),
                    can_upload=flags.get("can_upload", False),
                    can_export=flags.get("can_export", False),
                    can_manage=flags.get("can_manage", False),
                )

        # 1. Super Admin User
        self.super_role = Role.objects.get(code="SUPER_ADMIN")
        self.super_user = User.objects.create_superuser(
            username="superadmin",
            password="adminpassword123",
            email="admin@havells.com"
        )
        UserProfile.objects.create(user=self.super_user, role=self.super_role)

        # 2. Analyst User (Read-only analytics, no upload, no admin/audit/settings)
        self.analyst_role = Role.objects.get(code="ANALYST")
        self.analyst_user = User.objects.create_user(
            username="analyst_user",
            password="analystpassword123",
            email="analyst@havells.com"
        )
        UserProfile.objects.create(user=self.analyst_user, role=self.analyst_role)

        # 3. MIS Executive User (Analytics + Upload + Import History)
        self.mis_role = Role.objects.get(code="MIS_EXECUTIVE")
        self.mis_user = User.objects.create_user(
            username="mis_user",
            password="mispassword123",
            email="mis@havells.com"
        )
        UserProfile.objects.create(user=self.mis_user, role=self.mis_role)

    def test_superadmin_full_access(self):
        """Super Admin has unrestricted access to all modules and dashboards."""
        self.client.login(username="superadmin", password="adminpassword123")
        
        urls_to_test = [
            reverse('analytics:dashboard'),
            reverse('analytics:rm'),
            reverse('analytics:monthly'),
            reverse('imports:upload'),
            reverse('imports:history'),
            reverse('quality:issues'),
            reverse('core:audit_logs'),
            reverse('core:settings'),
            reverse('core:rbac_dashboard'),
        ]
        for url in urls_to_test:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Super Admin should access {url}")

    def test_direct_url_unauthorized_blocked_403(self):
        """Analyst attempting to access restricted URL receives HTTP 403 Forbidden."""
        self.client.login(username="analyst_user", password="analystpassword123")

        restricted_urls = [
            reverse('imports:upload'),
            reverse('core:audit_logs'),
            reverse('core:settings'),
            reverse('core:rbac_dashboard'),
        ]
        for url in restricted_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"Analyst must receive 403 Forbidden on {url}")
            self.assertTemplateUsed(response, 'core/403.html')

    def test_upload_post_permission_enforcement(self):
        """Users without upload permission cannot initiate upload requests."""
        self.client.login(username="analyst_user", password="analystpassword123")
        
        # Direct POST to upload endpoint
        response = self.client.post(reverse('imports:upload'), {'excel_file': 'fake.xlsx'})
        self.assertEqual(response.status_code, 403)

    def test_export_permission_enforcement(self):
        """User without can_export is blocked with HTTP 403 Forbidden."""
        custom_role = Role.objects.create(code="NO_EXPORT_ROLE", name="No Export Role")
        ModulePermission.objects.create(role=custom_role, module_code='export', can_view=True, can_export=False)
        no_export_user = User.objects.create_user(username="no_export", password="password123")
        UserProfile.objects.create(user=no_export_user, role=custom_role)

        self.client.login(username="no_export", password="password123")
        response = self.client.get(reverse('analytics:export_mis'))
        self.assertEqual(response.status_code, 403, "User without can_export should be blocked with 403")

    def test_sidebar_dynamic_visibility(self):
        """Sidebar contains only permitted links and hides empty unauthorized groups."""
        self.client.login(username="analyst_user", password="analystpassword123")
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        # Permitted modules
        self.assertIn('id="nav-dashboard"', content)
        self.assertIn('id="nav-rm"', content)
        self.assertIn('id="nav-monthly"', content)

        # Restricted modules should NOT be in the HTML
        self.assertNotIn('id="nav-upload"', content)
        self.assertNotIn('id="nav-audit"', content)
        self.assertNotIn('id="nav-settings"', content)
        self.assertNotIn('id="nav-rbac"', content)

    def test_immediate_permission_revocation(self):
        """Revoking permission takes effect immediately on the next request."""
        self.client.login(username="mis_user", password="mispassword123")
        # Initially MIS Executive can view import history
        response = self.client.get(reverse('imports:history'))
        self.assertEqual(response.status_code, 200)

        # Super Admin revokes history permission from MIS_EXECUTIVE role
        perm = ModulePermission.objects.get(role=self.mis_role, module_code='history')
        perm.can_view = False
        perm.save()

        # Immediate next request must be 403 Forbidden
        response = self.client.get(reverse('imports:history'))
        self.assertEqual(response.status_code, 403)

    def test_custom_user_matrix_override(self):
        """User with use_custom_permissions=True overrides their base role template."""
        # Analyst by default cannot upload
        self.assertFalse(has_module_perm(self.analyst_user, 'upload', 'can_view'))

        # Enable custom permissions and grant upload view
        profile = self.analyst_user.profile
        profile.use_custom_permissions = True
        profile.save()
        self.analyst_user.refresh_from_db()

        ModulePermission.objects.create(
            user=self.analyst_user,
            module_code='upload',
            can_view=True,
            can_upload=False
        )

        self.assertTrue(has_module_perm(self.analyst_user, 'upload', 'can_view'))
        self.assertFalse(has_module_perm(self.analyst_user, 'upload', 'can_upload'))

    def test_deactivated_user_cannot_login(self):
        """Deactivated user account is rejected at login."""
        self.analyst_user.is_active = False
        self.analyst_user.save()

        login_success = self.client.login(username="analyst_user", password="analystpassword123")
        self.assertFalse(login_success)

    def test_anonymous_user_redirected_to_login(self):
        """Unauthenticated user accessing protected dashboard is redirected to login."""
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
