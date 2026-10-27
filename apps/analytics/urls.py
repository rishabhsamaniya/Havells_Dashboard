from django.urls import path
from apps.analytics import views

app_name = 'analytics'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('rm/', views.rm_analytics_view, name='rm'),
    path('monthly/', views.monthly_analytics_view, name='monthly'),
    path('story/', views.story_analytics_view, name='story'),
    path('payment/', views.payment_analytics_view, name='payment'),
    path('category/', views.category_analytics_view, name='category'),
    path('spoc/', views.spoc_analytics_view, name='spoc'),
    path('dealers/', views.dealer_analytics_view, name='dealers'),
    path('transactions/', views.transaction_explorer_view, name='transactions'),
    path('pnl/', views.pnl_analytics_view, name='pnl'),
    path('export/', views.export_centre_view, name='export_centre'),
    path('export/mis-workbook/', views.export_mis_workbook, name='export_mis'),
    path('export/pnl/', views.export_pnl_workbook_view, name='export_pnl'),
    path('export/transactions-csv/', views.export_transactions_csv, name='export_csv'),
]
