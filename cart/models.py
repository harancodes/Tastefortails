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
from customadmin.models import Notification

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

        price = self.product_variant.sales_price or self.product_variant.variant_price
        return price * self.quantity


    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant.weight})"

    def clean(self):
    
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        if self.product_variant.quantity_in_stock < self.quantity:
            raise ValidationError(
                f"Not enough stock for {self.product_variant.product.name} ({self.product_variant.weight})."
            )

    def save(self, *args, **kwargs):
       
        self.clean()
        super().save(*args, **kwargs)





from django.db import models
from decimal import Decimal

class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="orders")
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    applied_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    applied_coupon_code_frozen = models.CharField(max_length=50, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)

    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'))
    notes = models.TextField(blank=True, null=True)

    is_paid = models.BooleanField(default=False)

    @property
    def calculate_total_amount(self):
        """
        Calculate total amount without considering coupon discounts.
        """
        items_total = sum(item.total_price for item in self.items.all())
        self.total_amount = items_total + self.shipping_charge
        self.save()

   
    def calculate_final_total(self):
        """
        Calculate final total considering coupon discounts, shipping and active items.
        """
        subtotal = sum(item.total_price for item in self.items.exclude(status__in=['cancelled', 'returned']))

        self.total_amount = subtotal + self.shipping_charge

        if self.applied_coupon and subtotal >= self.applied_coupon.min_cart_value:
            self.discount = self.applied_coupon.calculate_discount(subtotal)
            self.applied_coupon_code_frozen = self.applied_coupon.code  # Store code
        else:
            self.discount = Decimal('0.00')
            self.applied_coupon = None

        self.total_amount -= self.discount
        self.save()

    @property
    def applied_coupon_code(self):
        if self.applied_coupon:
            return self.applied_coupon.code
        return self.applied_coupon_code_frozen

    @property
    def can_be_cancelled(self):
        """
        Check if at least one item can still be cancelled.
        """
        return any(item.can_be_cancelled for item in self.items.all())

    def __str__(self):
        return f"Order {self.id} - {self.user.email}"
    

    @property
    def can_download_invoice(self):
        active_items = self.items.exclude(status='cancelled')
        if not active_items.exists():
            return False  # No active items, so can't download invoice

        return all(item.status in ['delivered', 'returned'] for item in active_items)

        
    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.exclude(status__in=['cancelled', 'returned']))

    @property
    def total_shipping(self):
        return self.shipping_charge

    @property
    def total_discount(self):
        return self.discount or Decimal('0.00')

    @property
    def total_saved(self):
        return self.discount if self.discount else Decimal('0.00')

    @property
    def grand_total(self):
        return self.total_amount

    @property
    def refunded_amount(self):
        refunded = sum(item.get_estimated_amount for item in self.items.filter(status='returned'))
        return refunded
        
    @property
    def raw_items_total(self):
        return sum(item.total_price for item in self.items.all())







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
  
    ordered_unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordered_total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordered_price_after_coupon = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # In OrderItem model

    @property
    def per_unit_discount(self):
        return round(self.product_variant.sales_price - self.ordered_price_after_coupon, 2)

    @property
    def total_discount(self):
        return round(self.per_unit_discount * self.quantity, 2)

    

    @property
    def can_be_cancelled(self):
        
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
     
    


    @property
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
        return self.price_after_coupon * self.quantity



    def cancel_item(self, reason=""):
        if not self.can_be_cancelled:
            raise ValidationError("This item cannot be cancelled.")

        with transaction.atomic():
            
            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()

            self.status = "cancelled"
            self.save()

            refund_amount = (self.ordered_price_after_coupon * self.quantity).quantize(Decimal('0.01'))

            order = self.order
            if hasattr(order, 'payment') and order.payment.status == 'completed' and refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=order.user)
                wallet.add_amount(refund_amount, reason=reason or "Refund for cancelled item")



    ### return item ###

    def return_item(self, reason=""):
        if self.status == "returned":
            raise ValidationError("Item already returned.")
        if not self.can_be_returned:
            raise ValidationError("This item cannot be returned.")

        with transaction.atomic():
            self.status = "returned"
            self.return_status = "approved"
            self.save()

            
            refund_amount = (self.ordered_price_after_coupon * self.quantity).quantize(Decimal('0.01'))

            order = self.order
            if hasattr(order, 'payment') and order.payment.status == 'completed' and refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=order.user)
                wallet.add_amount(refund_amount, reason=reason or "Refund for returned item")

            # Restock the item
            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()


    # def return_item(self, reason=""):
    #     if self.status == "returned":
    #         raise ValidationError("Item already returned.")
    #     if not self.can_be_returned:
    #         raise ValidationError("This item cannot be returned.")

    #     with transaction.atomic():
    #         order = self.order

    #         self.status = "returned"
    #         self.return_status = "approved"
    #         self.save()

    #         # Refund the frozen total paid for this item (with or without coupon)
    #         refund_amount = self.ordered_total_price or self.total_after_coupon

    #         if hasattr(order, 'payment') and order.payment.status == 'completed' and refund_amount > 0:
    #             wallet, _ = Wallet.objects.get_or_create(user=order.user)
    #             wallet.add_amount(refund_amount, reason=reason or "Refund for returned item")

    #         # Add stock back
    #         self.product_variant.quantity_in_stock += self.quantity
    #         self.product_variant.save()



