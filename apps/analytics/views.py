import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Avg, F, Q

from apps.analytics.models import BillingTransaction
from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.export_service import ExportService
from apps.core.models import AuditLog
from apps.core.permissions import permission_required

def extract_filters_from_request(request):
    """
    Extracts global dashboard filter params from GET query parameters
    """
    filters = {}
    if request.GET.get('month'):
        filters['month'] = request.GET.get('month')
    if request.GET.get('rm'):
        filters['rm'] = request.GET.get('rm')
    if request.GET.get('spoc'):
        filters['payment_spoc'] = request.GET.get('spoc')
    if request.GET.get('category'):
        filters['category'] = request.GET.get('category')
    if request.GET.get('status'):
        filters['payment_status'] = request.GET.get('status')
    if request.GET.get('search'):
        filters['search'] = request.GET.get('search')
    if request.GET.get('batch_id'):
        filters['batch_id'] = request.GET.get('batch_id')
    return filters

@login_required
@permission_required('dashboard', 'can_view')
def dashboard_view(request):
    AnalyticsService.auto_repair_uncategorized_transactions()
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    
    qs = AnalyticsService.get_filtered_queryset(filters)
    kpis = AnalyticsService.get_executive_kpis(qs)
    
    # RM comparison chart data
    rm_data = AnalyticsService.get_rm_analytics(qs)
    # Monthly trends data
    month_data = AnalyticsService.get_monthly_analytics(qs)
    # Category mix data (grouped < 9% into Others)
    grouped_cats = AnalyticsService.get_grouped_category_mix(qs, threshold_pct=9.0)
    cat_data = AnalyticsService.get_category_analytics(qs)
    
    context = {
        'kpis': kpis,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'rm_data': rm_data,
        'month_data': month_data,
        'cat_data': cat_data['category_list'][:8],
        'grouped_cats': grouped_cats,
        # JSON serialized data for Plotly charts
        'plotly_rm_json': json.dumps([{
            'rm': r['rm'],
            'billing': float(r['total_billing']),
            'story': float(r['total_story']),
            'story_pct': float(r['story_percentage']),
            'tx_count': r['tx_count'],
        } for r in rm_data]),
        'plotly_month_json': json.dumps([{
            'month': m['month_label'],
            'billing': float(m['total_billing']),
            'paid': float(m['total_paid']),
            'story': float(m['total_story']),
            'growth': float(m['billing_growth_pct']) if m['billing_growth_pct'] is not None else 0,
        } for m in month_data]),
        'plotly_cat_json': json.dumps([{
            'category': c['category'],
            'billing': c['billing'],
            'story': c['story'],
            'percentage': c['percentage'],
            'is_grouped': c.get('is_grouped', False),
        } for c in grouped_cats]),
    }
    return render(request, 'analytics/dashboard.html', context)

@login_required
@permission_required('rm', 'can_view')
def rm_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    rm_list = AnalyticsService.get_rm_analytics(qs)

    return render(request, 'analytics/rm_analytics.html', {
        'rm_list': rm_list,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'plotly_rm_json': json.dumps([{
            'rm': r['rm'],
            'billing': float(r['total_billing']),
            'paid': float(r['total_paid']),
            'story': float(r['total_story']),
            'story_pct': float(r['story_percentage']),
            'dealers': r['unique_dealers'],
            'share_billing': float(r['share_billing_pct']),
        } for r in rm_list])
    })

@login_required
@permission_required('monthly', 'can_view')
def monthly_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    month_list = AnalyticsService.get_monthly_analytics(qs)

    return render(request, 'analytics/monthly_analytics.html', {
        'month_list': month_list,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'plotly_month_json': json.dumps([{
            'month': m['month_label'],
            'billing': float(m['total_billing']),
            'paid': float(m['total_paid']),
            'story': float(m['total_story']),
            'billing_growth': float(m['billing_growth_pct']) if m['billing_growth_pct'] is not None else 0,
            'story_growth': float(m['story_growth_pct']) if m['story_growth_pct'] is not None else 0,
        } for m in month_list])
    })

@login_required
@permission_required('story', 'can_view')
def story_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    story_data = AnalyticsService.get_story_analytics(qs)

    return render(request, 'analytics/story_analytics.html', {
        'story': story_data,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'story_rm_json': json.dumps([{
            'rm': item['rm'],
            'story': float(item['sum_story']),
            'story_pct': float(item['story_pct'])
        } for item in story_data['story_by_rm']]),
        'story_cat_json': json.dumps([{
            'cat': item['standardized_category'],
            'story': float(item['sum_story']),
            'story_pct': float(item['story_pct'])
        } for item in story_data['story_by_cat']]),
    })

@login_required
@permission_required('payment', 'can_view')
def payment_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    payment_data = AnalyticsService.get_payment_reconciliation(qs)

    return render(request, 'analytics/payment_analytics.html', {
        'payment': payment_data,
        'filter_opts': filter_opts,
        'active_filters': filters,
    })

@login_required
@permission_required('category', 'can_view')
def category_analytics_view(request):
    AnalyticsService.auto_repair_uncategorized_transactions()
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    cat_data = AnalyticsService.get_category_analytics(qs)
    grouped_cats = AnalyticsService.get_grouped_category_mix(qs, threshold_pct=9.0)

    return render(request, 'analytics/category_analytics.html', {
        'cat_data': cat_data,
        'grouped_cats': grouped_cats,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'plotly_cat_json': json.dumps([{
            'category': c['category'],
            'billing': c['billing'],
            'story': c['story'],
            'percentage': c['percentage'],
            'is_grouped': c.get('is_grouped', False),
        } for c in grouped_cats])
    })

