from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('record-sale/', views.record_sale, name='record_sale'),
    path('record-payment/', views.record_payment, name='record_payment'),
    path('update-stock/<int:stock_id>/', views.update_stock, name='update_stock'),
    path('stock-history/', views.stock_history, name='stock_history'),
    path('stock-history/<int:stock_id>/', views.stock_history, name='stock_history_detail'),
    path('sales-report/', views.sales_report, name='sales_report'),
    path('download-sales-report/', views.download_sales_report, name='download_sales_report'),
    path('ucf-balance/', views.ucf_balance_report, name='ucf_balance'),
]