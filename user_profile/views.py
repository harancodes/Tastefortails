from . import views
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import  login_required
from authentication.views import block_superuser_navigation
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect, render, get_object_or_404
from authentication.models import Address, CustomUser
from django.http import JsonResponse
from cart.models import Order, OrderItem
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Spacer, Table, Paragraph, SimpleDocTemplate, TableStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage , PageNotAnInteger
from product.models import Products, Review
from cart.models import Wallet
from decimal import Decimal
import re
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
import random
import string



#### address management ####3

@block_superuser_navigation
@login_required
@never_cache
def manage_address(request):
    addresses = Address.objects.filter(user=request.user)  
    return render(request, 'manage_address.html', {'addresses': addresses})





from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

@block_superuser_navigation
@login_required
@never_cache
def add_address(request):
    if request.method == "POST":
        try:
            logger.info(f"POST data: {request.POST}")
            logger.info(f"Content type: {request.content_type}")
            
            
            name = request.POST.get("name")
            phone = request.POST.get("phone")
            address_line = request.POST.get("address_line")
            address_type = request.POST.get("address_type")
            city = request.POST.get("city")
            state = request.POST.get("state")
            postal_code = request.POST.get("postal_code")
            country = request.POST.get("country")
            
            
            required_fields = {
                'name': name,
                'phone': phone,
                'address_line': address_line,
                'address_type': address_type,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'country': country
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                return JsonResponse({
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }, status=400)
            
            
            address = Address(
                user=request.user,
                name=name,
                phone=phone,
                address_line=address_line,
                address_type=address_type,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country
            )
            address.save()
            
            logger.info(f"Address saved successfully with ID: {address.id}")
            
            return JsonResponse({
                "success": True,
                "address": {
                    "id": address.id,
                    "name": address.name,
                    "phone": address.phone,
                    "address_line": address.address_line,
                    "address_type": address.address_type,
                    "city": address.city,
                    "state": address.state,
                    "postal_code": address.postal_code,
                    "country": address.country
                }
            }, status=201)
            
        except Exception as e:
            logger.error(f"Error in add_address: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": f"An error occurred: {str(e)}"
            }, status=500)
    
    return JsonResponse({
        "success": False,
        "error": "Only POST method is allowed."
    }, status=405)

@block_superuser_navigation
@login_required
@never_cache
def edit_address(request, address_id):

    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == "POST":
        
        address.name = request.POST.get("name")
        address.phone = request.POST.get("phone")
        address.address_line = request.POST.get("address_line")
        address.address_type = request.POST.get("address_type")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.postal_code = request.POST.get("postal_code")
        address.country = request.POST.get("country")
        

        try:
            address.save() 
            return JsonResponse({"success": True}, status=200) 
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)  

    return JsonResponse({"error": "Invalid request method."}, status=400)


@block_superuser_navigation
@login_required
@never_cache
def delete_address(request, address_id):
    if request.method == "DELETE":
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        if address.orders.exists():
            return JsonResponse({
                "error": "This address cannot be deleted as it is associated with one or more orders. Please add a new address instead.",
                "type": "address_in_use"
            }, status=400)
        
        try:
            address.delete()
            return JsonResponse({"success": True}, status=200)
        except Exception as e:
            return JsonResponse({
                "error": "An error occurred while deleting the address.",
                "details": str(e)
            }, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=400)

#### address ends ###3

##### order starts ####

from collections import defaultdict

@block_superuser_navigation
@never_cache
@login_required
def order_list_view(request):
    orders_list = Order.objects.filter(user=request.user, is_paid=False).order_by('-created_at')

    status = request.GET.get('status')
    if status:
        orders_list = orders_list.filter(items__status=status).distinct()

    paginator = Paginator(orders_list, 5)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    for order in orders:
        grouped_items = defaultdict(list)
        for item in order.items.all():
            grouped_items[item.product_variant.product].append(item)
        order.grouped_items = grouped_items.items()  

    return render(request, 'order_list.html', {'orders': orders})


