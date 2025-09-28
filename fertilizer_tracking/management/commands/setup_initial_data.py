from django.core.management.base import BaseCommand
from fertilizer_tracking.models import Depot, Product, Stock

class Command(BaseCommand):
    help = 'Setup initial data for CMM Chronos Ltd'
    
    def handle(self, *args, **options):
        # Create depots
        depots_data = [
            {'name': 'MONZE', 'district': 'MONZE', 'manager': 'Matimba Munang\'andu', 'phone': '0760382210', 'nrc': '198061/77/1'},
            {'name': 'PEMBA', 'district': 'PEMBA', 'manager': 'Matimba Munang\'andu', 'phone': '0760382210', 'nrc': '198061/77/1'},
            {'name': 'KALOMO', 'district': 'KALOMO', 'manager': 'Armin Halurka Scherrer', 'phone': '0960110755', 'nrc': '214134/77/1'},
        ]
        
        for depot_data in depots_data:
            depot, created = Depot.objects.get_or_create(
                name=depot_data['name'],
                defaults=depot_data
            )
            if created:
                self.stdout.write(f"Created depot: {depot.name}")
        
        # Create products
        products_data = [
            {'name': 'D-COMPOUND', 'price_per_bag': 1200.00, 'commission_per_bag': 50.00},
            {'name': 'UREA', 'price_per_bag': 1200.00, 'commission_per_bag': 50.00},
        ]
        
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                self.stdout.write(f"Created product: {product.name}")
        
        self.stdout.write(self.style.SUCCESS('Initial data setup completed!'))