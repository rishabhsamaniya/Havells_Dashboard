from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.core.models import AuditLog, MetricDefinition, MonthlyRMTarget
from apps.analytics.models import BillingTransaction

def user_login(request):
    if request.user.is_authenticated:
        return redirect('analytics:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            AuditLog.objects.create(
                action='LOGIN',
                model_name='User',
                object_id=str(user.id),
                user=user,
                details={'username': username}
            )
            return redirect('analytics:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')

def user_logout(request):
    logout(request)
    return redirect('core:login')

@login_required
def audit_logs(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:200]
    return render(request, 'core/audit_logs.html', {'logs': logs})

@login_required
def settings_view(request):
    metric = MetricDefinition.objects.filter(code='STORY_DEFINITION').first()
    if not metric:
        metric = MetricDefinition.objects.create(
            code='STORY_DEFINITION',
            name='STORY Margin Definition',
            description='Preserves the dedicated STORY column from the source Excel file as the source of truth.',
            formula_type='SOURCE_COLUMN',
            notes='Do not assume STORY is Billing minus Paid unless confirmed by admin.'
        )

    targets = MonthlyRMTarget.objects.all().order_by('month_label', 'rm_name')
    rms = list(BillingTransaction.objects.filter(import_batch__is_active=True).values_list('rm', flat=True).distinct().order_by('rm'))
    months = list(BillingTransaction.objects.filter(import_batch__is_active=True).values_list('month_label', flat=True).distinct().order_by('month_label'))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_story_metric':
            metric.formula_type = request.POST.get('formula_type', 'SOURCE_COLUMN')
            metric.formula_expression = request.POST.get('formula_expression', '')
            metric.notes = request.POST.get('notes', '')
            metric.save()
            AuditLog.objects.create(
                action='METRIC_CHANGE',
                model_name='MetricDefinition',
                object_id=str(metric.id),
                user=request.user,
                details={'formula_type': metric.formula_type}
            )
            messages.success(request, 'STORY business metric definition updated successfully.')
        elif action == 'add_target':
            rm_name = request.POST.get('rm_name')
            month_label = request.POST.get('month_label')
            target_billing = request.POST.get('target_billing') or '0'
            target_story = request.POST.get('target_story') or '0'
            MonthlyRMTarget.objects.update_or_create(
                rm_name=rm_name,
                month_label=month_label,
                defaults={
                    'target_billing': target_billing,
                    'target_story': target_story
                }
            )
            AuditLog.objects.create(
                action='TARGET_UPDATE',
                model_name='MonthlyRMTarget',
                object_id=f"{rm_name}_{month_label}",
                user=request.user,
                details={'rm': rm_name, 'month': month_label, 'target_billing': target_billing}
            )
            messages.success(request, f'Target set for {rm_name} in {month_label}.')
        return redirect('core:settings')

    return render(request, 'core/settings.html', {
        'metric': metric,
        'targets': targets,
        'rms': rms,
        'months': months,
    })
