from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import CustomUser, Address
from product.models import Variant
from .models import Cart , CartItem , Order, Payment
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import JsonResponse 
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem, Order
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import json
from .models import Wallet
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from authentication.views import block_superuser_navigation
from customadmin.models import Coupon, UsedCoupon
from product.views import login_required_custom
from wishlist.models import Wishlist, WishlistItem
import razorpay

# 


@block_superuser_navigation
@never_cache
@login_required_custom
def add_to_cart(request, variant_id):
    if request.method == 'POST':
        if not variant_id:
            return JsonResponse({'success': False, 'error': 'Variant ID is missing'}, status=400)

        try:
            variant = Variant.objects.get(id=variant_id)
        except Variant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product variant not found'}, status=404)

        # ✅ Parse quantity from request body
        try:
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)

        if quantity < 1:
            return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'}, status=400)

        if quantity > variant.quantity_in_stock:
            return JsonResponse({'success': False, 'error': 'Insufficient stock available'}, status=400)

        if quantity > 10:
            return JsonResponse({'success': False, 'error': 'Maximum allowed quantity is 10'}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product_variant=variant)

        if created:
            cart_item.quantity = quantity
        else:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.quantity_in_stock:
                return JsonResponse({'success': False, 'error': 'Insufficient stock available'}, status=400)
            if new_quantity > 10:
                return JsonResponse({'success': False, 'error': 'Maximum allowed quantity is 10'}, status=400)
            cart_item.quantity = new_quantity

        cart_item.save()

        # ✅ Remove from wishlist
        try:
            wishlist = request.user.wishlist  
            WishlistItem.objects.filter(wishlist=wishlist, variant=variant).delete()
        except Wishlist.DoesNotExist:
            pass

        cart_item_count = cart.items.count()
        total_price = cart.total_price

        return JsonResponse({
            'success': True,
            'total_price': total_price,
            'cart_item_count': cart_item_count
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)




@block_superuser_navigation
@never_cache
@login_required_custom
@require_POST
def update_quantity(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        new_quantity = data.get('quantity')

        if item_id is None or new_quantity is None:
            return JsonResponse({'error': 'Invalid request data'}, status=400)

        new_quantity = int(new_quantity)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if new_quantity > cart_item.product_variant.quantity_in_stock:
            return JsonResponse({'error': 'Requested quantity exceeds available stock'}, status=400)
        
        elif new_quantity > 10:
            return JsonResponse({'error': 'Please order quantity 10 or less from the available stock'}, status=400)

        cart_item.quantity = new_quantity
        cart_item.save()

        return JsonResponse({'success': True})

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)



@block_superuser_navigation
@never_cache
@login_required_custom
def remove_cart_item(request, item_id):
    if request.method == 'POST':
        
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        
        
        cart_item.delete()


        cart_total_price = sum(
    item.quantity * item.product_variant.product.variant_price
    for item in cart_item.cart.items.all()
)


        
        return JsonResponse({
            'message': 'Item removed from cart.',
            'cart_total_price': cart_total_price
        }, status=200)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)


@block_superuser_navigation
@never_cache
@login_required_custom
def view_cart(request):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        items = cart.items.select_related("product_variant", "product_variant__product")  
        cart_total_price = sum(item.total_price for item in items)

        return render(request, 'cart.html', {
            'cart': cart,
            'items': items,
            'cart_total_price': cart_total_price,
        })
    else:
        return render(request, 'cart.html', {
            'message': 'Your cart is empty.',
            'cart_total_price': 0
        })




