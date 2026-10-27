import os
import openpyxl
import pandas as pd
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage

from apps.imports.models import ImportBatch, RejectedRecord
from apps.imports.services.excel_service import ExcelImportService, CANONICAL_FIELD_CANDIDATES
from apps.analytics.services.analytics_service import AnalyticsService

@login_required
def upload_view(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        uploaded_file = request.FILES['excel_file']
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in ['.xlsx', '.xls']:
            messages.error(request, 'Invalid file format. Please upload an Excel file (.xlsx or .xls).')
            return redirect('imports:upload')

        # Calculate file hash
        file_hash = ImportBatch.calculate_file_hash(uploaded_file)
        
        # Check duplicate import
        existing_batch = ImportBatch.objects.filter(file_hash=file_hash, is_active=True).first()
        is_duplicate_hash = existing_batch is not None

        # Create batch
        batch = ImportBatch.objects.create(
            file_name=uploaded_file.name,
            file_hash=file_hash,
            uploaded_file=uploaded_file,
            uploaded_by=request.user,
            status='PENDING'
        )

        # Inspect workbook
        try:
            sheet_info = ExcelImportService.inspect_workbook(batch.uploaded_file.path)
            batch.detected_sheets = [s['name'] for s in sheet_info]
            batch.save()
        except Exception as e:
            messages.error(request, f"Error inspecting Excel file: {str(e)}")
            batch.status = 'FAILED'
            batch.error_log = str(e)
            batch.save()
            return redirect('imports:upload')

        # Auto-pick Master sheet if available, else first sheet
        master_candidate = next((s['name'] for s in sheet_info if 'master' in s['name'].lower()), None)
        selected_sheet = master_candidate or (sheet_info[0]['name'] if sheet_info else 'Sheet1')
        batch.sheet_name = selected_sheet
        batch.save()

        return redirect('imports:mapping', batch_id=batch.id)

    recent_batches = ImportBatch.objects.all().order_by('-uploaded_at')[:10]
    return render(request, 'imports/upload.html', {
        'recent_batches': recent_batches
    })

@login_required
def column_mapping_view(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id)
    
    # Allow user to switch sheet
    if request.GET.get('sheet'):
        batch.sheet_name = request.GET['sheet']
        batch.save()

    file_path = batch.uploaded_file.path
    sheet_name = batch.sheet_name

    try:
        preview_data = ExcelImportService.get_sheet_preview(file_path, sheet_name, max_rows=50)
    except Exception as e:
        messages.error(request, f"Unable to preview sheet '{sheet_name}': {str(e)}")
        return redirect('imports:upload')

    if request.method == 'POST':
        # Construct mapping from form post
        mapping = {}
        for canonical in CANONICAL_FIELD_CANDIDATES.keys():
            selected_col = request.POST.get(f"map_{canonical}")
            if selected_col and selected_col != '__ignore__':
                mapping[canonical] = selected_col

        mode = request.POST.get('import_mode', 'new')

        # Run process import
        success, result = ExcelImportService.process_import(
            import_batch=batch,
            column_mapping=mapping,
            mode=mode,
            user=request.user
        )

        if success:
            messages.success(
                request,
                f"Successfully imported {result['successful_records']} records from sheet '{sheet_name}'. "
                f"Billing: ₹{result['total_billing']:,.2f}, STORY: ₹{result['total_story']:,.2f}."
            )
            if result['rejected_records'] > 0:
                messages.warning(request, f"{result['rejected_records']} records were rejected due to validation errors.")
            if result['duplicate_records'] > 0:
                messages.info(request, f"{result['duplicate_records']} potential duplicate records were flagged.")
            return redirect('imports:reconcile', batch_id=batch.id)
        else:
            messages.error(request, f"Import failed: {result}")
            return redirect('imports:mapping', batch_id=batch.id)

    # Check for duplicate hash warning
    duplicate_batch = ImportBatch.objects.filter(
        file_hash=batch.file_hash,
        is_active=True
    ).exclude(id=batch.id).first()

    return render(request, 'imports/mapping.html', {
        'batch': batch,
        'detected_sheets': batch.detected_sheets,
        'current_sheet': sheet_name,
        'headers': preview_data['headers'],
        'raw_columns': preview_data['raw_columns'],
        'preview_rows': preview_data['rows'][:20],
        'suggested_mapping': preview_data['suggested_mapping'],
        'canonical_fields': CANONICAL_FIELD_CANDIDATES,
        'duplicate_batch': duplicate_batch,
    })

@login_required
def import_history_view(request):
    batches = ImportBatch.objects.all().order_by('-uploaded_at')
    return render(request, 'imports/history.html', {'batches': batches})

@login_required
def download_rejected_records(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id)
    rejected_rows = batch.rejected_rows.all().order_by('source_row_number')

    if not rejected_rows.exists():
        messages.info(request, "No rejected records for this batch.")
        return redirect('imports:history')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rejected Records"

    # Headers
    headers = ["Source Row", "Rejection Reason", "Original Raw Row Data"]
    ws.append(headers)

    for r in rejected_rows:
        raw_str = "; ".join([f"{k}: {v}" for k, v in r.raw_data.items() if v is not None])
        ws.append([r.source_row_number, r.rejection_reason, raw_str])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Rejected_Records_Batch_{batch.id}.xlsx"'
    wb.save(response)
    return response

@login_required
def reconcile_batch_view(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id)
    reconcile_data = AnalyticsService.get_source_reconciliation(batch)
    return render(request, 'imports/reconciliation.html', {
        'batch': batch,
        'reconcile': reconcile_data
    })
