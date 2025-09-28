from django import forms
from django.core.exceptions import ValidationError
from .models import DailySale, UCFPayment, Stock, StockHistory
from datetime import date

class DailySaleForm(forms.ModelForm):
    class Meta:
        model = DailySale
        fields = ['date', 'depot', 'product', 'bags_sold']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'depot': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'bags_sold': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        depot = cleaned_data.get('depot')
        product = cleaned_data.get('product')
        bags_sold = cleaned_data.get('bags_sold')
        
        if depot and product and bags_sold:
            try:
                stock = Stock.objects.get(depot=depot, product=product)
                if not stock.can_sell_bags(bags_sold):
                    available_bags = stock.get_available_bags()
                    raise ValidationError(
                        f"Insufficient stock! Available: {available_bags} bags, "
                        f"Trying to sell: {bags_sold} bags. "
                        f"Shortage: {bags_sold - available_bags} bags."
                    )
            except Stock.DoesNotExist:
                # If no stock record exists, it means zero stock
                raise ValidationError(
                    f"No stock available for {product} at {depot}. "
                    f"Please add stock before recording sales."
                )
        
        return cleaned_data

class UCFPaymentForm(forms.ModelForm):
    class Meta:
        model = UCFPayment
        fields = ['date', 'payment_type', 'amount', 'description', 'reference_number']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class StockUpdateForm(forms.ModelForm):
    change_type = forms.ChoiceField(
        choices=StockHistory.CHANGE_TYPES,
        initial='addition',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description for this stock change'})
    )
    
    class Meta:
        model = Stock
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['quantity'].initial = self.instance.quantity