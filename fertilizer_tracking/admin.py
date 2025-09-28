from django.contrib import admin
from .models import Depot, Product, Stock, DailySale, UCFPayment, DailyBalance

@admin.register(Depot)
class DepotAdmin(admin.ModelAdmin):
    list_display = ['name', 'district', 'manager', 'phone']
    search_fields = ['name', 'district', 'manager']
    list_filter = ['district']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_per_bag', 'commission_per_bag']
    search_fields = ['name']

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['depot', 'product', 'quantity', 'date_updated']
    list_filter = ['depot', 'product']
    search_fields = ['depot__name', 'product__name']

@admin.register(DailySale)
class DailySaleAdmin(admin.ModelAdmin):
    list_display = ['date', 'depot', 'product', 'bags_sold', 'total_amount', 'commission_earned']
    list_filter = ['date', 'depot', 'product']
    search_fields = ['depot__name', 'product__name']
    date_hierarchy = 'date'

@admin.register(UCFPayment)
class UCFPaymentAdmin(admin.ModelAdmin):
    list_display = ['date', 'payment_type', 'amount', 'reference_number', 'description']
    list_filter = ['date', 'payment_type']
    search_fields = ['description', 'reference_number']
    date_hierarchy = 'date'

@admin.register(DailyBalance)
class DailyBalanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'opening_balance', 'total_sales', 'total_commissions', 'total_payments', 'closing_balance']
    readonly_fields = ['total_sales', 'total_commissions', 'total_payments', 'closing_balance']
    date_hierarchy = 'date'
    search_fields = ['date']