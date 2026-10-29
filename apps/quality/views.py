import io
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum

from apps.quality.models import DataQualityIssue, CategoryMapping
from apps.analytics.models import BillingTransaction
from apps.core.models import AuditLog
from apps.core.permissions import permission_required, has_module_perm

@login_required
@permission_required('quality', 'can_view')
def issues_list_view(request):
    qs = DataQualityIssue.objects.select_related('import_batch', 'reviewed_by').all()

    # Filters
    severity = request.GET.get('severity')
    issue_type = request.GET.get('issue_type')
    review_status = request.GET.get('review_status')
    search = request.GET.get('search')

    if severity:
        qs = qs.filter(severity=severity)
    if issue_type:
        qs = qs.filter(issue_type=issue_type)
    if review_status:
        qs = qs.filter(review_status=review_status)
    if search:
        qs = qs.filter(description__icontains=search)

    # Export to Excel if requested
    if request.GET.get('export') == 'excel':
        if not has_module_perm(request.user, 'quality', 'can_export', request):
            return render(request, 'core/403.html', {
                'module_code': 'quality',
                'module_name': 'Data Quality',
                'required_action': 'can_export',
                'error_message': 'You do not have permission to export quality issues.'
            }, status=403)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data Quality Exceptions"
        headers = ["ID", "Batch", "Row #", "Field Name", "Original Value", "Type", "Severity", "Description", "Status", "Review Notes"]
        ws.append(headers)
        for issue in qs:
            ws.append([
                issue.id,
                issue.import_batch.file_name,
                issue.source_row_number,
                issue.field_name,
                str(issue.original_value or ''),
                issue.get_issue_type_display(),
                issue.get_severity_display(),
                issue.description,
                issue.get_review_status_display(),
                issue.review_notes
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Data_Quality_Exceptions.xlsx"'
        wb.save(response)
        return response

    stats = {
        'total': DataQualityIssue.objects.count(),
        'pending': DataQualityIssue.objects.filter(review_status='PENDING').count(),
        'critical': DataQualityIssue.objects.filter(severity__in=['CRITICAL', 'HIGH']).count(),
        'duplicates': DataQualityIssue.objects.filter(issue_type='POTENTIAL_DUPLICATE').count(),
        'exceptions': DataQualityIssue.objects.filter(issue_type='BUSINESS_EXCEPTION').count(),
    }

    return render(request, 'quality/issues.html', {
        'issues': qs[:250],
        'stats': stats,
        'current_severity': severity,
        'current_type': issue_type,
        'current_status': review_status,
    })

@login_required
@permission_required('quality', 'can_edit')
def review_issue(request, issue_id):
    issue = get_object_or_404(DataQualityIssue, id=issue_id)
    if request.method == 'POST':
        new_status = request.POST.get('review_status')
        notes = request.POST.get('review_notes', '')
        if new_status in dict(DataQualityIssue.STATUS_CHOICES):
            issue.review_status = new_status
            issue.review_notes = notes
            issue.reviewed_by = request.user
            issue.reviewed_at = timezone.now()
            issue.save()

            AuditLog.objects.create(
                action='REVIEW',
                model_name='DataQualityIssue',
                object_id=str(issue.id),
                user=request.user,
                details={'status': new_status, 'notes': notes}
            )
            messages.success(request, f"Issue #{issue.id} marked as {issue.get_review_status_display()}.")

    return redirect('quality:issues')

@login_required
@permission_required('category_mapping', 'can_view')
def category_normalization_view(request):
    if request.method == 'POST':
        if not has_module_perm(request.user, 'category_mapping', 'can_edit', request):
            return render(request, 'core/403.html', {
                'module_code': 'category_mapping',
                'module_name': 'Category Mapping',
                'required_action': 'can_edit',
                'error_message': 'You do not have permission to modify category mappings.'
            }, status=403)
        action = request.POST.get('action')
        if action == 'update_mapping':
            raw_cat = request.POST.get('raw_category')
            std_cat = request.POST.get('standardized_category', '').strip()
            if raw_cat and std_cat:
                mapping, created = CategoryMapping.objects.update_or_create(
                    raw_category=raw_cat,
                    defaults={
                        'standardized_category': std_cat,
                        'is_reviewed': True,
                        'reviewed_by': request.user
                    }
                )
                # Update all existing transactions with this raw category
                updated_count = BillingTransaction.objects.filter(raw_category=raw_cat).update(
                    standardized_category=std_cat
                )
                AuditLog.objects.create(
                    action='NORMALIZE',
                    model_name='CategoryMapping',
                    object_id=raw_cat,
                    user=request.user,
                    details={'raw': raw_cat, 'standardized': std_cat, 'updated_transactions': updated_count}
                )
                messages.success(request, f"Normalized '{raw_cat}' to '{std_cat}' across {updated_count} transactions.")
        return redirect('quality:categories')

    mappings = CategoryMapping.objects.all().order_by('standardized_category')
    
    # Calculate transaction stats per category mapping
    stats_map = {}
    tx_agg = BillingTransaction.objects.values('raw_category').annotate(
        tx_count=Count('id'),
        billing_sum=Sum('billing_amount'),
        story_sum=Sum('story_amount')
    )
    for t in tx_agg:
        stats_map[t['raw_category']] = t

    enhanced_mappings = []
    for m in mappings:
        stat = stats_map.get(m.raw_category, {'tx_count': 0, 'billing_sum': 0, 'story_sum': 0})
        enhanced_mappings.append({
            'mapping': m,
            'tx_count': stat['tx_count'],
            'billing_sum': stat['billing_sum'] or 0,
            'story_sum': stat['story_sum'] or 0,
        })

    return render(request, 'quality/categories.html', {
        'mappings': enhanced_mappings
    })
