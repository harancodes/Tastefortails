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
            # Log the received data for debugging
            logger.info(f"POST data: {request.POST}")
            logger.info(f"Content type: {request.content_type}")
            
            # Get data from POST request
            name = request.POST.get("name")
            phone = request.POST.get("phone")
            address_line = request.POST.get("address_line")
            address_type = request.POST.get("address_type")
            city = request.POST.get("city")
            state = request.POST.get("state")
            postal_code = request.POST.get("postal_code")
            country = request.POST.get("country")
            
            # Validate required fields
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
            
            # Create and save the address
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
        # Update the address fields
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
            return JsonResponse({"error": str(e)}, status=400)  # Bad Request

    return JsonResponse({"error": "Invalid request method."}, status=400)


@block_superuser_navigation
@login_required
@never_cache
def delete_address(request, address_id):
    if request.method == "DELETE":
        # Use get_object_or_404 to handle the case where the address does not exist
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Check if the address is used in any orders
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


@block_superuser_navigation
@never_cache
@login_required
def order_list_view(request):
    orders_list = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders_list = orders_list.filter(status__status=status)

    # Pagination
    paginator = Paginator(orders_list.order_by('id'), 5)  # Show 10 orders per page
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    return render(request, 'order_list.html', {'orders': orders})

@block_superuser_navigation
@never_cache
@login_required
def generate_invoice(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    user = item.order.user
    address = item.order.shipping_address  

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{item.id}.pdf"'

    # Create the PDF object, using the response object as its "file."
    pdf = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER  # Center alignment
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        textColor=colors.darkblue
    )
    
    normal_style = styles['BodyText']
    
    # Create the content
    content = []
    
    # Add title
    content.append(Paragraph("Invoice", title_style))
    content.append(Spacer(1, 12))
    
    # Add store information (dynamic)
    store_name = "EvoTime"  # Replace with dynamic data (e.g., from a Store model)
    store_address = "Ivrine Stafford Texas North America"  # Replace with dynamic data
    content.append(Paragraph(store_name, header_style))
    content.append(Paragraph(store_address, normal_style))
    content.append(Spacer(1, 12))
    
    # Add customer information
    content.append(Paragraph("Bill To:", header_style))
    content.append(Paragraph(f"{user.full_name}", normal_style))
    content.append(Paragraph(f"Email: {user.email}", normal_style))  # Add email
    if address:
        content.append(Paragraph(f"{address.address_line}", normal_style))
        content.append(Paragraph(f"{address.city}, {address.state} {address.postal_code}", normal_style))
        content.append(Paragraph(f"{address.country}", normal_style))
    content.append(Spacer(1, 12))
    
    # Add order details
    content.append(Paragraph("Order Details", header_style))
    order_details = [
        ["Order ID", item.order.id],
        ["Product", Paragraph(item.product_variant.product.name, normal_style)],  # Wrap product name
        ["Quantity", item.quantity],
        ["Price per unit", f"${item.product_variant.product.variant_price}"],
        ["Total Price", f"${item.total_price}"]
    ]
    
    # Define column widths
    col_widths = [1.5 * inch, 4.5 * inch]  # Adjust column widths to fit content
    
    table = Table(order_details, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrap
    ]))
    
    content.append(table)
    content.append(Spacer(1, 12))
    
    # Add thank you message
    content.append(Paragraph("Thank you for your purchase!", normal_style))
    
    # Build the PDF
    pdf.build(content)
    
    return response




