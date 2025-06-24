from django.db import models
from authentication.models import CustomUser, Address
from product.models import Variant , Products
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from customadmin.models import Coupon
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from customadmin.models import UsedCoupon

from decimal import Decimal, ROUND_HALF_UP


class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.email}"
    
    @property
    def total_price(self):
    
        total = sum(item.total_price for item in self.items.all())  
        return total



from django.db import models
from django.core.exceptions import ValidationError

class CartItem(models.Model):
    cart = models.ForeignKey(
        'cart.Cart',  
        on_delete=models.CASCADE,
        related_name="items"
    )
    product_variant = models.ForeignKey(
        'product.Variant',  
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
        """Return total price of this item (unit price * quantity). Uses offer/sales price if available."""
        price = self.product_variant.sales_price or self.product_variant.variant_price
        return price * self.quantity


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
    is_paid = models.BooleanField(default=False)



    def calculate_total_amount(self):
        items_total = sum(item.total_price for item in self.items.all())
        self.total_amount = items_total + self.shipping_charge
        self.save()

    def __str__(self):
        return f"Order {self.id} - {self.user.email}"
    

    def calculate_final_total(self):
        subtotal = sum(item.total_price for item in self.items.exclude(status__in=['cancelled', 'returned']))

        self.total_amount = subtotal + self.shipping_charge
        if self.applied_coupon and subtotal >= self.applied_coupon.min_cart_value:
            self.discount = self.applied_coupon.calculate_discount(subtotal)
        else:
            self.discount = 0
            self.applied_coupon = None
        self.total_amount -= self.discount
        self.save()



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

    ALLOWED_STATUS_TRANSITIONS = {
    'pending': ['processing'],
    'processing': ['shipped'],
    'shipped': ['delivered'],
    'delivered': [],
    'cancelled': [],
    'returned': []
}

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
    


    def get_estimated_amount(self):
      
        order = self.order
        active_items = order.items.exclude(status__in=['cancelled', 'returned'])

        total_active_price = sum(item.total_price for item in active_items)
        total_items = active_items.count()

        if total_items <= 0 or total_active_price <= 0:
            return Decimal('0.00')

        
        shipping_share = order.shipping_charge / total_items

    
        discount_share = Decimal('0.00')
        if order.applied_coupon and order.discount > 0:
            item_share_ratio = self.total_price / total_active_price
            discount_share = (order.discount * item_share_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        refund = (self.total_price + shipping_share - discount_share).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return refund
    @property
    def total_price(self):
        return (self.price_after_coupon or self.product_variant.sales_price) * self.quantity

        
    def cancel_item(self, reason=""):
        if not self.can_be_cancelled:
            raise ValidationError("This item cannot be cancelled.")

        with transaction.atomic():
            order = self.order

            
            old_paid_amount = order.total_amount
            active_items_count = order.items.exclude(status__in=["cancelled", "returned"]).count()

            if active_items_count <= 0:
                raise ValidationError("No active items in order.")

            per_item_shipping = order.shipping_charge / active_items_count

            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()
            self.status = "cancelled"
            self.save()

            order.calculate_final_total()
            new_paid_amount = order.total_amount

            if hasattr(order, 'payment') and order.payment.status == 'completed':
                wallet, _ = Wallet.objects.get_or_create(user=order.user)
           
                refund = (old_paid_amount - new_paid_amount ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                if refund > 0:
                    wallet.add_amount(refund, reason="Order item cancelled - refund incl. shipping share")

 ### return item ###

    def return_item(self, reason=""):
        if self.status == "returned":
            raise ValidationError("Item already returned.")
        if not self.can_be_returned:
            raise ValidationError("This item cannot be returned.")

        with transaction.atomic():
            order = self.order

            old_paid_amount = order.total_amount

            # Mark returned
            self.status = "returned"
            self.return_status = "approved"
            self.save()

            # Recalculate coupon + totals
            order.calculate_final_total()

            new_paid_amount = order.total_amount
            refund_amount = (old_paid_amount - new_paid_amount).quantize(Decimal('0.01'))

            print(f"Refund: ₹{refund_amount} (Old: {old_paid_amount}, New: {new_paid_amount})")

            if hasattr(order, 'payment') and order.payment.status == 'completed' and refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=order.user)
                wallet.add_amount(refund_amount, reason=reason or "Refund for returned item")

            # Restock inventory
            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()


###3


    @property
    def price_after_coupon(self):
        order = self.order
        active_items = order.items.exclude(status__in=['cancelled', 'returned'])
        subtotal = sum(item.total_price for item in active_items)

        if not order.applied_coupon or order.discount <= 0 or subtotal <= 0:
            return self.product_variant.sales_price

        item_share_ratio = self.total_price / subtotal
        discount_share = (order.discount * item_share_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        effective_price = (self.total_price - discount_share) / self.quantity

        return effective_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


    def change_status(self, new_status):
        allowed = self.ALLOWED_STATUS_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(f"Invalid status transition from {self.status} to {new_status}")

        self.status = new_status
        self.save()


    @property
    def status_choices(self):

        return self.STATUS_CHOICES
    
    @property
    def allowed_transitions(self):
        return self.ALLOWED_STATUS_TRANSITIONS.get(self.status, [])



    @property
    def total_price(self):
        return self.product_variant.sales_price* self.quantity

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
    







    

