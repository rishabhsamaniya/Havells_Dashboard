from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('settings/', views.settings_view, name='settings'),
]
