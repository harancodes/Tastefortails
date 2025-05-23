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


        cart, created = Cart.objects.get_or_create(user=request.user)

        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product_variant=variant)

        if created:
            cart_item.quantity = 1  # Set initial quantity to 1
        else:
            # Check if adding one more exceeds available stock
            if cart_item.quantity + 1 > variant.quantity_in_stock:
                return JsonResponse({'success': False, 'error': 'Insufficient stock available'}, status=400)
            
            cart_item.quantity += 1  # Increment quantity if already in cart

        cart_item.save()  # Save the cart item

        # Update cart total price
        cart_item_count = cart.items.count()
        total_price = cart.total_price

        return JsonResponse({
            'success': True,
            'total_price': total_price,
            'cart_item_count': cart_item_count
        })
    else:
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

        cart_item.quantity = new_quantity
        cart_item.save()

        # Calculate the new item total price
        item_total_price = cart_item.total_price

        # Calculate the new cart total price
        cart_total_price = cart_item.cart.total_price

        return JsonResponse({
            'item_total_price': item_total_price,
            'cart_total_price': cart_total_price
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    except ValueError:
        return JsonResponse({'error': 'Invalid quantity value'}, status=400)


@block_superuser_navigation
@never_cache
@login_required_custom
def remove_cart_item(request, item_id):
    if request.method == 'POST':
        # Fetch the CartItem object
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        
        # Remove the item from the cart
        cart_item.delete()

        # Calculate the new cart total price
        cart_total_price = sum(item.quantity * item.product_variant.product.variant_price for item in cart_item.cart.items.all())

        # Return success response with updated cart total price
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
        items = cart.items.all()
        return render(request, 'cart.html', {'cart': cart, 'items': items})
    else:
        return render(request, 'cart.html', {'message': 'Your cart is empty.'})



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
                return redirect("home")  # Adjust if needed with namespace
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

            # original_total_price_str = request.POST.get("original_total_price")
            # discounted_total_price_str = request.POST.get("discounted_total_price")

            # if original_total_price_str is None:
            #     messages.error(request, "Original total price is missing.")
            #     return redirect("cart:checkout")

            # try:
            #     original_total_price = float(original_total_price_str)
            # except ValueError:
            #     messages.error(request, "Invalid original total price.")
            #     return redirect("cart:checkout")

            # if discounted_total_price_str:
            #     try:
            #         discounted_total_price = float(discounted_total_price_str)
            #     except ValueError:
            #         messages.error(request, "Invalid discounted total price.")
            #         return redirect("cart:checkout")
            # else:
            #     discounted_total_price = original_total_price

            # if discounted_total_price:
            #     total_price = Decimal(discounted_total_price) + shipping_charge
            # else:
            #     total_price = Decimal(original_total_price) + shipping_charge

            # if not address_id or not payment_method:
            #     messages.error(request, "Please select an address and payment method.")
            #     return redirect("cart:checkout")

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

        return render(
            request,
            "checkout.html",
            {
                "cart_items": cart_items if not variant_id else [],
                "cart_total": cart_total,
                "discount": discount,
                "total_price": total_price,
                "shipping_charge": shipping_charge,
                "wallet": wallet,
                "addresses": Address.objects.filter(user=request.user),
                "buy_now_item": single_variant if variant_id else None,
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
                "cart_total": cart_total,
                "discount": discount,
                "total_price": total_price,
                "shipping_charge": shipping_charge,
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

        # Adjust quantity if needed
        if cart_item.quantity > variant_stock:
            cart_item.quantity = variant_stock

        # Update the variant
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
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order_items = OrderItem.objects.filter(order=order)

        return render(request, "order_success.html", {
            "order": order,
            "order_items": order_items,
        })
    except Exception as e:
        print("Error in order_success view:", e)
        messages.error(request, "There was a problem loading your order.")
        return redirect("home")