@block_superuser_navigation
@never_cache
@login_required_custom
def checkout(request):
    try:
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        variant_id = request.GET.get("variant_id")
        is_buy_now = bool(variant_id)
        single_variant = None
        single_quantity = 1

        if is_buy_now:
            single_variant = get_object_or_404(Variant, id=variant_id)
            cart_items = []
            cart_total = single_variant.product.variant_price
        else:
            cart_items = CartItem.objects.filter(cart=user_cart)
            if not cart_items.exists():
                messages.error(request, "Your cart is empty!")
                return redirect("product:list")  
            cart_total = user_cart.total_price

        discount = 0
        total_price = cart_total
        applied_coupon = None

        applied_coupon_data = request.session.get("applied_coupon")
        if applied_coupon_data and 'id' in applied_coupon_data:
            try:
                coupon_id = applied_coupon_data['id']
                applied_coupon = Coupon.objects.get(id=coupon_id, is_active=True)

                if cart_total >= applied_coupon.min_cart_value:
                    cart_total = Decimal(cart_total)
                    discount = Decimal(
                        applied_coupon_data.get('discount_amount', applied_coupon.calculate_discount(cart_total))
                    )
                    total_price = max(cart_total - discount, Decimal(0))
                else:
                    request.session.pop("applied_coupon", None)

            except Coupon.DoesNotExist:
                request.session.pop("applied_coupon", None)

        shipping_charge = Decimal(100)

        if request.method == "POST":
            address_id = request.POST.get("address")
            payment_method = request.POST.get("payment_method")

            original_total_price_str = request.POST.get("original_total_price")
            discounted_total_price_str = request.POST.get("discounted_total_price")

            if original_total_price_str is None:
                messages.error(request, "Original total price is missing.")
                return redirect("cart:checkout")

            try:
                original_total_price = float(original_total_price_str)
            except ValueError:
                messages.error(request, "Invalid original total price.")
                return redirect("cart:checkout")

            if discounted_total_price_str:
                try:
                    discounted_total_price = float(discounted_total_price_str)
                except ValueError:
                    messages.error(request, "Invalid discounted total price.")
                    return redirect("cart:checkout")
            else:
                discounted_total_price = original_total_price

            if discounted_total_price:
                total_price = Decimal(discounted_total_price) + shipping_charge
            else:
                total_price = Decimal(original_total_price) + shipping_charge

            if not address_id or not payment_method:
                messages.error(request, "Please select an address and payment method.")
                return redirect("cart:checkout")

            try:
                shipping_address = Address.objects.get(user=request.user, id=address_id)
            except Address.DoesNotExist:
                messages.error(request, "Invalid address selection.")
                return redirect("cart:checkout")

            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=shipping_address,
                    total_amount=total_price,
                    discount=discount,
                    applied_coupon=applied_coupon if applied_coupon else None,
                    shipping_charge=shipping_charge,
                )

                if applied_coupon:
                    UsedCoupon.objects.create(user=request.user, coupon=applied_coupon)
                    request.session.pop("applied_coupon", None)

                if is_buy_now and single_variant:
                    if single_variant.quantity_in_stock < single_quantity:
                        messages.error(
                            request,
                            f"Not enough stock for {single_variant.product.name} ({single_variant.weight})",
                        )
                        return redirect("product_detail", pk=single_variant.product.id)

                    single_variant.quantity_in_stock -= single_quantity
                    single_variant.save()

                    OrderItem.objects.create(
                        order=order,
                        product_variant=single_variant,
                        quantity=single_quantity,
                        status="processing",
                    )
                else:
                    for cart_item in cart_items:
                        variant = cart_item.product_variant
                        if variant.quantity_in_stock < cart_item.quantity:
                            messages.error(
                                request,
                                f"Not enough stock for {variant.product.name} ({variant.weight})",
                            )
                            return redirect("view_cart")

                        variant.quantity_in_stock -= cart_item.quantity
                        variant.save()

                        OrderItem.objects.create(
                            order=order,
                            product_variant=variant,
                            quantity=cart_item.quantity,
                            status="processing",
                        )

                # Wallet Payment Logic
                if payment_method == "wallet":
                    wallet.refresh_from_db()
                    total_price_decimal = Decimal(total_price)

                    if wallet.deduct_amount(total_price_decimal, reason=f"Payment for Order {order.id}"):
                        Payment.objects.create(
                            order=order,
                            amount=total_price_decimal,
                            transaction_id=f"wallet_{order.id}",
                            payment_method="wallet",
                            status="completed",
                        )

                        if not is_buy_now:
                            cart_items.delete()

                        messages.success(request, "Payment successful! Your order has been placed.")
                        return redirect("cart:order_success", order_id=order.id)
                    else:
                        messages.error(
                            request, "Insufficient wallet balance. Please choose another payment method."
                        )
                        return redirect("cart:checkout")

                elif payment_method == "cod":
                    Payment.objects.create(
                        order=order,
                        amount=total_price,
                        transaction_id=f"cod_{order.id}",
                        payment_method="cod",
                        status="pending",
                    )

                    if not is_buy_now:
                        cart_items.delete()
                    return redirect("cart:order_success", order_id=order.id)
                
        total_price_with_shipping = total_price + shipping_charge

        return render(
            request,
            "checkout.html",
            {
                "cart_items": cart_items if not variant_id else [],
                "cart_total": float(cart_total),
                "discount": discount,
                "total_price": float(total_price),
                "shipping_charge": float(shipping_charge),
                "wallet": wallet,
                "addresses": Address.objects.filter(user=request.user),
                "buy_now_item": single_variant if variant_id else None,
                "total_price_with_shipping": total_price_with_shipping
            },
        )

    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        messages.error(request, f"Error: {str(e)}")

        return render(
            request,
            "checkout.html",
            {
                "cart_items": cart_items if not variant_id else [],
                "cart_total": float(cart_total),
                "discount": discount,
                "total_price": float(total_price),
                "shipping_charge": float(shipping_charge),
                "wallet": wallet,
                "addresses": Address.objects.filter(user=request.user),
                "buy_now_item": single_variant if variant_id else None,
                "error": str(e),
            },
        )

