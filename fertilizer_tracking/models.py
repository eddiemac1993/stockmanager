from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum
from decimal import Decimal

class Depot(models.Model):
    name = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    manager = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    nrc = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.name or 'NoName'} - {self.district or 'NoDistrict'}"

class Product(models.Model):
    name = models.CharField(max_length=100)
    price_per_bag = models.DecimalField(max_digits=10, decimal_places=2, default=1200.00)
    commission_per_bag = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    
    def __str__(self):
        return self.name or "NoProduct"

class Stock(models.Model):
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('depot', 'product')
    
    def get_available_bags(self):
        """Get available bags based on MT quantity"""
        bags_per_mt = 20
        return int(self.quantity * bags_per_mt) if self.quantity else 0
    
    def can_sell_bags(self, bags_to_sell):
        """Check if specified number of bags can be sold"""
        return self.get_available_bags() >= bags_to_sell
    
    def reduce_stock(self, bags_sold):
        """Reduce stock by specified number of bags"""
        if self.can_sell_bags(bags_sold):
            bags_per_mt = 20
            quantity_reduction = Decimal(bags_sold) / Decimal(bags_per_mt)
            old_quantity = self.quantity
            self.quantity -= quantity_reduction
            self.save()
            
            # Record stock change
            StockHistory.objects.create(
                stock=self,
                date=models.DateTimeField.now().date(),
                previous_quantity=old_quantity,
                new_quantity=self.quantity,
                change_type='sale',
                bags_sold=bags_sold,
                description=f"Stock reduced due to sale of {bags_sold} bags"
            )
            return True
        return False
    
    def get_monetary_value(self):
        """Calculate monetary value of stock in metric tons"""
        if self.product and self.quantity:
            bags_per_mt = 20
            total_bags = self.quantity * bags_per_mt
            monetary_value = total_bags * self.product.price_per_bag
            return monetary_value
        return 0
    
    def __str__(self):
        depot_name = self.depot.name if self.depot else "NoDepot"
        product_name = self.product.name if self.product else "NoProduct"
        return f"{depot_name} - {product_name}: {self.quantity}MT"

class StockHistory(models.Model):
    CHANGE_TYPES = [
        ('addition', 'Stock Addition'),
        ('sale', 'Stock Sale'),
        ('adjustment', 'Stock Adjustment'),
        ('correction', 'Stock Correction'),
    ]
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='history')
    date = models.DateField()
    previous_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    new_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    bags_sold = models.IntegerField(null=True, blank=True)  # Only for sales
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)  # Positive for addition, negative for reduction
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = "Stock Histories"
    
    def save(self, *args, **kwargs):
        # Calculate quantity change
        self.quantity_change = self.new_quantity - self.previous_quantity
        super().save(*args, **kwargs)
    
    def get_change_in_bags(self):
        """Get the change in number of bags"""
        return int(self.quantity_change * 20)
    
    def __str__(self):
        change_direction = "+" if self.quantity_change > 0 else ""
        return f"{self.date} - {self.stock} - {change_direction}{self.quantity_change}MT ({self.get_change_type_display()})"

class DailySale(models.Model):
    date = models.DateField()
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    bags_sold = models.IntegerField(validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ('date', 'depot', 'product')
    
    def save(self, *args, **kwargs):
        # Check if this is a new sale (not an update)
        is_new = self.pk is None
        
        # Calculate amounts first
        if self.product:
            self.total_amount = Decimal(self.bags_sold) * self.product.price_per_bag
            self.commission_earned = Decimal(self.bags_sold) * self.product.commission_per_bag
        else:
            self.total_amount = 0
            self.commission_earned = 0
        
        super().save(*args, **kwargs)
        
        # Reduce stock only for new sales
        if is_new and self.depot and self.product and self.bags_sold > 0:
            self.reduce_stock()
    
    def reduce_stock(self):
        """Reduce stock quantity based on bags sold - FIXED VERSION"""
        try:
            # Get stock record
            stock = Stock.objects.get(depot=self.depot, product=self.product)
            
            # Convert bags to MT (20 bags = 1 MT)
            bags_per_mt = 20
            quantity_reduction = Decimal(self.bags_sold) / Decimal(bags_per_mt)
            
            print(f"DEBUG: Attempting to reduce stock by {quantity_reduction} MT for {self.bags_sold} bags")
            print(f"DEBUG: Current stock before reduction: {stock.quantity} MT")
            
            # Ensure we don't go below zero
            if stock.quantity >= quantity_reduction:
                old_quantity = stock.quantity
                stock.quantity -= quantity_reduction
                stock.save()
                print(f"DEBUG: Stock successfully reduced to: {stock.quantity} MT")
                
                # Record stock history for the sale
                StockHistory.objects.create(
                    stock=stock,
                    date=self.date,
                    previous_quantity=old_quantity,
                    new_quantity=stock.quantity,
                    change_type='sale',
                    bags_sold=self.bags_sold,
                    description=f"Stock reduced due to sale of {self.bags_sold} bags on {self.date}"
                )
                return True
            else:
                # If insufficient stock, raise exception
                error_msg = f"Insufficient stock! Available: {stock.get_available_bags()} bags, Trying to sell: {self.bags_sold} bags"
                print(f"DEBUG: {error_msg}")
                # Delete the sale since stock is insufficient
                self.delete()
                raise Exception(error_msg)
                
        except Stock.DoesNotExist:
            # Handle cases where stock record doesn't exist
            error_msg = f"No stock record found for {self.product} at {self.depot}"
            print(f"DEBUG: {error_msg}")
            # Delete the sale since no stock record exists
            self.delete()
            raise Exception(error_msg)
        except Exception as e:
            print(f"DEBUG: Error reducing stock: {e}")
            raise
    
    def __str__(self):
        depot_name = self.depot.name if self.depot else "NoDepot"
        product_name = self.product.name if self.product else "NoProduct"
        return f"{self.date} - {depot_name} - {product_name} - {self.bags_sold} bags"

class UCFPayment(models.Model):
    PAYMENT_TYPES = [
        ('payment', 'Payment to UCF'),
        ('receipt', 'Receipt from UCF'),
    ]
    
    date = models.DateField()
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_number = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.date} - {self.payment_type} - K{self.amount}"

class DailyBalance(models.Model):
    date = models.DateField(unique=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commissions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def calculate_totals(self):
        """Calculate all totals based on the date"""
        # Get sales for this date
        sales_data = DailySale.objects.filter(date=self.date).aggregate(
            total_sales=Sum('total_amount') or 0,
            total_commissions=Sum('commission_earned') or 0
        )
        
        # Get payments for this date
        payments_data = UCFPayment.objects.filter(
            date=self.date,
            payment_type='payment'
        ).aggregate(total_payments=Sum('amount') or 0)
        
        self.total_sales = sales_data['total_sales'] or 0
        self.total_commissions = sales_data['total_commissions'] or 0
        self.total_payments = payments_data['total_payments'] or 0
        
        # Calculate closing balance
        self.closing_balance = (
            self.opening_balance + 
            self.total_sales + 
            self.total_commissions - 
            self.total_payments
        )
    
    def save(self, *args, **kwargs):
        # Auto-calculate totals before saving
        self.calculate_totals()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Balance for {self.date}"