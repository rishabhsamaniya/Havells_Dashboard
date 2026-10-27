import re
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import openpyxl
import pandas as pd
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from apps.imports.models import ImportBatch, RejectedRecord
from apps.analytics.models import BillingTransaction
from apps.quality.models import CategoryMapping, DataQualityIssue
from apps.core.models import AuditLog, MetricDefinition

CANONICAL_FIELD_CANDIDATES = {
    'month_label': ['months', 'month', 'billing month', 'month name', 'period'],
    'dealer_code': ['dealer code', 'dealercode', 'dms code', 'dealer id', 'code', 'party code'],
    'firm_name': ['firm name', 'firmname', 'agency name', 'party name', 'dealer firm name', 'company name'],
    'dealer_name': ['dealer/partner name', 'partner name', 'dealer name', 'proprietor name'],
    'raw_category': [
        'dine-out/salon/spa/\nphotoshoot/concert',
        'dine-out/salon/spa/photoshoot/concert',
        'experience category',
        'category',
        'experience',
        'service category'
    ],
    'rm': ['rm', 'relationship manager', 'rm name', 'manager'],
    'payment_spoc': ['payment spoc', 'spoc', 'payment_spoc', 'payment spoc name'],
    'billing_amount': ['billing amount', 'billingamt', 'billing', 'bill amount', 'invoice amount', 'client budget'],
    'amount_paid': ['amount paid', 'paid amount', 'amountpaid', 'payment', 'total paid'],
    'story_amount': ['story', 'story amount', 'story margin', 'story value', 'story billing'],
    'invoice_number': ['invoice number', 'invoice no', 'invoice', 'bill no', 'inv no'],
    'city_state': ['city & state', 'city / state', 'city', 'state', 'location'],
    'venue_name': ['hotel/restaurant/salon/photoshoot/Concert name', 'hotel/restaurant/salon/photoshoot/concert name', 'venue', 'vendor name', 'outlet']
}

