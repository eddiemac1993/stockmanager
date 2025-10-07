from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date, timedelta
from django.contrib import messages
from decimal import Decimal

from .models import Depot, Product, Stock, DailySale, UCFPayment, DailyBalance, StockHistory
from .forms import DailySaleForm, UCFPaymentForm, StockUpdateForm

def dashboard(request):
    today = date.today()

    # Overall sales (all time)
    all_sales = DailySale.objects.all()
    total_overall_sales = all_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_overall_commissions = all_sales.aggregate(Sum('commission_earned'))['commission_earned__sum'] or 0

    # Current stock with monetary value
    stocks = Stock.objects.select_related('depot', 'product')

    # Calculate total stock value and total available bags
    total_stock_value = 0
    total_available_bags = 0
    for stock in stocks:
        total_stock_value += stock.get_monetary_value()
        total_available_bags += stock.get_available_bags()

    # Payments to UCF
    recent_payments = UCFPayment.objects.order_by('-date')[:5]

    # Recent stock changes
    recent_stock_changes = StockHistory.objects.select_related('stock', 'stock__depot', 'stock__product').order_by('-date', '-created_at')[:10]

    context = {
        'all_sales': all_sales,
        'total_overall_sales': total_overall_sales,
        'total_overall_commissions': total_overall_commissions,
        'stocks': stocks,
        'recent_payments': recent_payments,
        'recent_stock_changes': recent_stock_changes,
        'total_stock_value': total_stock_value,
        'total_available_bags': total_available_bags,
        'today': today,
    }

    return render(request, 'fertilizer_tracking/dashboard.html', context)

def record_sale(request):
    # Get current stock levels to display in the template
    stocks = Stock.objects.select_related('depot', 'product')

    if request.method == 'POST':
        form = DailySaleForm(request.POST)
        if form.is_valid():
            try:
                # Get the data before saving to check stock
                depot = form.cleaned_data['depot']
                product = form.cleaned_data['product']
                bags_sold = form.cleaned_data['bags_sold']
                sale_date = form.cleaned_data['date']

                print(f"DEBUG: Attempting to record sale: {depot} - {product} - {bags_sold} bags")

                # Check stock availability one more time before saving
                stock = Stock.objects.get(depot=depot, product=product)
                available_bags_before = stock.get_available_bags()
                print(f"DEBUG: Available bags before sale: {available_bags_before}")

                if not stock.can_sell_bags(bags_sold):
                    messages.error(request, f"Insufficient stock! Available: {available_bags_before} bags")
                    return render(request, 'fertilizer_tracking/record_sale.html', {
                        'form': form,
                        'stocks': stocks
                    })

                # Save the sale
                sale = form.save()

                # Refresh stock to see the updated value
                stock.refresh_from_db()
                available_bags_after = stock.get_available_bags()

                print(f"DEBUG: Available bags after sale: {available_bags_after}")
                print(f"DEBUG: Stock reduced successfully!")

                messages.success(request, f"Sale recorded successfully! Stock reduced from {available_bags_before} to {available_bags_after} bags.")
                return redirect('dashboard')

            except Exception as e:
                print(f"DEBUG: Error in record_sale view: {e}")
                messages.error(request, f"Error recording sale: {str(e)}")
                return render(request, 'fertilizer_tracking/record_sale.html', {
                    'form': form,
                    'stocks': stocks
                })
        else:
            # Form is not valid
            messages.error(request, "Please correct the errors below.")
    else:
        form = DailySaleForm(initial={'date': date.today()})

    return render(request, 'fertilizer_tracking/record_sale.html', {
        'form': form,
        'stocks': stocks
    })

def record_payment(request):
    if request.method == 'POST':
        form = UCFPaymentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment recorded successfully!")
            return redirect('dashboard')
    else:
        form = UCFPaymentForm(initial={'date': date.today()})

    return render(request, 'fertilizer_tracking/record_payment.html', {'form': form})