@block_superuser_navigation
@never_cache
@login_required
def order_item_detail(request, item_id):
    """
    View for displaying detailed information about a specific order item
    """
    # Get the order item and make sure it belongs to the current user
    order_item = get_object_or_404(OrderItem, id=item_id)
    
    # Security check: Make sure the order belongs to the current user
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
def cancel_order_item(request, item_id):
    """
    View for cancelling a specific order item and processing a wallet refund if payment was completed.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('order_list')

    order_item = get_object_or_404(OrderItem, id=item_id)

    try:
        if not order_item.can_be_cancelled:
            messages.error(request, "This item can no longer be cancelled.")
            return redirect('order_item_detail', item_id=item_id)

        with transaction.atomic():
            reason = request.POST.get('reason', '')

            # **1. Restock the cancelled item**
            product_variant = order_item.product_variant
            product_variant.quantity_in_stock += order_item.quantity
            product_variant.save()


            order = order_item.order
            total_items = order.items.count()  

            if total_items > 1:
                shipping_share = order.shipping_charge / Decimal(total_items) 
            else:
                shipping_share = order.shipping_charge 
    

            refund_amount = order_item.total_price + shipping_share


            payment = order.payment
            if payment.status == 'completed':
                wallet, _ = Wallet.objects.get_or_create(user=order.user) 
                wallet.add_amount(refund_amount, reason="Order Cancellation Refund")


            order_item.cancel_item(reason=reason)

            messages.success(request, "Item has been successfully cancelled, and the refund has been processed.")

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('user_profile:order_item_detail', item_id=item_id)



@block_superuser_navigation
@never_cache
@login_required
def return_order_item(request, item_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('order_list')

    order_item = get_object_or_404(OrderItem, id=item_id)

    if order_item.order.user != request.user:
        messages.error(request, "You don't have permission to return this order item.")
        return redirect('order_list')

    try:
        if not order_item.can_be_returned:
            messages.error(request, "This item is not eligible for return.")
            return redirect('order_item_detail', item_id=item_id)

        reason = request.POST.get('reason', '')
        order_item.return_status = "requested"
        order_item.return_reason = reason
        order_item.save()

        messages.success(request, "Return request submitted successfully. Waiting for admin approval.")
    
    except Exception as e:
        print(f"Exception: {e}")  # Debugging
        messages.error(request, "An error occurred while processing your return request.")

    return redirect('order_item_detail', item_id=item_id)

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
        products = Products.objects.filter(name__icontains=query)[:5]  # Limit results
        results = [{'id': p.id, 'name': p.name} for p in products]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def submit_review(request, order_item_id):
    if request.method == "POST":
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        product_id = request.POST.get('product_id')

        print(rating, review_text, product_id)

        if rating and review_text:
            # Ensure the product exists
            product = get_object_or_404(Products, id=product_id)

            # Check if the user has already reviewed this specific product
            existing_review = Review.objects.filter(user=request.user, product=product).exists()
            if not existing_review:
                Review.objects.create(
                    user=request.user,
                    product=product,
                    rating=int(rating),
                    review=review_text
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

@login_required
def update_profile_image(request):
    if request.method == "POST" and request.FILES.get("profile_image"):
        user = request.user
        user.profile_image = request.FILES["profile_image"]
        user.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)



@block_superuser_navigation
@never_cache
@login_required
def account_overview(request):
    user = request.user  # Get the logged-in user

    if request.method == "POST":
        # Retrieve form data
        dob = request.POST.get("dob")
        alternate_phone_number = request.POST.get("alternate_phone_number", "").strip()
        profile_image = request.FILES.get("profile_image")
        # email = request.POST.get('email')
        # full_name = request.POST.get('full_name')
        

        errors = False 

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

        # Validate Alternate Phone Number
        if alternate_phone_number:

            cleaned_phone = re.sub(r'\D', '', alternate_phone_number)
            
            if not re.match(r'^\d{10,15}$', cleaned_phone):
                messages.error(request, "Alternate phone number must be 10-15 digits long.")
                errors = True
            else:
                user.alternate_phone_number = cleaned_phone
        else:
            # If no phone number is provided, set to None or empty string
            user.alternate_phone_number = None

        # Validate Profile Image
        if profile_image:
            try:

                if not profile_image.content_type.startswith("image"):
                    messages.error(request, "Invalid file type! Please upload an image.")
                    errors = True
                else:

                    if profile_image.size > 5 * 1024 * 1024:  # 5MB limit
                        messages.error(request, "Image size should not exceed 5MB.")
                        errors = True
                    else:
                        # Delete existing profile image if it exists
                        if user.profile_image:
                            try:
                                user.profile_image.delete()
                            except Exception as e:
                                print(f"Error deleting existing profile image: {e}")
                        
                        # Save new profile image
                        user.profile_image = profile_image

            except Exception as e:
                messages.error(request, f"Error uploading image: {str(e)}")
                errors = True

        # if email:
        #     email = None

        #     if email != user.email:
        #         if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        #             messages.error(request, "Invalid email format.")
        #             errors = True
        #         elif request.user.__class__.objects.filter(email=email).exclude(id=user.id).exists():
        #             messages.error(request, "This email is already in use.")
        #             errors = True
        #         else:
        #             user.email = email

        
        # if full_name:
        #     user.full_name = full_name 


        if not errors:
            try:
                user.save()
                messages.success(request, "Profile updated successfully!")
                return redirect("account_overview")
            except Exception as e:
                messages.error(request, f"Error saving profile: {str(e)}")
                errors = True

    context = {
        "user": user,
        "dob": user.dob.strftime("%Y-%m-%d") if user.dob else None,
        "alternate_phone_number": user.alternate_phone_number or "",
        # "email": email,
        # "full_name" : full_name
    }

    return render(request, "account_overview.html", context)



@block_superuser_navigation
@login_required
@never_cache
def manage_address(request):
    addresses = Address.objects.filter(user=request.user)  
    return render(request, 'manage_address.html', {'addresses': addresses})