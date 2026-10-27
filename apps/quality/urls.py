from django.urls import path
from apps.quality import views

app_name = 'quality'

urlpatterns = [
    path('issues/', views.issues_list_view, name='issues'),
    path('issues/<int:issue_id>/review/', views.review_issue, name='review_issue'),
    path('categories/', views.category_normalization_view, name='categories'),
]