###3

    @property
    def price_after_coupon(self):
        order = self.order
        active_items = order.items.exclude(status__in=['cancelled', 'returned'])

        # Base subtotal (no coupon applied yet)
        subtotal = sum(item.product_variant.sales_price * item.quantity for item in active_items)

        if not order.applied_coupon or order.discount <= 0 or subtotal <= 0:
            return self.product_variant.sales_price

        # Total of this item (before coupon)
        item_total = self.product_variant.sales_price * self.quantity

        # Share of discount for this item
        item_share_ratio = item_total / subtotal
        discount_share = (order.discount * item_share_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        unit_discount = discount_share / self.quantity
        discounted_price = self.product_variant.sales_price - unit_discount

        return discounted_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @property
    def total_after_coupon(self):
        """Returns total paid for this item after applying coupon (if any)."""
        return (self.price_after_coupon or self.product_variant.sales_price) * self.quantity

    @property
    def discount_share(self):
        order = self.order
        active_items = order.items.exclude(status__in=['cancelled', 'returned'])

        subtotal = sum(item.original_unit_price * item.quantity for item in active_items)

        if not order.applied_coupon or order.discount <= 0 or subtotal <= 0:
            return Decimal("0.00")

        item_total = self.original_unit_price * self.quantity
        ratio = item_total / subtotal
        return (order.discount * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)



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

    # def approve_return(self):
    #     if self.return_status != "requested":
    #         raise ValueError("This return request is not in a valid state.")

    #     # Handle stock and refund logic here

    #     self.return_status = "approved"
    #     self.status = "returned"
    #     self.save()


    # def reject_return(self, rejection_reason=""):
    #     if self.return_status != "requested":
    #         raise ValueError("This return request is not in a valid state to reject.")

    #     self.return_status = "rejected"
    #     self.return_reason = rejection_reason
    #     self.save()


    # @property
    # def total_price(self):
    #     return self.product_variant.sales_price* self.quantity

    def approve_return(self):
        if self.return_status != "requested":
            raise ValueError("This return request is not in a valid state.")

        order_user = self.order.user  # Save user reference early (avoid accessing self.order.user later)

        with transaction.atomic():
            # Update statuses
            self.status = "returned"
            self.return_status = "approved"
            self.save()

            # Refund logic
            refund_amount = (self.ordered_price_after_coupon * self.quantity).quantize(Decimal('0.01'))

            order = self.order
            if hasattr(order, 'payment') and order.payment.status == 'completed' and refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=order_user)
                wallet.add_amount(refund_amount, reason="Refund for approved return")

            # Restock the item
            self.product_variant.quantity_in_stock += self.quantity
            self.product_variant.save()

        
        Notification.objects.create(
            user=order_user,
            message=f"Refund Accepted: Your refund for '{self.product_variant.product.name}' has been processed successfully.",
            is_read=False
        )


    def reject_return(self, rejection_reason=""):
        if self.return_status != "requested":
            raise ValueError("This return request is not in a valid state to reject.")

        order_user = self.order.user

        with transaction.atomic():
            self.return_status = "rejected"
            self.return_reason = rejection_reason
            self.save()

  
        Notification.objects.create(
            user=order_user,
            message=f"Refund Rejected: Your refund for '{self.product_variant.product.name}' was rejected. Reason: {rejection_reason}",
            is_read=False
        )


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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="wallet")
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
    







    