from django.http import HttpResponse, HttpResponseForbidden


from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib import messages
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch


@block_superuser_navigation
@never_cache
@login_required
def generate_order_invoice(request, order_id):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from decimal import Decimal

    order = get_object_or_404(Order, id=order_id, user=request.user)
    valid_items = order.items.filter(status__in=["delivered", "returned"])

    if not valid_items.exists():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Invoice is only available after items are delivered or returned.'}, status=403)
        messages.error(request, "Invoice is only available after items are delivered or returned.")
        return redirect('orders:order_detail', order_id=order.id)

    user = order.user
    address = order.shipping_address

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_order_{order.id}.pdf"'

    pdf = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=12, alignment=TA_CENTER)
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=12, spaceAfter=6, textColor=colors.darkblue)
    normal_style = styles['BodyText']

    content = [
        Paragraph("Invoice", title_style),
        Spacer(1, 12),
        Paragraph("Taste for Tails", header_style),
        Paragraph("Kochi", normal_style),
        Spacer(1, 12),
        Paragraph("Bill To:", header_style),
        Paragraph(f"{user.full_name}", normal_style),
        Paragraph(f"Email: {user.email}", normal_style),
    ]

    if address:
        content += [
            Paragraph(f"{address.address_line}", normal_style),
            Paragraph(f"{address.city}, {address.state} {address.postal_code}", normal_style),
            Paragraph(f"{address.country}", normal_style)
        ]
    content.append(Spacer(1, 12))

    content.append(Paragraph("Order Items", header_style))
    item_data = [["Product", "Qty", "Status", "Unit Price", "After Discount", "Total Paid"]]

    for item in valid_items:
        variant = item.product_variant

        item_data.append([
            Paragraph(f"{variant.product.name} ({variant.weight})", normal_style),
            str(item.quantity),
            item.status.capitalize(),
            f"Rs {item.ordered_unit_price}",
            f"Rs {item.ordered_price_after_coupon}",
            f"Rs {item.ordered_total_price}",
        ])

    item_table = Table(item_data, colWidths=[2.4 * inch, 0.6 * inch, 0.9 * inch, 1.0 * inch, 1.2 * inch, 1.2 * inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))
    content.append(item_table)
    content.append(Spacer(1, 12))

    content.append(Paragraph("Order Summary", header_style))
    summary_data = [
        ["Order ID", str(order.id)],
        ["Coupon Used", order.applied_coupon.code if order.applied_coupon else "None"],
        ["Order Discount", f"Rs {order.discount}"],
        ["Shipping Charge", f"Rs {order.shipping_charge}"],
        ["Final Order Total", f"Rs {order.total_amount}"],
    ]

    summary_table = Table(summary_data, colWidths=[2.2 * inch, 4.2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 12))
    content.append(Paragraph("Thank you for your purchase!", normal_style))

    pdf.build(content)
    return response


