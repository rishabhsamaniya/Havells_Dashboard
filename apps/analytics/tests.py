from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files import File

from apps.core.models import MetricDefinition, AuditLog
from apps.imports.models import ImportBatch
from apps.imports.services.excel_service import ExcelImportService
from apps.analytics.models import BillingTransaction
from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.export_service import ExportService
from apps.quality.models import CategoryMapping, DataQualityIssue
from django.conf import settings

class HavellsMISValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser('testadmin', 'test@havells.local', 'password123')
        self.client.login(username='testadmin', password='password123')

        # Load reference workbook into database
        sample_path = settings.BASE_DIR / 'sample_data' / 'Havells Billing Apr to Aug-2026.xlsx'
        with open(sample_path, 'rb') as f:
            file_obj = File(f, name='Havells Billing Apr to Aug-2026.xlsx')
            file_hash = ImportBatch.calculate_file_hash(file_obj)
            self.batch = ImportBatch.objects.create(
                file_name='Havells Billing Apr to Aug-2026.xlsx',
                file_hash=file_hash,
                uploaded_file=file_obj,
                uploaded_by=self.user,
                sheet_name='Master',
                status='PENDING'
            )
            mapping = {
                'month_label': 'Months',
                'dealer_code': 'Dealer Code',
                'firm_name': 'Firm Name',
                'raw_category': 'Dine-Out/Salon/Spa/\nPhotoshoot/Concert',
                'rm': 'RM',
                'payment_spoc': 'PAYMENT SPOC',
                'billing_amount': 'Billing Amount',
                'amount_paid': 'Amount Paid',
                'story_amount': 'STORY'
            }
            success, result = ExcelImportService.process_import(
                import_batch=self.batch,
                column_mapping=mapping,
                mode='new',
                user=self.user
            )
            self.assertTrue(success)

    def test_reconciliation_exact_totals(self):
        """
        Verify that database transactions reconcile penny-for-penny with Excel
        """
        recon = AnalyticsService.get_source_reconciliation(self.batch)
        self.assertEqual(recon['excel_rows'], 923)
        self.assertEqual(recon['db_rows'], 923)
        self.assertEqual(recon['diff_rows'], 0)
        self.assertEqual(recon['diff_billing'], Decimal('0.00'))
        self.assertEqual(recon['diff_paid'], Decimal('0.00'))
        self.assertEqual(recon['diff_story'], Decimal('0.00'))
        self.assertTrue(recon['is_perfect_match'])

    def test_executive_kpis(self):
        """
        Verify Executive KPIs calculations
        """
        qs = AnalyticsService.get_filtered_queryset()
        kpis = AnalyticsService.get_executive_kpis(qs)
        self.assertEqual(kpis['total_records'], 923)
        self.assertEqual(kpis['total_billing'], Decimal('8877840.46'))
        self.assertEqual(kpis['total_paid'], Decimal('7773524.70'))
        self.assertEqual(kpis['total_story'], Decimal('1104315.76'))
        self.assertGreater(kpis['unique_dealers'], 0)
        self.assertGreater(kpis['unique_firms'], 0)

    def test_rm_sum_matches_overall_sum(self):
        """
        Verify that the sum of RM billing equals the total overall billing
        """
        qs = AnalyticsService.get_filtered_queryset()
        kpis = AnalyticsService.get_executive_kpis(qs)
        rm_data = AnalyticsService.get_rm_analytics(qs)
        rm_billing_sum = sum([r['total_billing'] for r in rm_data])
        rm_story_sum = sum([r['total_story'] for r in rm_data])
        
        self.assertEqual(rm_billing_sum, kpis['total_billing'])
        self.assertEqual(rm_story_sum, kpis['total_story'])

    def test_monthly_sum_matches_overall_sum(self):
        """
        Verify that the sum of monthly billing equals the total overall billing
        """
        qs = AnalyticsService.get_filtered_queryset()
        kpis = AnalyticsService.get_executive_kpis(qs)
        month_data = AnalyticsService.get_monthly_analytics(qs)
        m_billing_sum = sum([m['total_billing'] for m in month_data])
        m_story_sum = sum([m['total_story'] for m in month_data])

        self.assertEqual(m_billing_sum, kpis['total_billing'])
        self.assertEqual(m_story_sum, kpis['total_story'])

    def test_category_normalization_preserves_raw(self):
        """
        Verify that category normalization updates standardized_category while preserving raw_category
        """
        tx = BillingTransaction.objects.filter(raw_category__icontains='spa').first()
        if tx:
            self.assertIn('spa', tx.raw_category.lower())
            self.assertEqual(tx.standardized_category, 'Spa')

    def test_views_return_200(self):
        """
        Verify that all core dashboard and analytics views return HTTP 200
        """
        routes = [
            'analytics:dashboard',
            'analytics:rm',
            'analytics:monthly',
            'analytics:story',
            'analytics:payment',
            'analytics:category',
            'analytics:spoc',
            'analytics:dealers',
            'analytics:transactions',
            'analytics:export_centre',
            'imports:upload',
            'imports:history',
            'quality:issues',
            'quality:categories',
            'core:audit_logs',
            'core:settings',
        ]
        for r in routes:
            response = self.client.get(reverse(r))
            self.assertEqual(response.status_code, 200, f"Route {r} failed with status {response.status_code}")

    def test_export_mis_workbook(self):
        """
        Verify that the consolidated multi-tab MIS Excel report generates correctly
        """
        response = self.client.get(reverse('analytics:export_mis'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertGreater(len(response.content), 1000)
