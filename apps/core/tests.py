from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.management import call_command

from apps.core.models import (
    Role, UserProfile, AppModule, RolePermission, 
    UserPermissionOverride, ModulePermission, AuditLog
)
from apps.core.constants import AVAILABLE_MODULES, DEFAULT_ROLE_TEMPLATES
from apps.core.permissions import has_module_perm, get_user_effective_permissions, clear_user_permission_cache

User = get_user_model()


class DynamicRBACSystemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Run init_rbac once for all tests to seed AppModule, 5 Predefined Roles, and RolePermission records
        call_command('init_rbac', force_reset=True)

        # 1. Super Admin User
        cls.super_role = Role.objects.get(code="SUPER_ADMIN")
        cls.super_user = User.objects.create_superuser(
            username="superadmin",
            password="adminpassword123",
            email="admin@havells.com"
        )
        UserProfile.objects.update_or_create(user=cls.super_user, defaults={'role': cls.super_role})

        # 2. Analyst User (Read-only analytics, no upload, no admin/audit/settings)
        cls.analyst_role = Role.objects.get(code="ANALYST")
        cls.analyst_user = User.objects.create_user(
            username="analyst_user",
            password="analystpassword123",
            email="analyst@havells.com"
        )
        UserProfile.objects.update_or_create(user=cls.analyst_user, defaults={'role': cls.analyst_role})

        # 3. MIS Executive User (Analytics + Upload + Import History)
        cls.mis_role = Role.objects.get(code="MIS_EXECUTIVE")
        cls.mis_user = User.objects.create_user(
            username="mis_user",
            password="mispassword123",
            email="mis@havells.com"
        )
        UserProfile.objects.update_or_create(user=cls.mis_user, defaults={'role': cls.mis_role})

        # 4. Custom User
        cls.custom_role = Role.objects.get(code="CUSTOM_USER")
        cls.custom_user = User.objects.create_user(
            username="custom_user",
            password="custompassword123",
            email="custom@havells.com"
        )
        UserProfile.objects.update_or_create(user=cls.custom_user, defaults={'role': cls.custom_role})

    def setUp(self):
        self.client = Client()

    def test_five_predefined_roles_exist(self):
        """All 5 predefined roles must exist in the database."""
        expected_roles = ["SUPER_ADMIN", "MANAGEMENT", "MIS_EXECUTIVE", "ANALYST", "CUSTOM_USER"]
        for role_code in expected_roles:
            self.assertTrue(Role.objects.filter(code=role_code).exists(), f"Role {role_code} must exist.")

    def test_init_rbac_is_idempotent(self):
        """Running init_rbac multiple times does not duplicate roles or modules."""
        initial_role_count = Role.objects.count()
        initial_mod_count = AppModule.objects.count()

        call_command('init_rbac')

        self.assertEqual(Role.objects.count(), initial_role_count)
        self.assertEqual(AppModule.objects.count(), initial_mod_count)

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
        
        response = self.client.post(reverse('imports:upload'), {'excel_file': 'fake.xlsx'})
        self.assertEqual(response.status_code, 403)

    def test_export_permission_enforcement(self):
        """User without can_export is blocked with HTTP 403 Forbidden."""
        export_mod = AppModule.objects.get(code='export')
        role_perm = RolePermission.objects.get(role=self.analyst_role, module=export_mod)
        role_perm.can_export = False
        role_perm.save()

        self.client.login(username="analyst_user", password="analystpassword123")
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
        """Revoking permission in RolePermission takes effect immediately."""
        self.client.login(username="mis_user", password="mispassword123")
        # Initially MIS Executive can view import history
        response = self.client.get(reverse('imports:history'))
        self.assertEqual(response.status_code, 200)

        # Super Admin revokes history permission from MIS_EXECUTIVE role
        history_mod = AppModule.objects.get(code='history')
        perm = RolePermission.objects.get(role=self.mis_role, module=history_mod)
        perm.can_view = False
        perm.save()

        # Immediate next request must be 403 Forbidden
        response = self.client.get(reverse('imports:history'))
        self.assertEqual(response.status_code, 403)

    def test_three_state_user_override_allow_and_deny(self):
        """Explicit ALLOW grants permission; explicit DENY blocks permission."""
        upload_mod = AppModule.objects.get(code='upload')
        dashboard_mod = AppModule.objects.get(code='dashboard')

        # 1. By default, analyst cannot upload, but can view dashboard
        self.assertFalse(has_module_perm(self.analyst_user, 'upload', 'can_view'))
        self.assertTrue(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

        # 2. Add UserPermissionOverride: ALLOW for upload view & upload action
        UserPermissionOverride.objects.create(
            user=self.analyst_user,
            module=upload_mod,
            view_override='ALLOW',
            upload_override='ALLOW'
        )

        # 3. Add UserPermissionOverride: DENY for dashboard view
        UserPermissionOverride.objects.create(
            user=self.analyst_user,
            module=dashboard_mod,
            view_override='DENY'
        )

        # Effective permissions should reflect overrides
        self.assertTrue(has_module_perm(self.analyst_user, 'upload', 'can_view'))
        self.assertTrue(has_module_perm(self.analyst_user, 'upload', 'can_upload'))
        self.assertFalse(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

    def test_role_default_changes_respect_user_overrides(self):
        """Changing role defaults updates INHERIT users without touching explicit ALLOW/DENY users."""
        dashboard_mod = AppModule.objects.get(code='dashboard')

        # User 1 inherits role defaults
        user1 = User.objects.create_user(username="inheritor", password="pw")
        UserProfile.objects.create(user=user1, role=self.analyst_role)

        # User 2 explicitly DENIES dashboard
        user2 = User.objects.create_user(username="denier", password="pw")
        UserProfile.objects.create(user=user2, role=self.analyst_role)
        UserPermissionOverride.objects.create(user=user2, module=dashboard_mod, view_override='DENY')

        # Check initial state: user1 can view, user2 cannot view
        self.assertTrue(has_module_perm(user1, 'dashboard', 'can_view'))
        self.assertFalse(has_module_perm(user2, 'dashboard', 'can_view'))

        # Now change Role default to can_view=False
        role_perm = RolePermission.objects.get(role=self.analyst_role, module=dashboard_mod)
        role_perm.can_view = False
        role_perm.save()

        # User 1 now inherits False
        self.assertFalse(has_module_perm(user1, 'dashboard', 'can_view'))
        # User 2 remains False due to explicit DENY
        self.assertFalse(has_module_perm(user2, 'dashboard', 'can_view'))

        # Re-enable role default to True
        role_perm.can_view = True
        role_perm.save()

        # User 1 inherits True
        self.assertTrue(has_module_perm(user1, 'dashboard', 'can_view'))
        # User 2 STILL remains False because DENY override is preserved!
        self.assertFalse(has_module_perm(user2, 'dashboard', 'can_view'))

    def test_reset_user_overrides_restores_inheritance(self):
        """Resetting user overrides restores normal role default inheritance."""
        dashboard_mod = AppModule.objects.get(code='dashboard')
        UserPermissionOverride.objects.create(
            user=self.analyst_user,
            module=dashboard_mod,
            view_override='DENY'
        )
        self.assertFalse(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

        # Reset overrides (e.g. deleting or setting to INHERIT)
        UserPermissionOverride.objects.filter(user=self.analyst_user).delete()

        # Should now inherit True from ANALYST role
        self.assertTrue(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

    def test_role_admin_user_count_no_attribute_error(self):
        """RoleAdmin changelist displays user_count without AttributeError."""
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.get(reverse('admin:core_role_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned Users")

    def test_admin_role_matrix_view_get_and_post(self):
        """Super Admin can view and save role permissions in the Django Admin matrix view."""
        self.client.login(username="superadmin", password="adminpassword123")
        url = reverse('admin:core_role_matrix', args=[self.analyst_role.pk])
        
        # GET matrix
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permissions Matrix: Analyst")

        # POST update: grant upload can_view and can_upload to Analyst
        post_data = {
            'action': 'save',
            'perm_upload_can_view': 'on',
            'perm_upload_can_upload': 'on',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        # Check that Analyst role now has upload view & upload
        upload_mod = AppModule.objects.get(code='upload')
        rp = RolePermission.objects.get(role=self.analyst_role, module=upload_mod)
        self.assertTrue(rp.can_view)
        self.assertTrue(rp.can_upload)

    def test_admin_user_matrix_view_get_post_and_reset(self):
        """Super Admin can view, override, and reset user permissions in the Django Admin matrix view."""
        self.client.login(username="superadmin", password="adminpassword123")
        url = reverse('admin:core_user_matrix', args=[self.analyst_user.pk])

        # GET user matrix
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission Overrides: analyst_user")

        # POST override: DENY dashboard view
        post_data = {
            'action_type': 'save_overrides',
            'override_dashboard_can_view': 'DENY',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        # Check effective permission
        self.assertFalse(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

        # POST reset: restores role defaults
        reset_data = {'action_type': 'reset_defaults'}
        response = self.client.post(url, reset_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

    def test_deactivated_user_cannot_login_and_has_no_perms(self):
        """Deactivated user account cannot login and returns False for all perms."""
        self.analyst_user.is_active = False
        self.analyst_user.save()

        login_success = self.client.login(username="analyst_user", password="analystpassword123")
        self.assertFalse(login_success)
        self.assertFalse(has_module_perm(self.analyst_user, 'dashboard', 'can_view'))

    def test_anonymous_user_redirected_to_login(self):
        """Unauthenticated user accessing protected dashboard is redirected to login."""
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_ordinary_user_cannot_access_rbac_views(self):
        """Non-admin user receives 403 when trying to access RBAC management views."""
        self.client.login(username="analyst_user", password="analystpassword123")
        response = self.client.get(reverse('core:rbac_dashboard'))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse('core:rbac_role_permissions', args=[self.analyst_role.pk]))
        self.assertEqual(response.status_code, 403)

    def test_superadmin_can_access_rbac_role_and_user_matrix(self):
        """Super Admin can access custom rbac_role_permissions and rbac_user_permissions views."""
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.get(reverse('core:rbac_role_permissions', args=[self.analyst_role.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('core:rbac_user_permissions', args=[self.analyst_user.pk]))
        self.assertEqual(response.status_code, 200)