@block_superuser_navigation
@never_cache
@login_required
def generate_invoice(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)

    # if item.status != "delivered":
    #     return HttpResponseForbidden("Invoice is only available after item is delivered.")

    user = item.order.user
    address = item.order.shipping_address

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{item.id}.pdf"'

    pdf = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=12, alignment=TA_CENTER)
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=12, spaceAfter=6, textColor=colors.darkblue)
    normal_style = styles['BodyText']

    content = []
    content.append(Paragraph("Invoice", title_style))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Taste for Tails", header_style))
    content.append(Paragraph("Kochi", normal_style))
    content.append(Spacer(1, 12))

    # Billing details
    content.append(Paragraph("Bill To:", header_style))
    content.append(Paragraph(f"{user.full_name}", normal_style))
    content.append(Paragraph(f"Email: {user.email}", normal_style))
    if address:
        content.append(Paragraph(f"{address.address_line}", normal_style))
        content.append(Paragraph(f"{address.city}, {address.state} {address.postal_code}", normal_style))
        content.append(Paragraph(f"{address.country}", normal_style))
    content.append(Spacer(1, 12))

    # Pricing
    price_after_coupon = item.price_after_coupon
    total_paid = (price_after_coupon * item.quantity).quantize(Decimal("0.01"))

    # Order details
    content.append(Paragraph("Order Details", header_style))
    order_details = [
        ["Order ID", item.order.id],
        ["Product", Paragraph(item.product_variant.product.name, normal_style)],
        ["Quantity", item.quantity],
        ["Original Price per unit", f"Rs {item.product_variant.sales_price}"],
        ["Price per unit (after discount)", f"Rs {price_after_coupon}"],
        ["Total Paid (incl. discount)", f"Rs {total_paid}"],
        ["Coupon Used", item.order.applied_coupon.code if item.order.applied_coupon else "None"],
        ["Order Discount", f"Rs {item.order.discount}"],
        ["Shipping Charge", f"Rs {item.order.shipping_charge}"],
        ["Final Order Total", f"Rs {item.order.total_amount}"],
    ]

    table = Table(order_details, colWidths=[1.8 * inch, 4.2 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))

    content.append(table)
    content.append(Spacer(1, 12))
    content.append(Paragraph("Thank you for your purchase!", normal_style))

    pdf.build(content)
    return response



@block_superuser_navigation
@never_cache
@login_required
def order_item_detail(request, item_id):
    """
    View for displaying detailed information about a specific order item
    """
    
    order_item = get_object_or_404(OrderItem, id=item_id)
    
    
    if order_item.order.user != request.user:
        messages.error(request, "You don't have permission to view this order item.")
        return redirect('order_list')
        
    context = {
        'order_item': order_item,
    }
    
    return render(request, 'order_item_detail.html', context)

