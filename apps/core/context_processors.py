from apps.imports.models import ImportBatch
from apps.core.models import MetricDefinition
from apps.quality.models import DataQualityIssue
from apps.core.permissions import get_user_effective_permissions

def app_context(request):
    """
    Global context processor for MIS Dashboard
    Provides active import batch info, metric settings, pending quality alert counts, and RBAC user permissions.
    """
    total_batches = ImportBatch.objects.filter(is_active=True).count()
    latest_batch = ImportBatch.objects.filter(is_active=True, status='COMPLETED').order_by('-uploaded_at').first()
    
    pending_alerts_count = DataQualityIssue.objects.filter(
        review_status='PENDING',
        severity__in=['CRITICAL', 'HIGH']
    ).count()

    story_metric = MetricDefinition.objects.filter(code='STORY_DEFINITION', is_active=True).first()

    user_perms = {}
    user_role = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        user_perms = get_user_effective_permissions(request.user, request)
        if hasattr(request.user, 'profile') and request.user.profile.role:
            user_role = request.user.profile.role.name
        elif request.user.is_superuser:
            user_role = "Super Admin"

    return {
        'total_active_batches': total_batches,
        'latest_batch': latest_batch,
        'pending_alerts_count': pending_alerts_count,
        'story_metric_definition': story_metric,
        'app_name': 'Havells Billing MIS Analytics',
        'current_fy': 'FY 2026-27',
        'user_perms': user_perms,
        'user_role': user_role,
    }