@login_required
@permission_required('spoc', 'can_view')
def spoc_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    spoc_list = AnalyticsService.get_spoc_analytics(qs)

    return render(request, 'analytics/spoc_analytics.html', {
        'spoc_list': spoc_list,
        'filter_opts': filter_opts,
        'active_filters': filters,
    })

@login_required
@permission_required('dealers', 'can_view')
def dealer_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    dealer_data = AnalyticsService.get_dealer_analytics(qs)

    return render(request, 'analytics/dealer_analytics.html', {
        'dealer_data': dealer_data,
        'filter_opts': filter_opts,
        'active_filters': filters,
    })

@login_required
@permission_required('transactions', 'can_view')
def transaction_explorer_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters).order_by('id')

    # Sorting
    sort_by = request.GET.get('sort', 'id')
    order = request.GET.get('order', 'asc')
    valid_sort_fields = ['id', 'month_label', 'dealer_code', 'firm_name', 'rm', 'standardized_category', 'payment_spoc', 'billing_amount', 'amount_paid', 'story_amount']
    if sort_by in valid_sort_fields:
        prefix = '-' if order == 'desc' else ''
        qs = qs.order_by(f"{prefix}{sort_by}")

    # Server-side pagination
    paginator = Paginator(qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'analytics/transaction_explorer.html', {
        'page_obj': page_obj,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'sort_by': sort_by,
        'order': order,
        'total_count': paginator.count,
    })

@login_required
@permission_required('export', 'can_view')
def export_centre_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    kpis = AnalyticsService.get_executive_kpis(qs)

    return render(request, 'analytics/export_centre.html', {
        'kpis': kpis,
        'filter_opts': filter_opts,
        'active_filters': filters,
    })

@login_required
@permission_required('export', 'can_export')
def export_mis_workbook(request):
    filters = extract_filters_from_request(request)
    excel_bytes = ExportService.generate_consolidated_mis_workbook(filters)
    
    AuditLog.objects.create(
        action='EXPORT',
        model_name='ConsolidatedMISReport',
        object_id='ALL',
        user=request.user,
        details={'filters': filters}
    )

    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Havells_Billing_MIS_Consolidated_Report.xlsx"'
    return response

@login_required
@permission_required('transactions', 'can_export')
def export_transactions_csv(request):
    import csv
    filters = extract_filters_from_request(request)
    qs = AnalyticsService.get_filtered_queryset(filters).order_by('id')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Havells_Transactions.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        "Source Row", "Month", "Dealer Code", "Firm Name", "Experience Category",
        "RM", "Payment SPOC", "Billing Amount", "Amount Paid", "STORY", "Payment Status"
    ])
    for tx in qs[:10000]:
        writer.writerow([
            tx.source_row_number,
            tx.month_label,
            tx.dealer_code,
            tx.firm_name,
            tx.standardized_category,
            tx.rm,
            tx.payment_spoc,
            tx.billing_amount,
            tx.amount_paid,
            tx.story_amount,
            tx.payment_status,
        ])
    return response

@login_required
@permission_required('pnl', 'can_view')
def pnl_analytics_view(request):
    filters = extract_filters_from_request(request)
    filter_opts = AnalyticsService.get_filter_options()
    qs = AnalyticsService.get_filtered_queryset(filters)
    pnl = AnalyticsService.get_pnl_analytics(qs)

    monthly_pnl_json = json.dumps([{
        'month': m['month_label'],
        'revenue': float(m['revenue']),
        'cost': float(m['cost']),
        'profit': float(m['profit']),
        'margin_pct': float(m['margin_pct']),
        'rev_growth': float(m['rev_growth_pct']) if m['rev_growth_pct'] is not None else 0,
        'profit_growth': float(m['profit_growth_pct']) if m['profit_growth_pct'] is not None else 0,
        'cumulative_profit': float(m['cumulative_profit']),
    } for m in pnl['monthly_pnl']])

    category_pnl_json = json.dumps([{
        'category': c['standardized_category'],
        'revenue': float(c['revenue']),
        'cost': float(c['cost']),
        'profit': float(c['profit']),
        'margin_pct': float(c['margin_pct']),
    } for c in pnl['category_pnl'][:8]])

    rm_pnl_json = json.dumps([{
        'rm': r['rm'],
        'revenue': float(r['revenue']),
        'cost': float(r['cost']),
        'profit': float(r['profit']),
        'margin_pct': float(r['margin_pct']),
    } for r in pnl['rm_pnl']])

    return render(request, 'analytics/pnl_analytics.html', {
        'pnl': pnl,
        'filter_opts': filter_opts,
        'active_filters': filters,
        'monthly_pnl_json': monthly_pnl_json,
        'category_pnl_json': category_pnl_json,
        'rm_pnl_json': rm_pnl_json,
    })

@login_required
@permission_required('pnl', 'can_export')
def export_pnl_workbook_view(request):
    filters = extract_filters_from_request(request)
    excel_bytes = ExportService.generate_pnl_workbook(filters)
    
    AuditLog.objects.create(
        action='EXPORT',
        model_name='ProfitAndLossStatement',
        object_id='ALL',
        user=request.user,
        details={'filters': filters}
    )

    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Havells_Billing_Profit_And_Loss_Statement.xlsx"'
    return response
