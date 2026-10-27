from django.urls import path
from apps.imports import views

app_name = 'imports'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('<int:batch_id>/mapping/', views.column_mapping_view, name='mapping'),
    path('<int:batch_id>/rejected/', views.download_rejected_records, name='rejected'),
    path('<int:batch_id>/reconcile/', views.reconcile_batch_view, name='reconcile'),
    path('history/', views.import_history_view, name='history'),
]
