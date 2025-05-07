from django import forms
from .models import Products, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Products
        fields = [
            'name',
            'description',
            'image',
            'brand',
            'category',
            'weight',
            'regular_price',
            'offer_percentage',
            'sales_price',
            'is_available',
            'stock'
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'regular_price': forms.NumberInput(attrs={'step': '0.01'}),
            'offer_percentage': forms.NumberInput(attrs={'step': '0.01'}),
            'sales_price': forms.NumberInput(attrs={'step': '0.01'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'image', 'is_active', 'is_listed']

    # If you want to use specific widgets for fields (like text area for description), you can specify that here
    widgets = {
        'name': forms.TextInput(attrs={'placeholder': 'Enter category name'}),
    }
