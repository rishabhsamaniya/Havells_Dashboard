from apps.imports.models import ImportBatch
from apps.core.models import MetricDefinition
from apps.quality.models import DataQualityIssue

def app_context(request):
    """
    Global context processor for MIS Dashboard
    Provides active import batch info, metric settings, and pending quality alert counts.
    """
    total_batches = ImportBatch.objects.filter(is_active=True).count()
    latest_batch = ImportBatch.objects.filter(is_active=True, status='COMPLETED').order_by('-uploaded_at').first()
    
    pending_alerts_count = DataQualityIssue.objects.filter(
        review_status='PENDING',
        severity__in=['CRITICAL', 'HIGH']
    ).count()

    story_metric = MetricDefinition.objects.filter(code='STORY_DEFINITION', is_active=True).first()

    return {
        'total_active_batches': total_batches,
        'latest_batch': latest_batch,
        'pending_alerts_count': pending_alerts_count,
        'story_metric_definition': story_metric,
        'app_name': 'Havells Billing MIS Analytics',
        'current_fy': 'FY 2026-27',
    }
