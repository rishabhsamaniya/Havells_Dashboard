from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('settings/', views.settings_view, name='settings'),

    # RBAC Routes
    path('rbac/', views.rbac_dashboard_view, name='rbac_dashboard'),
    path('rbac/users/create/', views.rbac_user_create_view, name='rbac_user_create'),
    path('rbac/users/<int:user_id>/edit/', views.rbac_user_edit_view, name='rbac_user_edit'),
    path('rbac/users/<int:user_id>/permissions/', views.rbac_user_permissions_view, name='rbac_user_permissions'),
    path('rbac/users/<int:user_id>/toggle-active/', views.rbac_toggle_user_active_view, name='rbac_toggle_user_active'),
    path('rbac/roles/create/', views.rbac_role_create_view, name='rbac_role_create'),
    path('rbac/roles/<int:role_id>/permissions/', views.rbac_role_permissions_view, name='rbac_role_permissions'),
]
