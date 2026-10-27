from django.contrib import admin
from apps.analytics.models import BillingTransaction

@admin.register(BillingTransaction)
class BillingTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_row_number', 'month_label', 'dealer_code', 'firm_name', 'rm', 'standardized_category', 'billing_amount', 'amount_paid', 'story_amount', 'payment_status')
    list_filter = ('month_label', 'rm', 'payment_status', 'standardized_category')
    search_fields = ('dealer_code', 'firm_name', 'rm', 'payment_spoc')
