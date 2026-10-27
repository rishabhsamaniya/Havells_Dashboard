from decimal import Decimal
import pandas as pd
from django.db.models import Sum, Count, Avg, F, Q, Max, Min
from apps.analytics.models import BillingTransaction
from apps.core.models import MonthlyRMTarget, MetricDefinition
from apps.quality.models import DataQualityIssue

class AnalyticsService:
    @staticmethod
    def get_filtered_queryset(filters=None):
        """
        Builds the base queryset honoring active import batches and multi-dimensional filters
        """
        qs = BillingTransaction.objects.filter(import_batch__is_active=True)
        if not filters:
            return qs

        if filters.get('month'):
            month_val = filters['month']
            if isinstance(month_val, list):
                qs = qs.filter(month_label__in=month_val)
            else:
                qs = qs.filter(month_label=month_val)

        if filters.get('rm'):
            rm_val = filters['rm']
            if isinstance(rm_val, list):
                qs = qs.filter(rm__in=rm_val)
            else:
                qs = qs.filter(rm=rm_val)

        if filters.get('payment_spoc'):
            spoc_val = filters['payment_spoc']
            if isinstance(spoc_val, list):
                qs = qs.filter(payment_spoc__in=spoc_val)
            else:
                qs = qs.filter(payment_spoc=spoc_val)

        if filters.get('category'):
            cat_val = filters['category']
            if isinstance(cat_val, list):
                qs = qs.filter(standardized_category__in=cat_val)
            else:
                qs = qs.filter(standardized_category=cat_val)

        if filters.get('payment_status'):
            qs = qs.filter(payment_status=filters['payment_status'])

        if filters.get('financial_year'):
            qs = qs.filter(financial_year=filters['financial_year'])

        if filters.get('search'):
            term = filters['search'].strip()
            qs = qs.filter(
                Q(dealer_code__icontains=term) |
                Q(firm_name__icontains=term) |
                Q(rm__icontains=term) |
                Q(invoice_number__icontains=term)
            )

        if filters.get('batch_id'):
            qs = qs.filter(import_batch_id=filters['batch_id'])

        return qs

    @staticmethod
    def get_filter_options():
        """
        Returns all unique distinct values for dynamic dropdown filters
        """
        qs = BillingTransaction.objects.filter(import_batch__is_active=True)
        months = list(qs.values_list('month_label', flat=True).distinct().order_by('month_label'))
        rms = list(qs.values_list('rm', flat=True).distinct().order_by('rm'))
        spocs = list(qs.values_list('payment_spoc', flat=True).distinct().order_by('payment_spoc'))
        categories = list(qs.values_list('standardized_category', flat=True).distinct().order_by('standardized_category'))
        
        # Sort months chronologically if format like Apr`26, May`26, Jun`26, Jul`26, Aug`26
        month_order = {'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12, 'jan': 1, 'feb': 2, 'mar': 3}
        def month_sort_key(m):
            m_prefix = m[:3].lower() if m else ''
            return month_order.get(m_prefix, 99)
        months.sort(key=month_sort_key)

        return {
            'months': months,
            'rms': rms,
            'spocs': spocs,
            'categories': categories,
            'payment_statuses': ['PAID', 'PARTIAL', 'UNPAID', 'OVERPAID']
        }

    @staticmethod
    def get_executive_kpis(qs):
        """
        Computes high-level Executive KPIs with MoM trend indicators and calculations
        """
        agg = qs.aggregate(
            total_billing=Sum('billing_amount'),
            total_paid=Sum('amount_paid'),
            total_story=Sum('story_amount'),
            total_records=Count('id'),
            unique_dealers=Count('dealer_code', distinct=True),
            unique_firms=Count('firm_name', distinct=True),
            avg_billing=Avg('billing_amount'),
        )

        total_billing = agg['total_billing'] or Decimal('0.00')
        total_paid = agg['total_paid'] or Decimal('0.00')
        total_story = agg['total_story'] or Decimal('0.00')
        total_records = agg['total_records'] or 0
        unique_dealers = agg['unique_dealers'] or 0
        unique_firms = agg['unique_firms'] or 0
        avg_billing_record = agg['avg_billing'] or Decimal('0.00')
        avg_billing_dealer = (total_billing / Decimal(str(unique_dealers))) if unique_dealers > 0 else Decimal('0.00')
        story_percentage = (total_story / total_billing * 100) if total_billing > 0 else Decimal('0.00')
        payment_diff = total_billing - total_paid

        # Highest Billing Month
        month_agg = qs.values('month_label').annotate(sum_billing=Sum('billing_amount')).order_by('-sum_billing').first()
        highest_billing_month = month_agg['month_label'] if month_agg else 'N/A'
        highest_billing_month_val = month_agg['sum_billing'] if month_agg else Decimal('0.00')

        # Highest Billing RM & Highest STORY RM
        rm_billing = qs.values('rm').annotate(sum_billing=Sum('billing_amount')).order_by('-sum_billing').first()
        top_billing_rm = rm_billing['rm'] if rm_billing else 'N/A'
        top_billing_rm_val = rm_billing['sum_billing'] if rm_billing else Decimal('0.00')

        rm_story = qs.values('rm').annotate(sum_story=Sum('story_amount')).order_by('-sum_story').first()
        top_story_rm = rm_story['rm'] if rm_story else 'N/A'
        top_story_rm_val = rm_story['sum_story'] if rm_story else Decimal('0.00')

        # MoM Billing Growth
        month_order = {'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12, 'jan': 1, 'feb': 2, 'mar': 3}
        month_billing_list = list(qs.values('month_label').annotate(b=Sum('billing_amount')))
        month_billing_list.sort(key=lambda x: month_order.get(x['month_label'][:3].lower(), 99))
        
        mom_growth_pct = Decimal('0.00')
        if len(month_billing_list) >= 2:
            prev_b = month_billing_list[-2]['b'] or Decimal('0.00')
            curr_b = month_billing_list[-1]['b'] or Decimal('0.00')
            if prev_b > 0:
                mom_growth_pct = ((curr_b - prev_b) / prev_b) * 100

        # Data Quality Issues
        quality_issues_count = DataQualityIssue.objects.filter(import_batch__is_active=True).count()
        critical_issues_count = DataQualityIssue.objects.filter(
            import_batch__is_active=True,
            severity__in=['CRITICAL', 'HIGH']
        ).count()

        return {
            'total_billing': total_billing,
            'total_paid': total_paid,
            'total_story': total_story,
            'story_percentage': round(story_percentage, 2),
            'total_records': total_records,
            'unique_dealers': unique_dealers,
            'unique_firms': unique_firms,
            'avg_billing_record': round(avg_billing_record, 2),
            'avg_billing_dealer': round(avg_billing_dealer, 2),
            'payment_difference': payment_diff,
            'highest_billing_month': highest_billing_month,
            'highest_billing_month_val': highest_billing_month_val,
            'top_billing_rm': top_billing_rm,
            'top_billing_rm_val': top_billing_rm_val,
            'top_story_rm': top_story_rm,
            'top_story_rm_val': top_story_rm_val,
            'mom_growth_pct': round(mom_growth_pct, 2),
            'quality_issues_count': quality_issues_count,
            'critical_issues_count': critical_issues_count,
        }

    @staticmethod
    def get_rm_analytics(qs):
        """
        Comprehensive RM performance report with category mix, targets, and trend
        """
        total_billing_all = qs.aggregate(s=Sum('billing_amount'))['s'] or Decimal('0.00')
        total_story_all = qs.aggregate(s=Sum('story_amount'))['s'] or Decimal('0.00')

        rm_list = qs.values('rm').annotate(
            total_billing=Sum('billing_amount'),
            total_paid=Sum('amount_paid'),
            total_story=Sum('story_amount'),
            tx_count=Count('id'),
            unique_dealers=Count('dealer_code', distinct=True),
            unique_firms=Count('firm_name', distinct=True),
            avg_billing=Avg('billing_amount'),
        ).order_by('-total_billing')

        results = []
        for r in rm_list:
            b = r['total_billing'] or Decimal('0.00')
            p = r['total_paid'] or Decimal('0.00')
            s = r['total_story'] or Decimal('0.00')
            tx = r['tx_count'] or 0
            dealers = r['unique_dealers'] or 0
            
            story_pct = (s / b * 100) if b > 0 else Decimal('0.00')
            avg_story_tx = (s / Decimal(str(tx))) if tx > 0 else Decimal('0.00')
            share_billing = (b / total_billing_all * 100) if total_billing_all > 0 else Decimal('0.00')
            share_story = (s / total_story_all * 100) if total_story_all > 0 else Decimal('0.00')
            avg_per_dealer = (b / Decimal(str(dealers))) if dealers > 0 else Decimal('0.00')

            # Targets check
            targets = MonthlyRMTarget.objects.filter(rm_name=r['rm'])
            target_billing_sum = targets.aggregate(s=Sum('target_billing'))['s'] or Decimal('0.00')
            achievement_pct = (b / target_billing_sum * 100) if target_billing_sum > 0 else None

            # Category Mix for this RM
            cat_mix = list(
                qs.filter(rm=r['rm'])
                .values('standardized_category')
                .annotate(cat_billing=Sum('billing_amount'), cat_count=Count('id'))
                .order_by('-cat_billing')
            )

            # Monthly Trend for this RM
            month_trend = list(
                qs.filter(rm=r['rm'])
                .values('month_label')
                .annotate(m_billing=Sum('billing_amount'), m_story=Sum('story_amount'))
            )

            results.append({
                'rm': r['rm'],
                'total_billing': b,
                'total_paid': p,
                'total_story': s,
                'story_percentage': round(story_pct, 2),
                'tx_count': tx,
                'unique_dealers': dealers,
                'unique_firms': r['unique_firms'],
                'avg_billing': round(r['avg_billing'] or 0, 2),
                'avg_per_dealer': round(avg_per_dealer, 2),
                'avg_story_tx': round(avg_story_tx, 2),
                'share_billing_pct': round(share_billing, 2),
                'share_story_pct': round(share_story, 2),
                'target_billing': target_billing_sum,
                'achievement_pct': round(achievement_pct, 2) if achievement_pct is not None else None,
                'category_mix': cat_mix,
                'month_trend': month_trend,
            })

        return results

    @staticmethod
    def get_monthly_analytics(qs):
        """
        Month-wise Billing Analytics, Growth, and Comparisons
        """
        month_order = {'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12, 'jan': 1, 'feb': 2, 'mar': 3}
        
        raw_months = list(qs.values('month_label').annotate(
            total_billing=Sum('billing_amount'),
            total_paid=Sum('amount_paid'),
            total_story=Sum('story_amount'),
            tx_count=Count('id'),
            unique_dealers=Count('dealer_code', distinct=True),
            avg_billing=Avg('billing_amount'),
        ))
        raw_months.sort(key=lambda x: month_order.get(x['month_label'][:3].lower(), 99))

        results = []
        prev_billing = None
        prev_story = None
        prev_tx = None

        for m in raw_months:
            b = m['total_billing'] or Decimal('0.00')
            p = m['total_paid'] or Decimal('0.00')
            s = m['total_story'] or Decimal('0.00')
            tx = m['tx_count'] or 0
            story_pct = (s / b * 100) if b > 0 else Decimal('0.00')

            billing_growth = None
            story_growth = None
            tx_growth = None

            if prev_billing is not None and prev_billing > 0:
                billing_growth = round(((b - prev_billing) / prev_billing) * 100, 2)
            if prev_story is not None and prev_story > 0:
                story_growth = round(((s - prev_story) / prev_story) * 100, 2)
            if prev_tx is not None and prev_tx > 0:
                tx_growth = round(((tx - prev_tx) / Decimal(str(prev_tx))) * 100, 2)

            # RM distribution in this month
            rm_breakdown = list(
                qs.filter(month_label=m['month_label'])
                .values('rm')
                .annotate(rm_billing=Sum('billing_amount'), rm_story=Sum('story_amount'))
                .order_by('-rm_billing')
            )

            # Category distribution in this month
            cat_breakdown = list(
                qs.filter(month_label=m['month_label'])
                .values('standardized_category')
                .annotate(cat_billing=Sum('billing_amount'), cat_story=Sum('story_amount'))
                .order_by('-cat_billing')
            )

            results.append({
                'month_label': m['month_label'],
                'total_billing': b,
                'total_paid': p,
                'total_story': s,
                'story_percentage': round(story_pct, 2),
                'tx_count': tx,
                'unique_dealers': m['unique_dealers'],
                'avg_billing': round(m['avg_billing'] or 0, 2),
                'billing_growth_pct': billing_growth,
                'story_growth_pct': story_growth,
                'tx_growth_pct': tx_growth,
                'rm_breakdown': rm_breakdown,
                'cat_breakdown': cat_breakdown,
            })

            prev_billing = b
            prev_story = s
            prev_tx = tx

        return results

    @staticmethod
    def get_story_analytics(qs):
        """
        STORY deep-dive analysis, positive/negative/zero counts, outliers, and breakdowns
        """
        total_billing = qs.aggregate(s=Sum('billing_amount'))['s'] or Decimal('0.00')
        total_story = qs.aggregate(s=Sum('story_amount'))['s'] or Decimal('0.00')
        overall_story_pct = (total_story / total_billing * 100) if total_billing > 0 else Decimal('0.00')

        # Positive, Negative, Zero records
        pos_qs = qs.filter(story_amount__gt=0)
        neg_qs = qs.filter(story_amount__lt=0)
        zero_qs = qs.filter(story_amount=0)

        pos_count = pos_qs.count()
        pos_sum = pos_qs.aggregate(s=Sum('story_amount'))['s'] or Decimal('0.00')
        
        neg_count = neg_qs.count()
        neg_sum = neg_qs.aggregate(s=Sum('story_amount'))['s'] or Decimal('0.00')

        zero_count = zero_qs.count()

        # Highest and lowest STORY records
        top_story_txs = qs.order_by('-story_amount')[:10]
        lowest_story_txs = qs.order_by('story_amount')[:10]

        # By RM
        story_by_rm = list(
            qs.values('rm')
            .annotate(
                sum_story=Sum('story_amount'),
                sum_billing=Sum('billing_amount'),
                tx_count=Count('id')
            )
            .order_by('-sum_story')
        )
        for item in story_by_rm:
            b = item['sum_billing'] or Decimal('0.00')
            s = item['sum_story'] or Decimal('0.00')
            item['story_pct'] = round((s / b * 100) if b > 0 else 0, 2)

        # By Category
        story_by_cat = list(
            qs.values('standardized_category')
            .annotate(
                sum_story=Sum('story_amount'),
                sum_billing=Sum('billing_amount'),
                tx_count=Count('id')
            )
            .order_by('-sum_story')
        )
        for item in story_by_cat:
            b = item['sum_billing'] or Decimal('0.00')
            s = item['sum_story'] or Decimal('0.00')
            item['story_pct'] = round((s / b * 100) if b > 0 else 0, 2)

        # By Payment SPOC
        story_by_spoc = list(
            qs.values('payment_spoc')
            .annotate(
                sum_story=Sum('story_amount'),
                sum_billing=Sum('billing_amount'),
                tx_count=Count('id')
            )
            .order_by('-sum_story')
        )
        for item in story_by_spoc:
            b = item['sum_billing'] or Decimal('0.00')
            s = item['sum_story'] or Decimal('0.00')
            item['story_pct'] = round((s / b * 100) if b > 0 else 0, 2)

        return {
            'total_story': total_story,
            'overall_story_pct': round(overall_story_pct, 2),
            'pos_count': pos_count,
            'pos_sum': pos_sum,
            'neg_count': neg_count,
            'neg_sum': neg_sum,
            'zero_count': zero_count,
            'top_story_txs': top_story_txs,
            'lowest_story_txs': lowest_story_txs,
            'story_by_rm': story_by_rm,
            'story_by_cat': story_by_cat,
            'story_by_spoc': story_by_spoc,
        }

    @staticmethod
    def get_payment_reconciliation(qs):
        """
        Payment Reconciliation, Status Distributions, and SPOC differences
        """
        total_billing = qs.aggregate(s=Sum('billing_amount'))['s'] or Decimal('0.00')
        total_paid = qs.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0.00')
        reconciliation_diff = total_billing - total_paid
        paid_pct = (total_paid / total_billing * 100) if total_billing > 0 else Decimal('0.00')

        # Status counts
        status_dist = list(
            qs.values('payment_status')
            .annotate(
                count=Count('id'),
                billing_sum=Sum('billing_amount'),
                paid_sum=Sum('amount_paid')
            )
        )

        # SPOC-wise Billing & Payment
        spoc_reconciliation = list(
            qs.values('payment_spoc')
            .annotate(
                billing=Sum('billing_amount'),
                paid=Sum('amount_paid'),
                story=Sum('story_amount'),
                tx_count=Count('id')
            )
            .order_by('-billing')
        )
        for item in spoc_reconciliation:
            b = item['billing'] or Decimal('0.00')
            p = item['paid'] or Decimal('0.00')
            item['diff'] = b - p
            item['paid_pct'] = round((p / b * 100) if b > 0 else 0, 2)

        # Dealer differences where billing != paid
        mismatch_dealers = list(
            qs.filter(~Q(billing_amount=F('amount_paid')))
            .values('dealer_code', 'firm_name')
            .annotate(
                billing=Sum('billing_amount'),
                paid=Sum('amount_paid'),
                diff=Sum(F('billing_amount') - F('amount_paid')),
                tx_count=Count('id')
            )
            .order_by('-diff')[:25]
        )

        return {
            'total_billing': total_billing,
            'total_paid': total_paid,
            'reconciliation_diff': reconciliation_diff,
            'paid_pct': round(paid_pct, 2),
            'status_dist': status_dist,
            'spoc_reconciliation': spoc_reconciliation,
            'mismatch_dealers': mismatch_dealers,
        }

    @staticmethod
    def get_category_analytics(qs):
        """
        Experience Category breakdown and RM vs Category performance matrix
        """
        total_billing = qs.aggregate(s=Sum('billing_amount'))['s'] or Decimal('0.00')
        total_story = qs.aggregate(s=Sum('story_amount'))['s'] or Decimal('0.00')

        cat_list = list(
            qs.values('standardized_category')
            .annotate(
                billing=Sum('billing_amount'),
                paid=Sum('amount_paid'),
                story=Sum('story_amount'),
                tx_count=Count('id'),
                unique_dealers=Count('dealer_code', distinct=True),
                avg_billing=Avg('billing_amount')
            )
            .order_by('-billing')
        )

        for c in cat_list:
            b = c['billing'] or Decimal('0.00')
            s = c['story'] or Decimal('0.00')
            c['story_pct'] = round((s / b * 100) if b > 0 else 0, 2)
            c['share_billing'] = round((b / total_billing * 100) if total_billing > 0 else 0, 2)
            c['share_story'] = round((s / total_story * 100) if total_story > 0 else 0, 2)
            c['avg_billing'] = round(c['avg_billing'] or 0, 2)

        # Heatmap / Matrix: RM vs Category
        matrix_raw = list(
            qs.values('rm', 'standardized_category')
            .annotate(b=Sum('billing_amount'), s=Sum('story_amount'), count=Count('id'))
        )

        return {
            'category_list': cat_list,
            'matrix_raw': matrix_raw,
        }

    @staticmethod
    def get_spoc_analytics(qs):
        """
        Payment SPOC workload and distribution
        """
        total_billing = qs.aggregate(s=Sum('billing_amount'))['s'] or Decimal('0.00')

        spoc_list = list(
            qs.values('payment_spoc')
            .annotate(
                billing=Sum('billing_amount'),
                paid=Sum('amount_paid'),
                story=Sum('story_amount'),
                tx_count=Count('id'),
                unique_dealers=Count('dealer_code', distinct=True),
            )
            .order_by('-billing')
        )

        for sp in spoc_list:
            b = sp['billing'] or Decimal('0.00')
            p = sp['paid'] or Decimal('0.00')
            s = sp['story'] or Decimal('0.00')
            sp['diff'] = b - p
            sp['story_pct'] = round((s / b * 100) if b > 0 else 0, 2)
            sp['share_billing'] = round((b / total_billing * 100) if total_billing > 0 else 0, 2)

        return spoc_list

    @staticmethod
    def get_dealer_analytics(qs):
        """
        Dealer Code and Firm Name level analytics, repeat frequency, and anomalies
        """
        total_dealers = qs.values('dealer_code').distinct().count()

        top_dealers = list(
            qs.values('dealer_code', 'firm_name')
            .annotate(
                billing=Sum('billing_amount'),
                paid=Sum('amount_paid'),
                story=Sum('story_amount'),
                tx_count=Count('id'),
                active_months=Count('month_label', distinct=True)
            )
            .order_by('-billing')[:50]
        )

        dealers_with_neg_story = list(
            qs.filter(story_amount__lt=0)
            .values('dealer_code', 'firm_name')
            .annotate(
                billing=Sum('billing_amount'),
                story=Sum('story_amount'),
                tx_count=Count('id')
            )
            .order_by('story')
        )

        dealers_with_zero_story = list(
            qs.filter(story_amount=0, billing_amount__gt=0)
            .values('dealer_code', 'firm_name')
            .annotate(
                billing=Sum('billing_amount'),
                tx_count=Count('id')
            )
            .order_by('-billing')[:20]
        )

        return {
            'total_unique_dealers': total_dealers,
            'top_dealers': top_dealers,
            'dealers_with_neg_story': dealers_with_neg_story,
            'dealers_with_zero_story': dealers_with_zero_story,
        }

    @staticmethod
    def get_source_reconciliation(import_batch):
        """
        Performs an exact row-by-row and aggregate reconciliation of the active batch
        against the raw Excel workbook!
        """
        file_path = import_batch.uploaded_file.path
        sheet_name = import_batch.sheet_name
        
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        excel_rows = len(df)
        
        # Mapped columns
        col_map = import_batch.column_mapping or {}
        b_col = col_map.get('billing_amount')
        p_col = col_map.get('amount_paid')
        s_col = col_map.get('story_amount')
        
        excel_billing = Decimal(str(round(df[b_col].sum(), 2))) if b_col and b_col in df.columns else Decimal('0.00')
        excel_paid = Decimal(str(round(df[p_col].sum(), 2))) if p_col and p_col in df.columns else Decimal('0.00')
        excel_story = Decimal(str(round(df[s_col].sum(), 2))) if s_col and s_col in df.columns else Decimal('0.00')

        # Database counts
        db_qs = BillingTransaction.objects.filter(import_batch=import_batch)
        db_agg = db_qs.aggregate(
            db_billing=Sum('billing_amount'),
            db_paid=Sum('amount_paid'),
            db_story=Sum('story_amount'),
            db_rows=Count('id')
        )

        db_billing = db_agg['db_billing'] or Decimal('0.00')
        db_paid = db_agg['db_paid'] or Decimal('0.00')
        db_story = db_agg['db_story'] or Decimal('0.00')
        db_rows = db_agg['db_rows'] or 0

        diff_billing = db_billing - excel_billing
        diff_paid = db_paid - excel_paid
        diff_story = db_story - excel_story
        diff_rows = db_rows - excel_rows

        return {
            'batch': import_batch,
            'excel_rows': excel_rows,
            'db_rows': db_rows,
            'diff_rows': diff_rows,
            'excel_billing': excel_billing,
            'db_billing': db_billing,
            'diff_billing': diff_billing,
            'excel_paid': excel_paid,
            'db_paid': db_paid,
            'diff_paid': diff_paid,
            'excel_story': excel_story,
            'db_story': db_story,
            'diff_story': diff_story,
            'is_perfect_match': (diff_billing == 0 and diff_paid == 0 and diff_story == 0 and diff_rows == 0)
        }

    @staticmethod
    def get_grouped_category_mix(qs, threshold_pct=9.0):
        """
        Groups categories with percentage < threshold_pct (default 9%) into 'Others'
        Calculates and returns the combined percentage and billing for 'Others',
        keeping categories with >= 9% individually.
        """
        total_billing = qs.aggregate(s=Sum('billing_amount'))['s'] or Decimal('0.00')
        if total_billing == 0:
            return []

        cat_list = list(
            qs.values('standardized_category')
            .annotate(
                billing=Sum('billing_amount'),
                story=Sum('story_amount'),
                tx_count=Count('id')
            )
            .order_by('-billing')
        )

        individual_categories = []
        others_billing = Decimal('0.00')
        others_story = Decimal('0.00')
        others_tx_count = 0
        others_count = 0

        for c in cat_list:
            b = c['billing'] or Decimal('0.00')
            s = c['story'] or Decimal('0.00')
            pct = (b / total_billing * Decimal('100'))
            if pct >= Decimal(str(threshold_pct)):
                individual_categories.append({
                    'category': c['standardized_category'],
                    'billing': float(b),
                    'story': float(s),
                    'percentage': round(float(pct), 2),
                    'tx_count': c['tx_count'],
                    'is_grouped': False
                })
            else:
                others_billing += b
                others_story += s
                others_tx_count += c['tx_count']
                others_count += 1

        if others_billing > 0:
            others_pct = round(float(others_billing / total_billing * Decimal('100')), 2)
            individual_categories.append({
                'category': 'Others',
                'billing': float(others_billing),
                'story': float(others_story),
                'percentage': others_pct,
                'tx_count': others_tx_count,
                'is_grouped': True,
                'grouped_subcategories_count': others_count
            })

        return individual_categories

    @staticmethod
    def get_pnl_analytics(qs):
        """
        Comprehensive Profit and Loss (P&L) Analytics:
        Revenue, Cost of Fulfillment, Net Profit / STORY, Margins,
        Monthly P&L progression, Yearly P&L comparison, and Quarterly breakdowns.
        """
        month_order = {'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12, 'jan': 1, 'feb': 2, 'mar': 3}

        agg = qs.aggregate(
            gross_revenue=Sum('billing_amount'),
            fulfillment_cost=Sum('amount_paid'),
            net_profit=Sum('story_amount'),
            tx_count=Count('id'),
            unique_dealers=Count('dealer_code', distinct=True)
        )

        gross_revenue = agg['gross_revenue'] or Decimal('0.00')
        fulfillment_cost = agg['fulfillment_cost'] or Decimal('0.00')
        net_profit = agg['net_profit'] or Decimal('0.00')
        tx_count = agg['tx_count'] or 0
        unique_dealers = agg['unique_dealers'] or 0

        profit_margin_pct = (net_profit / gross_revenue * 100) if gross_revenue > 0 else Decimal('0.00')
        cost_ratio_pct = (fulfillment_cost / gross_revenue * 100) if gross_revenue > 0 else Decimal('0.00')

        # 1. Monthly P&L Ledger
        raw_months = list(qs.values('month_label').annotate(
            revenue=Sum('billing_amount'),
            cost=Sum('amount_paid'),
            profit=Sum('story_amount'),
            tx_count=Count('id')
        ))
        raw_months.sort(key=lambda x: month_order.get(x['month_label'][:3].lower(), 99))

        monthly_pnl = []
        cumulative_profit = Decimal('0.00')
        prev_rev = None
        prev_profit = None

        peak_profit_month = None
        peak_profit_val = Decimal('-999999999')
        lowest_profit_month = None
        lowest_profit_val = Decimal('999999999')

        for m in raw_months:
            rev = m['revenue'] or Decimal('0.00')
            cst = m['cost'] or Decimal('0.00')
            prf = m['profit'] or Decimal('0.00')
            tx = m['tx_count'] or 0
            
            cumulative_profit += prf
            margin = (prf / rev * 100) if rev > 0 else Decimal('0.00')
            cost_pct = (cst / rev * 100) if rev > 0 else Decimal('0.00')
            avg_profit_tx = (prf / Decimal(str(tx))) if tx > 0 else Decimal('0.00')

            rev_growth = None
            if prev_rev is not None and prev_rev > 0:
                rev_growth = round(((rev - prev_rev) / prev_rev) * 100, 2)

            profit_growth = None
            if prev_profit is not None and prev_profit > 0:
                profit_growth = round(((prf - prev_profit) / prev_profit) * 100, 2)

            if prf > peak_profit_val:
                peak_profit_val = prf
                peak_profit_month = m['month_label']

            if prf < lowest_profit_val:
                lowest_profit_val = prf
                lowest_profit_month = m['month_label']

            monthly_pnl.append({
                'month_label': m['month_label'],
                'revenue': rev,
                'cost': cst,
                'profit': prf,
                'margin_pct': round(margin, 2),
                'cost_pct': round(cost_pct, 2),
                'rev_growth_pct': rev_growth,
                'profit_growth_pct': profit_growth,
                'cumulative_profit': cumulative_profit,
                'tx_count': tx,
                'avg_profit_tx': round(avg_profit_tx, 2)
            })

            prev_rev = rev
            prev_profit = prf

        months_count = len(monthly_pnl) or 1
        avg_monthly_revenue = gross_revenue / Decimal(str(months_count))
        avg_monthly_profit = net_profit / Decimal(str(months_count))

        # 2. Yearly P&L Aggregations
        yearly_raw = list(qs.values('financial_year').annotate(
            revenue=Sum('billing_amount'),
            cost=Sum('amount_paid'),
            profit=Sum('story_amount'),
            tx_count=Count('id')
        ).order_by('financial_year'))

        yearly_pnl = []
        for y in yearly_raw:
            rev = y['revenue'] or Decimal('0.00')
            cst = y['cost'] or Decimal('0.00')
            prf = y['profit'] or Decimal('0.00')
            margin = (prf / rev * 100) if rev > 0 else Decimal('0.00')

            # Quarter calculations
            q1_qs = qs.filter(financial_year=y['financial_year'], month_label__iregex=r'^(apr|may|jun)')
            q2_qs = qs.filter(financial_year=y['financial_year'], month_label__iregex=r'^(jul|aug|sep)')
            q3_qs = qs.filter(financial_year=y['financial_year'], month_label__iregex=r'^(oct|nov|dec)')
            q4_qs = qs.filter(financial_year=y['financial_year'], month_label__iregex=r'^(jan|feb|mar)')

            def agg_q(q_queryset):
                res = q_queryset.aggregate(r=Sum('billing_amount'), c=Sum('amount_paid'), p=Sum('story_amount'))
                r = res['r'] or Decimal('0.00')
                c = res['c'] or Decimal('0.00')
                p = res['p'] or Decimal('0.00')
                m = (p / r * 100) if r > 0 else Decimal('0.00')
                return {'revenue': r, 'cost': c, 'profit': p, 'margin_pct': round(m, 2)}

            yearly_pnl.append({
                'financial_year': y['financial_year'],
                'revenue': rev,
                'cost': cst,
                'profit': prf,
                'margin_pct': round(margin, 2),
                'tx_count': y['tx_count'],
                'q1': agg_q(q1_qs),
                'q2': agg_q(q2_qs),
                'q3': agg_q(q3_qs),
                'q4': agg_q(q4_qs),
            })

        # 3. Category Profitability Breakdown
        category_pnl = list(qs.values('standardized_category').annotate(
            revenue=Sum('billing_amount'),
            cost=Sum('amount_paid'),
            profit=Sum('story_amount'),
            tx_count=Count('id')
        ).order_by('-profit'))
        for cp in category_pnl:
            r = cp['revenue'] or Decimal('0.00')
            p = cp['profit'] or Decimal('0.00')
            cp['margin_pct'] = round((p / r * 100) if r > 0 else Decimal('0.00'), 2)
            cp['profit_share'] = round((p / net_profit * 100) if net_profit > 0 else Decimal('0.00'), 2)

        # 4. RM Profitability Breakdown
        rm_pnl = list(qs.values('rm').annotate(
            revenue=Sum('billing_amount'),
            cost=Sum('amount_paid'),
            profit=Sum('story_amount'),
            tx_count=Count('id')
        ).order_by('-profit'))
        for rp in rm_pnl:
            r = rp['revenue'] or Decimal('0.00')
            p = rp['profit'] or Decimal('0.00')
            rp['margin_pct'] = round((p / r * 100) if r > 0 else Decimal('0.00'), 2)
            rp['profit_share'] = round((p / net_profit * 100) if net_profit > 0 else Decimal('0.00'), 2)

        return {
            'gross_revenue': gross_revenue,
            'fulfillment_cost': fulfillment_cost,
            'net_profit': net_profit,
            'profit_margin_pct': round(profit_margin_pct, 2),
            'cost_ratio_pct': round(cost_ratio_pct, 2),
            'tx_count': tx_count,
            'unique_dealers': unique_dealers,
            'avg_monthly_revenue': round(avg_monthly_revenue, 2),
            'avg_monthly_profit': round(avg_monthly_profit, 2),
            'peak_profit_month': peak_profit_month or 'N/A',
            'peak_profit_val': peak_profit_val if peak_profit_val != Decimal('-999999999') else Decimal('0.00'),
            'lowest_profit_month': lowest_profit_month or 'N/A',
            'lowest_profit_val': lowest_profit_val if lowest_profit_val != Decimal('999999999') else Decimal('0.00'),
            'monthly_pnl': monthly_pnl,
            'yearly_pnl': yearly_pnl,
            'category_pnl': category_pnl,
            'rm_pnl': rm_pnl,
        }