def clean_header_name(header):
    if header is None:
        return ''
    cleaned = str(header).strip().replace('\r', ' ').replace('\n', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def parse_decimal_safe(val):
    if val is None or pd.isna(val):
        return Decimal('0.00'), None
    if isinstance(val, (int, float)):
        return Decimal(str(round(val, 2))), None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('nan', 'none', '-', 'nil', 'null'):
        return Decimal('0.00'), None
    
    # Handle accounting format negative (1,000.00)
    is_neg = False
    if val_str.startswith('(') and val_str.endswith(')'):
        is_neg = True
        val_str = val_str[1:-1]
    elif val_str.startswith('-'):
        is_neg = True
        val_str = val_str[1:]
        
    cleaned = re.sub(r'[^\d.]', '', val_str)
    try:
        dec = Decimal(cleaned)
        if is_neg:
            dec = -dec
        return dec.quantize(Decimal('0.01')), None
    except (InvalidOperation, ValueError) as e:
        return None, f"Invalid numeric format: '{val}'"

def parse_month_date(month_str):
    """
    Parses strings like Apr`26, Apr'26, Apr-26, 2026-04 into (date_obj, financial_year)
    """
    if not month_str or pd.isna(month_str):
        return None, '2026-27'
    m_clean = str(month_str).strip().replace('`', "'")
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    match = re.search(r'([A-Za-z]{3})[\'\s_-]?(\d{2,4})', m_clean)
    if match:
        m_txt = match.group(1).lower()
        yr_txt = match.group(2)
        if len(yr_txt) == 2:
            yr = 2000 + int(yr_txt)
        else:
            yr = int(yr_txt)
        m_num = month_names.get(m_txt, 4)
        try:
            d = date(yr, m_num, 1)
            # Financial year in India runs April to March
            if m_num >= 4:
                fy = f"{yr}-{str(yr+1)[-2:]}"
            else:
                fy = f"{yr-1}-{str(yr)[-2:]}"
            return d, fy
        except ValueError:
            pass
    return None, '2026-27'

def suggest_standardized_category(raw_cat):
    """
    Provides intelligent normalization suggestions while preserving original text
    """
    if not raw_cat or pd.isna(raw_cat):
        return 'Uncategorized'
    norm = str(raw_cat).strip()
    norm_lower = norm.lower().replace('-', ' ').replace('_', ' ')
    norm_lower = re.sub(r'\s+', ' ', norm_lower)
    
    if 'dine' in norm_lower:
        return 'Dine-Out'
    elif 'salon' in norm_lower:
        return 'Salon'
    elif 'spa' in norm_lower:
        return 'Spa'
    elif 'photo' in norm_lower:
        return 'Photoshoot'
    elif 'concert' in norm_lower:
        return 'Concert'
    elif 'gym' in norm_lower:
        return 'Gym'
    elif 'yoga' in norm_lower:
        return 'Yoga'
    elif 'staycation' in norm_lower:
        return 'Staycation'
    elif 'mammography' in norm_lower:
        return 'Mammography'
    elif 'health' in norm_lower:
        return 'Health Check-up'
    elif 'kids' in norm_lower:
        if 'summer' in norm_lower or 'online' in norm_lower:
            return 'Kids Online Classes'
        elif 'day out' in norm_lower:
            return 'Kids Day Out'
        return 'Kids Activity'
    return norm.title()

class ExcelImportService:
    @staticmethod
    def inspect_workbook(file_path):
        """
        Discovers worksheet names, row counts, and column headers without loading all into memory
        """
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheets = wb.sheetnames
        sheet_info = []
        for name in sheets:
            ws = wb[name]
            # Read first row for headers
            rows_iter = ws.iter_rows(values_only=True)
            first_row = next(rows_iter, None)
            headers = [clean_header_name(c) for c in (first_row or []) if c is not None]
            # Count preview rows up to 10
            sample_rows = []
            for _ in range(5):
                r = next(rows_iter, None)
                if r is not None:
                    sample_rows.append([str(c) if c is not None else '' for c in r])
            sheet_info.append({
                'name': name,
                'headers': headers,
                'sample_rows': sample_rows,
                'is_master_candidate': 'master' in name.lower() or 'working' in name.lower()
            })
        wb.close()
        return sheet_info

    @staticmethod
    def get_sheet_preview(file_path, sheet_name, max_rows=50):
        """
        Returns headers and first 50 rows for user preview & column mapping confirmation
        """
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
        headers = [clean_header_name(col) for col in df.columns]
        rows = df.fillna('').values.tolist()
        
        # Build initial auto-mapping suggestion
        mapping_suggestions = {}
        for canonical, candidates in CANONICAL_FIELD_CANDIDATES.items():
            matched_header = None
            for raw_col in df.columns:
                cleaned_col = clean_header_name(raw_col).lower()
                for cand in candidates:
                    if cand.lower() == cleaned_col or cand.lower() in cleaned_col:
                        matched_header = raw_col
                        break
                if matched_header:
                    break
            if matched_header:
                mapping_suggestions[canonical] = matched_header

        return {
            'headers': headers,
            'raw_columns': df.columns.tolist(),
            'rows': rows,
            'total_preview_rows': len(rows),
            'suggested_mapping': mapping_suggestions
        }

    @staticmethod
    def process_import(import_batch, column_mapping, mode='new', user=None):
        """
        Performs the complete import with transactional safety, duplicate detection,
        data cleaning, and anomaly logging.
        """
        file_path = import_batch.uploaded_file.path
        sheet_name = import_batch.sheet_name
        
        # Load entire sheet into pandas
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            import_batch.status = 'FAILED'
            import_batch.error_log = f"Failed to open sheet '{sheet_name}': {str(e)}"
            import_batch.save()
            return False, import_batch.error_log

        total_source_rows = len(df)
        import_batch.total_source_rows = total_source_rows
        import_batch.column_mapping = column_mapping
        import_batch.status = 'PROCESSING'
        import_batch.save()

        # Build column inverted lookup
        # column_mapping: {canonical_name: excel_column_name}
        col_lookup = {v: k for k, v in column_mapping.items() if v in df.columns}
        
        # Identify required fields
        required_fields = ['rm', 'dealer_code', 'billing_amount']
        missing_required = [rf for rf in required_fields if rf not in column_mapping or column_mapping[rf] not in df.columns]
        if missing_required:
            import_batch.status = 'FAILED'
            import_batch.error_log = f"Missing required column mappings: {', '.join(missing_required)}"
            import_batch.save()
            return False, import_batch.error_log

        # Preload category mappings cache
        cat_mappings = {cm.raw_category: cm.standardized_category for cm in CategoryMapping.objects.all()}
        new_category_mappings = []

        transactions_to_create = []
        quality_issues_to_create = []
        rejected_records_to_create = []

        successful_count = 0
        rejected_count = 0
        duplicate_count = 0
        
        total_billing = Decimal('0.00')
        total_paid = Decimal('0.00')
        total_story = Decimal('0.00')

        seen_transaction_signatures = set()

        # Check existing transactions if mode is 'new' to detect duplicate candidates across imports
        existing_signatures = set()
        if mode == 'new':
            # Fast signature check: (dealer_code, month_label, billing_amount, standardized_category)
            existing_signatures = set(
                BillingTransaction.objects.filter(import_batch__is_active=True)
                .values_list('dealer_code', 'month_label', 'billing_amount', 'standardized_category')
            )

        with transaction.atomic():
            # If mode == 'replace', soft-deactivate previous active batches for this file or user choice
            if mode == 'replace':
                ImportBatch.objects.filter(
                    file_hash=import_batch.file_hash,
                    is_active=True
                ).exclude(id=import_batch.id).update(is_active=False, status='REPLACED')

            for index, row in df.iterrows():
                row_num = index + 2  # Excel row (1-indexed header is row 1)
                row_dict = row.to_dict()
                # Clean nulls in dict for json
                json_safe_row = {clean_header_name(k): (None if pd.isna(v) else str(v)) for k, v in row_dict.items()}

                # Extract mapped fields
                def get_val(canonical):
                    col_name = column_mapping.get(canonical)
                    if col_name and col_name in row_dict and not pd.isna(row_dict[col_name]):
                        return row_dict[col_name]
                    return None

                # 1. Validate RM and Dealer Code
                rm_val = str(get_val('rm') or '').strip()
                dealer_code_val = str(get_val('dealer_code') or '').strip()
                firm_name_val = str(get_val('firm_name') or '').strip()
                month_label_val = str(get_val('month_label') or '').strip()
                raw_cat_val = str(get_val('raw_category') or '').strip()
                spoc_val = str(get_val('payment_spoc') or '').strip()

                if not rm_val or not dealer_code_val:
                    rejection_reason = "Missing mandatory identifier: "
                    missing = []
                    if not rm_val: missing.append("RM")
                    if not dealer_code_val: missing.append("Dealer Code")
                    rejection_reason += ", ".join(missing)
                    rejected_records_to_create.append(RejectedRecord(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        raw_data=json_safe_row,
                        rejection_reason=rejection_reason
                    ))
                    rejected_count += 1
                    continue

                # 2. Parse Numeric Fields
                billing_dec, b_err = parse_decimal_safe(get_val('billing_amount'))
                paid_dec, p_err = parse_decimal_safe(get_val('amount_paid'))
                story_dec, s_err = parse_decimal_safe(get_val('story_amount'))

                if b_err or p_err or s_err:
                    err_msg = b_err or p_err or s_err
                    rejected_records_to_create.append(RejectedRecord(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        raw_data=json_safe_row,
                        rejection_reason=f"Numeric parsing error: {err_msg}"
                    ))
                    rejected_count += 1
                    continue

                # Handle date & financial year
                trans_date, fy = parse_month_date(month_label_val)

                # Standardize category
                if raw_cat_val in cat_mappings:
                    std_category = cat_mappings[raw_cat_val]
                else:
                    std_category = suggest_standardized_category(raw_cat_val)
                    cat_mappings[raw_cat_val] = std_category
                    new_category_mappings.append(CategoryMapping(
                        raw_category=raw_cat_val,
                        standardized_category=std_category,
                        is_reviewed=False
                    ))

                # Check for in-batch or historical duplicate candidate
                sig = (dealer_code_val, month_label_val, billing_dec, std_category)
                is_duplicate = False
                if sig in seen_transaction_signatures or (mode == 'new' and sig in existing_signatures):
                    duplicate_count += 1
                    is_duplicate = True
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="Dealer Code / Month / Amount",
                        original_value=f"{dealer_code_val} | {month_label_val} | ₹{billing_dec}",
                        issue_type="POTENTIAL_DUPLICATE",
                        severity="HIGH",
                        description=f"Duplicate candidate: Dealer {dealer_code_val} already billed for ₹{billing_dec:,.2f} under {std_category} in {month_label_val}"
                    ))
                seen_transaction_signatures.add(sig)

                # Anomaly Checks:
                # Negative Billing
                if billing_dec < 0:
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="Billing Amount",
                        original_value=str(billing_dec),
                        issue_type="BUSINESS_EXCEPTION",
                        severity="HIGH",
                        description=f"Negative billing amount ₹{billing_dec:,.2f} detected"
                    ))

                # Negative STORY
                if story_dec < 0:
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="STORY",
                        original_value=str(story_dec),
                        issue_type="WARNING",
                        severity="MEDIUM",
                        description=f"Negative STORY amount ₹{story_dec:,.2f} recorded (Requires business review)"
                    ))
                elif story_dec == 0 and billing_dec > 0:
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="STORY",
                        original_value="0.00",
                        issue_type="WARNING",
                        severity="LOW",
                        description="Zero STORY amount on a non-zero billing record"
                    ))

                # Discrepancy between (Billing - Paid) and STORY
                calculated_diff = billing_dec - paid_dec
                if abs(calculated_diff - story_dec) > Decimal('0.05'):
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="STORY vs Difference",
                        original_value=f"STORY={story_dec}, Diff={calculated_diff}",
                        issue_type="BUSINESS_EXCEPTION",
                        severity="MEDIUM",
                        description=f"STORY (₹{story_dec:,.2f}) differs from Billing - Paid (₹{calculated_diff:,.2f})"
                    ))

                # High Outlier Billing
                if billing_dec > Decimal('50000.00'):
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="Billing Amount",
                        original_value=str(billing_dec),
                        issue_type="WARNING",
                        severity="LOW",
                        description=f"High outlier billing amount: ₹{billing_dec:,.2f}"
                    ))

                # Missing Payment SPOC
                if not spoc_val:
                    quality_issues_to_create.append(DataQualityIssue(
                        import_batch=import_batch,
                        source_row_number=row_num,
                        field_name="PAYMENT SPOC",
                        original_value=None,
                        issue_type="WARNING",
                        severity="LOW",
                        description="Payment SPOC is blank"
                    ))

                # Create Transaction Object
                tx = BillingTransaction(
                    import_batch=import_batch,
                    source_row_number=row_num,
                    month_label=month_label_val,
                    transaction_date=trans_date,
                    financial_year=fy,
                    rm=rm_val,
                    dealer_code=dealer_code_val,
                    firm_name=firm_name_val or dealer_code_val,
                    dealer_name=str(get_val('dealer_name') or ''),
                    raw_category=raw_cat_val,
                    standardized_category=std_category,
                    payment_spoc=spoc_val or 'Unassigned',
                    billing_amount=billing_dec,
                    amount_paid=paid_dec,
                    story_amount=story_dec,
                    calculated_difference=calculated_diff,
                    invoice_number=str(get_val('invoice_number') or ''),
                    city_state=str(get_val('city_state') or ''),
                    venue_name=str(get_val('venue_name') or ''),
                    raw_source_data=json_safe_row,
                    is_flagged=is_duplicate or (billing_dec < 0) or (story_dec < 0)
                )
                transactions_to_create.append(tx)
                successful_count += 1
                total_billing += billing_dec
                total_paid += paid_dec
                total_story += story_dec

            # Bulk save category mappings if any new ones
            if new_category_mappings:
                CategoryMapping.objects.bulk_create(new_category_mappings, ignore_conflicts=True)

            # Bulk create transactions
            BillingTransaction.objects.bulk_create(transactions_to_create, batch_size=500)

            # Bulk create rejected records
            if rejected_records_to_create:
                RejectedRecord.objects.bulk_create(rejected_records_to_create, batch_size=500)

            # Bulk create quality issues
            if quality_issues_to_create:
                DataQualityIssue.objects.bulk_create(quality_issues_to_create, batch_size=500)

            # Update ImportBatch details
            import_batch.successful_records = successful_count
            import_batch.rejected_records = rejected_count
            import_batch.duplicate_records = duplicate_count
            import_batch.total_billing_amount = total_billing
            import_batch.total_paid_amount = total_paid
            import_batch.total_story_amount = total_story
            import_batch.status = 'COMPLETED'
            import_batch.save()

            # Record Audit Log
            AuditLog.objects.create(
                action='IMPORT',
                model_name='ImportBatch',
                object_id=str(import_batch.id),
                user=user,
                details={
                    'file_name': import_batch.file_name,
                    'sheet_name': import_batch.sheet_name,
                    'successful_records': successful_count,
                    'rejected_records': rejected_count,
                    'duplicate_records': duplicate_count,
                    'total_billing': float(total_billing),
                    'total_story': float(total_story),
                    'mode': mode
                }
            )

        return True, {
            'successful_records': successful_count,
            'rejected_records': rejected_count,
            'duplicate_records': duplicate_count,
            'total_billing': total_billing,
            'total_paid': total_paid,
            'total_story': total_story,
        }