@block_superuser_navigation
@never_cache
@login_required_custom
def buy_now(request, variant_id):
    try:
        variant = get_object_or_404(Variant, id=variant_id)

        if variant.quantity_in_stock < 1:
            messages.error(request, f"{variant.product.name} ({variant.weight}) is out of stock!")
            return redirect('product_detail', pk=variant.product.id)
        
        return redirect(f"{reverse('cart:checkout')}?variant_id={variant_id}")
    
    except Variant.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect('home')  
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('home')



from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
import json

@block_superuser_navigation
@never_cache
@login_required_custom
@require_POST
def update_variant(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        variant_id = data.get('variant_id')

        if item_id is None or variant_id is None:
            return JsonResponse({'error': 'Invalid request data'}, status=400)

        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        new_variant = get_object_or_404(Variant, id=variant_id)

        if new_variant.product.id != cart_item.product_variant.product.id:
            return JsonResponse({'error': 'Invalid variant for this product'}, status=400)

        variant_stock = new_variant.quantity_in_stock

        if variant_stock <= 0:
            return JsonResponse({'error': 'Selected variant is out of stock'}, status=400)

        # Adjust quantity 
        if cart_item.quantity > variant_stock:
            cart_item.quantity = variant_stock

        # Update 
        cart_item.product_variant = new_variant
        cart_item.save()

        
        cart_total = sum(item.total_price for item in cart_item.cart.items.all())

        response_data = {
            'success': True,
            'variant_weight': new_variant.weight,
            'variant_stock': variant_stock,
            'item_total_price': float(cart_item.total_price),  
            'cart_total_price': float(cart_total)
        }

        # Optional: Add image URL if available
        if hasattr(new_variant, 'image1') and new_variant.image1:
            response_data['variant_image'] = new_variant.image1.url

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@block_superuser_navigation
@never_cache
@login_required
def order_success(request, order_id):
    print("Order Success View: order_id =", order_id)
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    return render(request, "order_success.html", {
            "order": order,
            "order_items": order_items,
        })
    
@require_POST
@block_superuser_navigation
@never_cache
@login_required
def apply_coupon(request):
    data = json.loads(request.body)
    coupon_code = data.get("coupon_code", "").strip()
    cart_total = float(data.get("cart_total", 0))

    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)

        # Check if the coupon has already been used by the user
        if UsedCoupon.objects.filter(user=request.user, coupon=coupon).exists():
            return JsonResponse({"valid": False, "message": "This coupon has already been used."})

        # Validate minimum cart value
        if cart_total < float(coupon.min_cart_value):
            return JsonResponse({"valid": False, "message": f"Minimum cart value to use this coupon is ₹{coupon.min_cart_value}."})

        # Calculate the discount amount using the model method
        discount_amount = coupon.calculate_discount(cart_total)

        # Save applied coupon & discount amount in session
        request.session['applied_coupon'] = {
            "id": coupon.id,
            "code": coupon.code,
            "discount_amount": float(discount_amount)
        }
        request.session.modified = True

        return JsonResponse({"valid": True, "discount_amount": float(discount_amount)})

    except Coupon.DoesNotExist:
        return JsonResponse({"valid": False, "message": "Invalid or expired coupon."})



