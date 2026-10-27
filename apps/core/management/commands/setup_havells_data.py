import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files import File

from apps.core.models import MetricDefinition, MonthlyRMTarget
from apps.imports.models import ImportBatch
from apps.imports.services.excel_service import ExcelImportService
from apps.analytics.services.analytics_service import AnalyticsService

class Command(BaseCommand):
    help = 'Sets up default superuser, metrics, and imports the reference Havells Excel workbook'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing Havells Billing Intelligence system..."))

        # 1. Superuser
        admin_user, created = User.objects.get_or_create(username='admin')
        if created:
            admin_user.set_password('admin123')
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.email = 'admin@havells-mis.local'
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created default superuser: admin / admin123"))
        else:
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' already exists."))

        # 2. Metric Definition
        metric, m_created = MetricDefinition.objects.get_or_create(
            code='STORY_DEFINITION',
            defaults={
                'name': 'STORY Margin Definition',
                'description': 'Preserves the dedicated STORY column from the source Excel file as the source of truth.',
                'formula_type': 'SOURCE_COLUMN',
                'notes': 'Dedicated STORY column is preserved as the source of truth. Not automatically hardcoded as Billing minus Paid.'
            }
        )
        if m_created:
            self.stdout.write(self.style.SUCCESS("Initialized default STORY Metric Definition."))

        # 3. Reference Excel File Import
        from django.conf import settings
        sample_path = settings.BASE_DIR / 'sample_data' / 'Havells Billing Apr to Aug-2026.xlsx'

        if not sample_path.exists():
            self.stdout.write(self.style.WARNING(f"Reference file not found at: {sample_path}"))
            return

        with open(sample_path, 'rb') as f:
            file_obj = File(f, name='Havells Billing Apr to Aug-2026.xlsx')
            file_hash = ImportBatch.calculate_file_hash(file_obj)

            # Check if already imported
            existing = ImportBatch.objects.filter(file_hash=file_hash, status='COMPLETED').first()
            if existing:
                self.stdout.write(self.style.WARNING(f"Reference workbook already imported in Batch #{existing.id}."))
                batch = existing
            else:
                self.stdout.write(self.style.NOTICE(f"Importing reference file: {sample_path.name}..."))
                batch = ImportBatch.objects.create(
                    file_name='Havells Billing Apr to Aug-2026.xlsx',
                    file_hash=file_hash,
                    uploaded_file=file_obj,
                    uploaded_by=admin_user,
                    sheet_name='Master',
                    status='PENDING'
                )

                # Canonical mapping for Master sheet
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
                    import_batch=batch,
                    column_mapping=mapping,
                    mode='new',
                    user=admin_user
                )

                if success:
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully imported {result['successful_records']} records! "
                        f"Total Billing: ₹{result['total_billing']:,.2f}, Total STORY: ₹{result['total_story']:,.2f}"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(f"Import failed: {result}"))
                    return

        # 4. Source Reconciliation Verification
        recon = AnalyticsService.get_source_reconciliation(batch)
        self.stdout.write(self.style.NOTICE("\n--- SOURCE RECONCILIATION SUMMARY ---"))
        self.stdout.write(f"Excel Rows: {recon['excel_rows']} | DB Transactions: {recon['db_rows']} | Diff: {recon['diff_rows']}")
        self.stdout.write(f"Excel Billing: ₹{recon['excel_billing']:,.2f} | DB Billing: ₹{recon['db_billing']:,.2f} | Diff: ₹{recon['diff_billing']:,.2f}")
        self.stdout.write(f"Excel Paid: ₹{recon['excel_paid']:,.2f} | DB Paid: ₹{recon['db_paid']:,.2f} | Diff: ₹{recon['diff_paid']:,.2f}")
        self.stdout.write(f"Excel STORY: ₹{recon['excel_story']:,.2f} | DB STORY: ₹{recon['db_story']:,.2f} | Diff: ₹{recon['diff_story']:,.2f}")
        if recon['is_perfect_match']:
            self.stdout.write(self.style.SUCCESS("PERFECT MATCH: All financial metrics and row counts reconcile to the penny!"))
        else:
            self.stdout.write(self.style.WARNING("Reconciliation variance detected."))
