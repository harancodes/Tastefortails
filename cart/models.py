from django.db import models
from authentication.models import CustomUser, Address
from product.models import Variant , Products
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from customadmin.models import Coupon
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.email}"

    @property
    def total_price(self):
        # total = sum(item.product_variant.variant_price for item in self.items.all())
        # return total
        total = sum(item.total_price for item in self.items.all())  # use CartItem.total_price
        return total



from django.db import models
from django.core.exceptions import ValidationError

class CartItem(models.Model):
    cart = models.ForeignKey(
        'cart.Cart',  # Update this if Cart is in a different app
        on_delete=models.CASCADE,
        related_name="items"
    )
    product_variant = models.ForeignKey(
        'product.Variant',  # Make sure 'products' is the actual app label
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ['-id']

    @property
    def total_price(self):
        """Return total price of this item (unit price * quantity)."""
        return self.product_variant.variant_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant.weight})"

    def clean(self):
        """Validates quantity and stock before saving."""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        if self.product_variant.quantity_in_stock < self.quantity:
            raise ValidationError(
                f"Not enough stock for {self.product_variant.product.name} ({self.product_variant.weight})."
            )

    def save(self, *args, **kwargs):
        """Ensure model is clean before saving."""
        self.clean()
        super().save(*args, **kwargs)





class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="orders")
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    applied_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    notes = models.TextField(blank=True, null=True) 



    def calculate_total_amount(self):
        items_total = sum(item.total_price for item in self.items.all())
        self.total_amount = items_total + self.shipping_charge
        self.save()

    def __str__(self):
        return f"Order {self.id} - {self.user.email}"
    


class OrderItem(models.Model):
    CANCELLATION_WINDOW_HOURS = 24  
    RETURN_WINDOW_DAYS = 7  

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned")
    ]

    RETURN_STATUS_CHOICES = [
        ("no_request", "No Request"),
        ("requested", "Return Requested"),
        ("approved", "Return Approved"),
        ("rejected", "Return Rejected"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # order_item_id = models.CharField(max_length=36, unique=True, editable=False, default=uuid.uuid4)
    product_variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    updated_at = models.DateTimeField(auto_now=True)
    return_status = models.CharField(max_length=50, choices=RETURN_STATUS_CHOICES, default="no_request")
    return_reason = models.TextField(blank=True, null=True)

    @property
    def can_be_cancelled(self):
        """Check if this order item is eligible for cancellation"""
        if self.status not in ["pending", "processing"]:
            return False
        time_elapsed = timezone.now() - self.order.created_at
        return time_elapsed.total_seconds() <= (self.CANCELLATION_WINDOW_HOURS * 3600)

    @property
    def can_be_returned(self):
        """Check if this order item is eligible for return (within 7 days after delivery)"""
        if self.status != "delivered":
            return False
        time_elapsed = timezone.now() - self.updated_at  
        return time_elapsed.total_seconds() <= (self.RETURN_WINDOW_DAYS * 86400)  

    def cancel_item(self, reason=""):
        """Cancels this specific order item"""
        if not self.can_be_cancelled:
            raise ValidationError("This item cannot be cancelled.")

        with transaction.atomic():
            
            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()

            
            self.status = "cancelled"
            self.save()

    def return_item(self, reason=""):
        """Handles return process for this specific order item and calculates refund"""
        if not self.can_be_returned:
            raise ValidationError("This item cannot be returned.")

        with transaction.atomic():
            
            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()

            
            self.status = "returned"
            self.save()

            
            total_items = self.order.items.exclude(status="returned").count()
            per_item_shipping_charge = self.order.shipping_charge / total_items if total_items > 0 else 0
            refund_amount = self.total_price + per_item_shipping_charge

            return refund_amount  


    @property
    def total_price(self):
        return self.product_variant.variant_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant.price})"


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('refund_pending', 'Refund Pending'),
        ('refund_completed', 'Refund Completed'),
        ('refund_not_required', 'Refund Not Required'),
        ('payment_not_received', 'Payment Not Received'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=50)  
    status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='pending')  
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"


class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def add_amount(self, amount, reason="Credit"):
        """Add amount to wallet and create a transaction."""
        amount = Decimal(amount)  
        self.balance += amount
        self.save()

        
        print(f"Adding amount {amount} to wallet for {self.user.email}")

        transaction = Transaction.objects.create(
            wallet=self, amount=amount, transaction_type="CREDIT", reason=reason
        )

        
        print(f"Transaction Created: {transaction}")

        return transaction  


    def deduct_amount(self, amount, reason="Debit"):
        """Deduct amount from wallet if sufficient balance and create a transaction."""
        amount = Decimal(amount)  
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            Transaction.objects.create(wallet=self, amount=-amount, transaction_type="DEBIT", reason=reason)
            return True  
        return False  

    

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("CREDIT", "Credit"),
        ("DEBIT", "Debit"),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    reason = models.CharField(max_length=255, blank=True, null=True)  
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.timestamp}"
    







    
# class ProductReview(models.Model):
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reviews")
#     product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="reviews")
#     rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
#     review = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ('user', 'product')  

#     def __str__(self):
#         return f"{self.user.email} - {self.product.name} ({self.rating} Stars)"