@require_POST
@block_superuser_navigation
@never_cache
@login_required
def remove_coupon(request):
    if 'applied_coupon' in request.session:
        del request.session['applied_coupon']
        request.session.modified = True
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "message": "No coupon applied."})


# @block_superuser_navigation
# @never_cache
# @login_required
# def order_success(request, order_id):
#     order = get_object_or_404(Order, id=order_id, user=request.user)
#     order_items = OrderItem.objects.filter(order=order)

#     return render(request, 'order_success.html', {'order_id': order_id, 'order_items': order_items})


@receiver(post_save, sender=CustomUser)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)




@block_superuser_navigation
@never_cache
@login_required
def create_razorpay_order(request):
    if request.method == "POST":
        data = json.loads(request.body)
        amount = data.get("amount", 0)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })

        order = Order.objects.create(
            user=request.user,
            total_amount=amount / 100,
            razorpay_order_id=razorpay_order["id"],
        )

        return JsonResponse({
            "id": razorpay_order["id"],  
            "amount": razorpay_order["amount"],
        })



@block_superuser_navigation
@never_cache
@login_required
def verify_razorpay_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get("razorpay_order_id")
            payment_id = data.get("payment_id")
            signature = data.get("signature")

            # Fetch order details
            order = Order.objects.get(razorpay_order_id=order_id)
            payment = Payment.objects.get(order=order)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params_dict = {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }

            try:
                client.utility.verify_payment_signature(params_dict)
                payment_successful = True
            except razorpay.errors.SignatureVerificationError:
                payment_successful = False

            with transaction.atomic():
                # Update payment status
                if payment_successful:
                    payment.status = "completed"
                    payment.transaction_id = payment_id
                    OrderItem.objects.filter(order=order).update(status="processing")
                    CartItem.objects.filter(cart__user=order.user).delete()
                else:
                    payment.status = "payment_not_received"  # Mark as failed but allow retry
                    order.save()

                payment.save()

            return JsonResponse({"success": True, "order_id": order.id, "payment_success": payment_successful})

        except Order.DoesNotExist:
            return JsonResponse({"success": False, "error": "Order not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)


@csrf_exempt
@block_superuser_navigation
@never_cache
@login_required
def pay_later(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.payment.status == "payment_not_received":
        order.payment.status = "pending"
        order.payment.save()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False, "error": "Payment is already completed or not eligible for pay later."})

@csrf_exempt
@block_superuser_navigation
@never_cache
@login_required
def retry_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.payment.status == "payment_not_received":
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "receipt": f"order_{order.id}",
            "payment_capture": 1
        })

        # Update Razorpay Order ID and Payment
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        # order.payment.transaction_id = razorpay_order['id']
        # order.payment.status = "pending"
        # order.payment.save()

        return JsonResponse({
            "razorpay_order_id": razorpay_order['id'], 
            "amount": order.total_amount,
            "order_id": order.id
        })
    else:
        return JsonResponse({"success": False, "error": "Payment is already completed or not eligible for retry."})
    

@csrf_exempt
@block_superuser_navigation
@never_cache
@login_required
def verify_payment(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Parse request body
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        # Verify payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        if client.utility.verify_payment_signature(params_dict):
            # Fetch payment details
            payment = client.payment.fetch(razorpay_payment_id)
            
            if payment['status'] == 'captured':
                # Update Order Payment Status
                order.payment.status = 'completed'
                order.payment.transaction_id = razorpay_payment_id
                order.payment.save()

                return JsonResponse({"success": True, "message": "Payment verified successfully!"})
            else:
                return JsonResponse({"success": False, "error": "Payment not captured."})

        return JsonResponse({"success": False, "error": "Invalid payment signature."})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@block_superuser_navigation
@never_cache
@login_required
def razorpay_payment_success(request):
    return JsonResponse({"message": "Payment Successful"})