def update_stock(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)

    if request.method == 'POST':
        form = StockUpdateForm(request.POST, instance=stock)
        if form.is_valid():
            # Get the old quantity before saving
            old_quantity = stock.quantity
            new_quantity = form.cleaned_data['quantity']
            change_type = form.cleaned_data['change_type']
            description = form.cleaned_data['description']

            # Save the stock with new quantity
            stock = form.save()

            # Record stock history
            StockHistory.objects.create(
                stock=stock,
                date=date.today(),
                previous_quantity=old_quantity,
                new_quantity=new_quantity,
                change_type=change_type,
                description=description or f"Stock updated from {old_quantity} to {new_quantity} MT"
            )

            messages.success(request, f"Stock updated successfully! Recorded {change_type} from {old_quantity} to {new_quantity} MT")
            return redirect('dashboard')
    else:
        form = StockUpdateForm(instance=stock)

    return render(request, 'fertilizer_tracking/update_stock.html', {'form': form, 'stock': stock})

def stock_history(request, stock_id=None):
    """View to see stock history for a specific stock item or all stocks"""
    if stock_id:
        stock = get_object_or_404(Stock, id=stock_id)
        history = StockHistory.objects.filter(stock=stock).select_related('stock', 'stock__depot', 'stock__product')
        title = f"Stock History - {stock.depot.name} - {stock.product.name}"
    else:
        stock = None
        history = StockHistory.objects.all().select_related('stock', 'stock__depot', 'stock__product')
        title = "All Stock History"

    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        history = history.filter(date__gte=start_date)
    if end_date:
        history = history.filter(date__lte=end_date)

    history = history.order_by('-date', '-created_at')

    context = {
        'stock': stock,
        'history': history,
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'fertilizer_tracking/stock_history.html', context)

def sales_report(request):
    start_date = request.GET.get('start_date', date.today() - timedelta(days=30))
    end_date = request.GET.get('end_date', date.today())

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    sales = DailySale.objects.filter(date__range=[start_date, end_date])
    total_sales = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_commissions = sales.aggregate(Sum('commission_earned'))['commission_earned__sum'] or 0

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_commissions': total_commissions,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'fertilizer_tracking/sales_report.html', context)

def download_sales_report(request):
    start_date = request.GET.get('start_date', date.today() - timedelta(days=30))
    end_date = request.GET.get('end_date', date.today())

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    sales = DailySale.objects.filter(date__range=[start_date, end_date])
    total_sales = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_commissions = sales.aggregate(Sum('commission_earned'))['commission_earned__sum'] or 0

    # Create a simple text report instead of PDF
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_to_{end_date}.txt"'

    report_lines = []
    report_lines.append(f"CMM Chronos Ltd - Sales Report ({start_date} to {end_date})")
    report_lines.append("=" * 60)
    report_lines.append(f"{'Date':<12} {'Depot':<15} {'Product':<15} {'Bags':<6} {'Amount':<12} {'Commission':<12}")
    report_lines.append("-" * 60)

    for sale in sales:
        report_lines.append(f"{sale.date:<12} {sale.depot.name:<15} {sale.product.name:<15} {sale.bags_sold:<6} K{sale.total_amount:<11.2f} K{sale.commission_earned:<11.2f}")

    report_lines.append("-" * 60)
    report_lines.append(f"{'TOTAL':<48} K{total_sales:<11.2f} K{total_commissions:<11.2f}")

    response.write("\n".join(report_lines))
    return response

def ucf_balance_report(request):
    # Calculate total owed to UCF
    total_sales = DailySale.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_payments = UCFPayment.objects.filter(payment_type='payment').aggregate(Sum('amount'))['amount__sum'] or 0
    total_receipts = UCFPayment.objects.filter(payment_type='receipt').aggregate(Sum('amount'))['amount__sum'] or 0

    balance_owed = total_sales - total_payments + total_receipts

    payments = UCFPayment.objects.all().order_by('-date')

    context = {
        'total_sales': total_sales,
        'total_payments': total_payments,
        'total_receipts': total_receipts,
        'balance_owed': balance_owed,
        'payments': payments,
    }

    return render(request, 'fertilizer_tracking/ucf_balance.html', context)