@block_superuser_navigation
@never_cache
@login_required
@never_cache
def cancel_order_item(request, item_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('order_list')

    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    try:
        if not order_item.can_be_cancelled:
            messages.error(request, "This item can no longer be cancelled.")
            return redirect('user_profile:order_item_detail', item_id=item_id)

        reason = request.POST.get('reason', '')
        order_item.cancel_item(reason=reason)

        messages.success(request, "Item has been successfully cancelled and refund processed.")

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('user_profile:order_item_detail', item_id=item_id)



from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction


@require_POST
@login_required
@block_superuser_navigation
@never_cache
def cancel_product_items(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.exclude(status='cancelled')

    if not order_items.exists():
        messages.error(request, "No active items found in this order.")
        return redirect('user_profile:order_list')

    try:
        with transaction.atomic():
            for item in order_items:
                if item.can_be_cancelled:
                    item.cancel_item(reason="Cancelled as part of full order cancellation.")

            order.calculate_final_total()
            messages.success(request, "Entire order cancelled successfully.")

    except Exception as e:
        messages.error(request, f"Error cancelling entire order: {e}")

    return redirect('user_profile:order_list')



@block_superuser_navigation
@never_cache
@login_required
def return_order_item(request, item_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('user_profile:order_list')

    order_item = get_object_or_404(OrderItem, id=item_id)

    if order_item.order.user != request.user:
        messages.error(request, "You don't have permission to return this order item.")
        return redirect('user_profile:order_list')

    try:
        if not order_item.can_be_returned:
            messages.error(request, "This item is not eligible for return.")
            return redirect('user_profile:order_item_detail', item_id=item_id)

        reason = request.POST.get('reason', '')
        order_item.return_status = "requested"
        order_item.return_reason = reason
        order_item.save()

        messages.success(request, "Return request submitted successfully. Waiting for admin approval.")
    
    except Exception as e:
        print(f"Exception: {e}")  
        messages.error(request, "An error occurred while processing your return request.")

    return redirect('user_profile:order_item_detail', item_id=item_id)

#### order ends ####

@block_superuser_navigation
@never_cache
@login_required
def wallet_view(request):
    """Display wallet balance and transaction history with pagination"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Get all transactions ordered by most recent first
    transactions_list = wallet.transactions.all().order_by("-timestamp", "id")
    
    # Set up pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions_list, 10)  # Show 10 transactions per page
    
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        transactions = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        transactions = paginator.page(paginator.num_pages)
    
    context = {
        "wallet": wallet,
        "page_obj": transactions,
    }
    
    return render(request, "wallet_page.html", context)


@block_superuser_navigation
@never_cache
@login_required
def search_products(request):
    query = request.GET.get('q', '')
    if query:
        orders = Order.objects.filter(
            Q(id__icontains=query) |
            Q(user__email__icontains=query) |
            Q(items__product_variant__product__name__icontains=query)
        ).distinct()[:5]

        results = [{'id': o.id, 'label': f"Order {o.id} - {o.user.email}"} for o in orders]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})


@block_superuser_navigation
@login_required
@never_cache
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_detail.html', {'order': order})

@block_superuser_navigation
@login_required
@never_cache
def submit_review(request, order_item_id):
    if request.method == "POST":
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        product_id = request.POST.get('product_id')

        print(rating, review_text, product_id)

        if rating and review_text:
            # Ensure the product exists
            product = get_object_or_404(Products, id=product_id)

            existing_review = Review.objects.filter(user=request.user, product=product).exists()
            if not existing_review:
                Review.objects.create(
    user=request.user,
    product=product,
    rating=int(rating),
    comment=review_text
)

                messages.success(request, "Review submitted successfully!")
            else:
                messages.error(request, "You have already reviewed this product.")

        else:
            messages.error(request, "Rating and review text are required.")

    return redirect('user_profile:order_item_detail', item_id=order_item_id)



def custom_page_not_found_view(request, exception):
    return render(request, '404page.html', status=404)


##### profile starts ####



import datetime
import re
import random
import string

@block_superuser_navigation
@login_required
@never_cache
def update_profile_image(request):
    if request.method == "POST" and request.FILES.get("profile_image"):
        user = request.user
        if user.profile_image:
            try:
                user.profile_image.delete()
            except Exception as e:
                print(f"Error deleting existing profile image: {e}")
        user.profile_image = request.FILES["profile_image"]
        if not user.profile_image.content_type.startswith("image"):
            return JsonResponse({"success": False, "error": "Invalid file type! Please upload an image."}, status=400)
        if user.profile_image.size > 5 * 1024 * 1024:  # 5MB limit
            return JsonResponse({"success": False, "error": "Image size should not exceed 5MB."}, status=400)
        user.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "No image provided."}, status=400)

@block_superuser_navigation
@never_cache
@login_required
def account_overview(request):
    user = request.user

    if request.method == "POST":
        dob = request.POST.get("dob")
        phone_number = request.POST.get("phone_number", "").strip()
        alternate_phone_number = request.POST.get("alternate_phone_number", "").strip()
        profile_image = request.FILES.get("profile_image")
        username = request.POST.get("username")
        full_name = request.POST.get("full_name")
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        errors = False

        # Validate Username
        if username and username != user.username:
            if not re.match(r'^[a-zA-Z0-9_]{3,200}$', username):
                messages.error(request, "Username must be 3-200 characters and contain only letters, numbers, or underscores.")
                errors = True
            elif request.user.__class__.objects.filter(username=username).exclude(id=user.id).exists():
                messages.error(request, "This username is already in use.")
                errors = True
            else:
                user.username = username

        # Validate Full Name
        if full_name:
            user.full_name = full_name

        # Validate Date of Birth
        if dob:
            try:
                dob_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
                if dob_date >= datetime.datetime.today().date():
                    messages.error(request, "Date of birth cannot be in the future!")
                    errors = True
                else:
                    user.dob = dob_date
            except ValueError:
                messages.error(request, "Invalid date format! Use YYYY-MM-DD.")
                errors = True

        # Validate Phone Number
        if phone_number:
            cleaned_phone = re.sub(r'\D', '', phone_number)
            if not re.match(r'^\d{9,15}$', cleaned_phone):
                messages.error(request, "Phone number must be 9-15 digits.")
                errors = True
            else:
                user.phone_number = cleaned_phone
        else:
            user.phone_number = None

        # Validate Alternate Phone Number
        if alternate_phone_number:
            cleaned_alt_phone = re.sub(r'\D', '', alternate_phone_number)
            if not re.match(r'^\d{9,15}$', cleaned_alt_phone):
                messages.error(request, "Alternate phone number must be 9-15 digits.")
                errors = True
            else:
                user.alternate_phone_number = cleaned_alt_phone
        else:
            user.alternate_phone_number = None

        ### Validate Profile Image
        if profile_image:
            if not profile_image.content_type.startswith("image"):
                messages.error(request, "Invalid file type! Please upload an image.")
                errors = True
            elif profile_image.size > 5 * 1024 * 1024:  # 5MB limit
                messages.error(request, "Image size should not exceed 5MB.")
                errors = True
            else:
                if user.profile_image:
                    try:
                        user.profile_image.delete()
                    except Exception as e:
                        print(f"Error deleting existing profile image: {e}")
                user.profile_image = profile_image

        # Validate Password
        if new_password:
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                errors = True
            elif len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                errors = True
            elif not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                errors = True
            else:
                user.set_password(new_password)

        if not errors:
            try:
                user.save()
                messages.success(request, "Profile updated successfully!")
                return redirect("user_profile:account_overview")
            except Exception as e:
                messages.error(request, f"Error saving profile: {str(e)}")
                errors = True

    context = {
        "user": user,
        "dob": user.dob.strftime("%Y-%m-%d") if user.dob else "",
        "phone_number": user.phone_number or "",
        "alternate_phone_number": user.alternate_phone_number or "",
        "username": user.username or "",
        "full_name": user.full_name or "",
    }
    return render(request, "account_overview.html", context)

@block_superuser_navigation
@never_cache
@login_required
def request_email_verification(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        new_email = data.get("new_email")
        if not new_email:
            return JsonResponse({"success": False, "error": "Email is required."}, status=400)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            return JsonResponse({"success": False, "error": "Invalid email format."}, status=400)
        if request.user.__class__.objects.filter(email=new_email).exclude(id=request.user.id).exists():
            return JsonResponse({"success": False, "error": "This email is already in use."}, status=400)
        
        # code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
 
        code = ''.join(random.choices(string.digits, k=6))

        request.session['email_confirmation_code'] = code
        request.session['new_email'] = new_email
        try:
            send_mail(
                'Email Verification',
                f'Your verification code is {code}',
                settings.DEFAULT_FROM_EMAIL,
                [new_email],
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Error sending email: {str(e)}"}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

@block_superuser_navigation
@never_cache
@login_required
def verify_email(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        code = data.get("code")
        new_email = data.get("new_email")
        if code == request.session.get('email_confirmation_code') and new_email == request.session.get('new_email'):
            user = request.user
            user.email = new_email
            user.save()
            request.session.pop('email_confirmation_code', None)
            request.session.pop('new_email', None)
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": "Invalid code or email."}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

@block_superuser_navigation
@login_required
@never_cache
def manage_address(request):
    addresses = Address.objects.filter(user=request.user)  
    return render(request, 'manage_address.html', {'addresses': addresses})




@login_required
@never_cache
def referral_profile_view(request):
    referral_code = request.user.referral_code
    return render(request, 'refferal_code.html', {
        'referral_code': referral_code
    }) 




from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from cart.models import Cart
from wishlist.models import Wishlist

@login_required
def ajax_get_counts(request):
    user = request.user

    cart = getattr(user, 'cart', None)
    wishlist = getattr(user, 'wishlist', None)

    cart_count = cart.items.count() if cart else 0
    wishlist_count = wishlist.items.count() if wishlist else 0

    return JsonResponse({
        'cart_count': cart_count,
        'wishlist_count': wishlist_count
    })
