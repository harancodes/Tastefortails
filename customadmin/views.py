from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q, ExpressionWrapper
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from product.models import ProductImage, Products, Category, Variant, Brand
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from customadmin.models import Banner
from django.urls import reverse
import logging
from django.db.models import Sum
from django.core.paginator import PageNotAnInteger, Paginator, EmptyPage
from cart.models import Order, OrderItem, Wallet, Payment, transaction
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, time, datetime
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.lib.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.http import HttpResponse
from customadmin.models import Coupon, UsedCoupon
from functools import wraps





def block_superuser_navigation(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect(reverse('customadmin:admin_dashboard'))
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url='admin_login',  # ensure this matches your URL name
        redirect_field_name=None  # remove ?next= from URL
    )(view_func)



logger = logging.getLogger(__name__)

@never_cache
def admin_login(request):
    logger.debug(f"Request user: {request.user}")
    
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('customadmin:admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        logger.debug(f"Authenticated user: {user}")

        if user is not None and user.is_staff:
            login(request, user)
            return redirect('customadmin:admin_dashboard')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'admin_login.html')



@admin_required
@never_cache
def admin_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("You are not authorized to access this page")
    User= get_user_model()
    total_users = User.objects.count()
    
    return render(request, 'admin_dashboard.html', {"total_users": total_users})

@admin_required
def user_list(request):
    User = get_user_model()
    users = User.objects.all()

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )

    users = users.order_by('-date_joined')

    paginator = Paginator(users, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'user_list.html', context)

@admin_required
def block_user(request, user_id):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        user.is_blocked = not user.is_blocked
        user.save()
        status = 'unblocked' if not user.is_blocked else 'blocked'
        messages.success(request, f'User has been {status} successfully.')
    except User.DoesNotExist:
        messages.error(request, 'User not found.')

    return redirect('customadmin:user_list')


###### User Ends ######


###### Category Section ######


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get('name')
        image = request.FILES.get('image')
        offer_percentage = request.POST.get('offer_percentage', '0')

        # Clean up and validate name
        if not name.strip():
            messages.error(request, "Category name cannot be empty.")
            return redirect('customadmin:add_category')

        if Category.objects.filter(name__iexact=name.strip()).exists():
            messages.error(request, "This category already exists.")
            return redirect('customadmin:add_category')

        # Validate offer_percentage
        try:
            offer_percentage = int(offer_percentage)
            if offer_percentage < 0 or offer_percentage > 100:
                raise ValueError
        except ValueError:
            messages.error(request, "Offer percentage must be between 0 and 100.")
            return redirect('customadmin:add_category')

        default_image = 'category/default_image.jpg'

        # Create Category
        Category.objects.create(
            name=name.strip(),
            image=image if image else default_image,
            offer_percentage=offer_percentage
        )

        messages.success(request, "Category added successfully.")
        return redirect('customadmin:category_list')

    return render(request, 'category/add_category.html')




@admin_required
def category_list(request):
    categories = Category.objects.filter(is_active=True) 

    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(name__icontains=search_query)

    categories = categories.order_by('-created_at')  

    paginator = Paginator(categories, 2)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'category/category_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })


@admin_required
def toggle_list_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_listed = not category.is_listed
    category.save()
    messages.success(request, f"{'Listed' if category.is_listed else 'Unlisted'} category successfully.")
    return redirect('customadmin:category_list')



@admin_required
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        image = request.FILES.get('image')
        offer_percentage = request.POST.get('offer_percentage', '').strip()

        has_error = False

        if not name:
            messages.error(request, "Category name cannot be empty.")
            has_error = True
        elif Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
            messages.error(request, f"A category with the name '{name}' already exists.")
            has_error = True
        else:
            category.name = name

        if offer_percentage:
            try:
                offer_val = float(offer_percentage)
                if offer_val < 0 or offer_val > 100:
                    messages.error(request, "Offer percentage must be between 0 and 100.")
                    has_error = True
                else:
                    category.offer_percentage = offer_val
            except ValueError:
                messages.error(request, "Offer percentage must be a valid number.")
                has_error = True
        else:
            category.offer_percentage = None  

        if image:
            category.image = image

        if not has_error:
            category.save()
            messages.success(request, "Category updated successfully.")
            return redirect('customadmin:category_list')

    return render(request, 'category/edit_category.html', {'category': category})






@admin_required
def soft_delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_active = False
    category.save()
    messages.success(request, "Category deleted (soft) successfully.")
    return redirect('customadmin:category_list')


from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.text import slugify

####### Category Ends #######

##### Product Section ######
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.db.models import Sum, Min,F, Max
from django.shortcuts import render
from django.db.models import FloatField


@admin_required
def product_list(request):
    
    products = Products.objects.filter(is_active=True).order_by('-created_at')


    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            
            Q(category__name__icontains=search_query)
        )

    
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.annotate(min_price=Min('variants__variant_price')).order_by('min_price')
    elif sort == 'price_desc':
        products = products.annotate(max_price=Max('variants__variant_price')).order_by('-max_price')
    elif sort == 'latest':
        products = products.order_by('-created_at')

    
    products = products.annotate(
        total_stock=Sum('variants__quantity_in_stock'),
        total_price=Sum(
            ExpressionWrapper(
                F('variants__variant_price') * F('variants__quantity_in_stock'),
                output_field=FloatField()
            )
        )
    )

    
    products = products.prefetch_related('images')

    
    paginator = Paginator(products, 3)  
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'products': products,
        'search_query': search_query,
    })



import cloudinary
import cloudinary.uploader
import base64
from PIL import Image
from io import BytesIO
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse

def add_product(request):
    if request.method == "POST":
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            category_id = request.POST.get('category')
            brand_id = request.POST.get('brand')
            product_type = request.POST.get('product_type')
            offer_percentage = int(request.POST.get('offer_percentage', 0) or 0)

            if not all([name, category_id, product_type]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('customadmin:add_product')

            if Products.objects.filter(name__iexact=name).exists():
                messages.error(request, f"A product with the name '{name}' already exists.")
                return redirect('customadmin:add_product')

            # Variants
            variants_weight = [w.strip() for w in request.POST.getlist('variants_weight[]') if w.strip()]
            variants_price = [p.strip() for p in request.POST.getlist('variants_price[]') if p.strip()]
            variants_stock = [s.strip() for s in request.POST.getlist('variants_stock[]') if s.strip()]

            if not all([variants_weight, variants_price, variants_stock]):
                messages.error(request, "At least one variant is required.")
                return redirect('customadmin:add_product')

            for w, p, s in zip(variants_weight, variants_price, variants_stock):
                try:
                    if float(p) < 0:
                        messages.error(request, "Variant price cannot be negative.")
                        return redirect('customadmin:add_product')
                    if int(s) < 0:
                        messages.error(request, "Variant stock cannot be negative.")
                        return redirect('customadmin:add_product')
                except ValueError:
                    messages.error(request, "Variant weight, price, and stock must be valid numbers.")
                    return redirect('customadmin:add_product')

            # Total stock and min price
            try:
                total_stock = sum(int(s) for s in variants_stock)
            except ValueError:
                messages.error(request, "Variant stock must be valid numbers.")
                return redirect('customadmin:add_product')

            # Create Product
            product = Products.objects.create(
                name=name,
                description=description,
                category_id=category_id,
                brand_id=brand_id or None,
                product_type=product_type,
                stock=total_stock,
                is_active=True,
                offer_percentage=offer_percentage
            )

            # Add Variants and apply offer logic
            for w, p, s in zip(variants_weight, variants_price, variants_stock):
                variant = Variant.objects.create(
                    product=product,
                    weight=w,
                    variant_price=float(p),
                    quantity_in_stock=int(s),
                )
                variant.apply_offer()
                variant.save()

            # Add Main Image
            main_image_data = request.POST.get('main_image_data')
            if main_image_data:
                main_image = save_cropped_image(main_image_data)
                ProductImage.objects.create(product=product, image=main_image, is_primary=True)
            else:
                main_image = request.FILES.get('main_image')
                if main_image:
                    ProductImage.objects.create(product=product, image=main_image, is_primary=True)
                else:
                    messages.warning(request, "No main image was provided. Product added without a primary image.")

            # Add Additional Images
            for i in range(1, 4):
                other_image_data = request.POST.get(f'other_image_data_{i}')
                if other_image_data:
                    other_image = save_cropped_image(other_image_data)
                    ProductImage.objects.create(product=product, image=other_image, is_primary=False)
                else:
                    other_image = request.FILES.get(f'other_image_{i}')
                    if other_image:
                        ProductImage.objects.create(product=product, image=other_image, is_primary=False)

            messages.success(request, f"Product '{product.name}' added successfully.")
            redirect_url = reverse('customadmin:product_list')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f"Product '{product.name}' added successfully.",
                    'redirect_url': redirect_url
                })

            return redirect(redirect_url)

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            messages.error(request, error_message)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)
            return redirect('customadmin:add_product')

    # GET request
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)

    return render(request, 'products/add_product.html', {
        'categories': categories,
        'brands': brands,
    })

def save_cropped_image(base64_data):
    """Helper function to save the base64 cropped image to Cloudinary"""
    
    try:
        format, imgstr = base64_data.split(';base64,')  
        imgdata = base64.b64decode(imgstr)
        
        image = Image.open(BytesIO(imgdata))
        
        # Upload the image to Cloudinary
        upload_result = cloudinary.uploader.upload(imgdata, resource_type="image")
        
        cloudinary_url = upload_result['secure_url']
        
        return cloudinary_url
    except Exception as e:
        raise ValueError(f"Error processing image: {str(e)}")
    
    ######################

def save_cropped_image(base64_data):
    try:
        format, imgstr = base64_data.split(';base64,')  
        imgdata = base64.b64decode(imgstr)
        image = Image.open(BytesIO(imgdata))
        upload_result = cloudinary.uploader.upload(imgdata, resource_type="image")
        print(upload_result) 
        cloudinary_url = upload_result['secure_url']
        return cloudinary_url
    except Exception as e:
        print(f"Error: {str(e)}")  
        raise ValueError(f"Error processing image: {str(e)}")




@admin_required
def edit_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)

    if request.method == "POST":
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            category_id = request.POST.get('category')
            brand_id = request.POST.get('brand')
            product_type = request.POST.get('product_type')
            offer_percentage = int(request.POST.get('offer_percentage', 0) or 0)
            
            if not all([name, category_id, product_type]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('customadmin:edit_product', product_id=product.id)
            
            if Products.objects.filter(name__iexact=name).exclude(id=product.id).exists():
                messages.error(request, f"A product with the name '{name}' already exists.")
                return redirect('customadmin:edit_product', product_id=product.id)

            variant_ids = request.POST.getlist('variant_ids[]', [])
            variants_weight = request.POST.getlist('variants_weight[]', [])
            variants_price = request.POST.getlist('variants_price[]', [])
            variants_stock = request.POST.getlist('variants_stock[]', [])
            
            variants_weight = [w.strip() for w in variants_weight if w.strip()]
            variants_price = [p.strip() for p in variants_price if p.strip()]
            variants_stock = [s.strip() for s in variants_stock if s.strip()]
            
            if not all([variants_weight, variants_price, variants_stock]):
                messages.error(request, "At least one variant is required.")
                return redirect('customadmin:edit_product', product_id=product.id)

            for w, p, s in zip(variants_weight, variants_price, variants_stock):
                try:
                    if float(p) < 0 or int(s) < 0:
                        messages.error(request, "Variant price and stock must be non-negative.")
                        return redirect('customadmin:edit_product', product_id=product.id)
                except ValueError:
                    messages.error(request, "Variant weight, price, and stock must be valid numbers.")
                    return redirect('customadmin:edit_product', product_id=product.id)

            try:
                total_stock = sum(int(s) for s in variants_stock if s)
            except ValueError:
                messages.error(request, "Variant stock must be valid numbers.")
                return redirect('customadmin:edit_product', product_id=product.id)

            product.name = name
            product.description = description
            product.category_id = category_id
            product.brand_id = brand_id or None
            product.product_type = product_type
            product.offer_percentage = offer_percentage
            product.stock = total_stock
            product.save()

            existing_variant_ids = list(Variant.objects.filter(product=product).values_list('id', flat=True))
            updated_variant_ids = []

            for i, (w, p, s) in enumerate(zip(variants_weight, variants_price, variants_stock)):
                try:
                    v_id = variant_ids[i] if i < len(variant_ids) and variant_ids[i] else None
                    price = float(p)
                    stock = int(s)

                    if v_id and v_id.isdigit():
                        v_id = int(v_id)
                        variant = Variant.objects.filter(id=v_id, product=product).first()
                        if variant:
                            variant.weight = w
                            variant.variant_price = price
                            variant.quantity_in_stock = stock
                            variant.apply_offer()
                            variant.save()
                            updated_variant_ids.append(v_id)
                    else:
                        variant = Variant.objects.create(
                            product=product,
                            weight=w,
                            variant_price=price,
                            quantity_in_stock=stock,
                        )
                        variant.apply_offer()
                        variant.save()
                        updated_variant_ids.append(variant.id)
                except (ValueError, IndexError) as e:
                    messages.error(request, f"Error with variant {i+1}: {str(e)}")
                    return redirect('customadmin:edit_product', product_id=product.id)

            variants_to_delete = set(existing_variant_ids) - set(updated_variant_ids)
            Variant.objects.filter(id__in=variants_to_delete).delete()

            remove_image_ids = request.POST.getlist('remove_image_ids[]', [])
            if remove_image_ids:
                ProductImage.objects.filter(id__in=remove_image_ids, product=product).delete()

            main_image_data = request.POST.get('main_image_data')
            if main_image_data:
                ProductImage.objects.filter(product=product, is_primary=True).delete()
                main_image = save_cropped_image(main_image_data)
                ProductImage.objects.create(product=product, image=main_image, is_primary=True)
            else:
                main_image = request.FILES.get('main_image')
                if main_image:
                    ProductImage.objects.filter(product=product, is_primary=True).delete()
                    ProductImage.objects.create(product=product, image=main_image, is_primary=True)

            for i in range(1, 4):
                other_image_data = request.POST.get(f'other_image_data_{i}')
                if other_image_data:
                    other_image = save_cropped_image(other_image_data)
                    ProductImage.objects.create(product=product, image=other_image, is_primary=False)
                else:
                    other_image = request.FILES.get(f'other_image_{i}')
                    if other_image:
                        ProductImage.objects.create(product=product, image=other_image, is_primary=False)

            messages.success(request, f"Product '{product.name}' updated successfully.")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f"Product '{product.name}' updated successfully.",
                    'redirect_url': reverse('customadmin:product_list')
                })

            return redirect('customadmin:product_list')

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            messages.error(request, error_message)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)

            return redirect('customadmin:edit_product', product_id=product.id)

    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    variants = Variant.objects.filter(product=product)
    images = ProductImage.objects.filter(product=product)

    return render(request, 'products/edit_product.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
        'variants': variants,
        'images': images,
    })


@never_cache
@admin_required
def soft_delete_product(request, product_id):
    try:
        product = Products.objects.get(id=product_id)
        product.is_active = False
        product.save()
        messages.success(request, f"'{product.name}' has been deactivated successfully.")
    except Products.DoesNotExist:
        messages.error(request, "Product not found.")
    except Exception as e:
        messages.error(request, f"Error deactivating product: {str(e)}")
    
    return redirect('customadmin:product_list')


# @admin_required
# @never_cache
# def block_product(request, product_id):
#     product = get_object_or_404(Products, id=product_id)
#     product.is_blocked = not product.is_blocked  # Toggling the block status
#     product.save()
#     status = 'blocked' if product.is_blocked else 'unblocked'
#     messages.success(request, f"{product.name} has been {status} successfully.")
#     return redirect('customadmin:product_list')

# @admin_required
# @never_cache
# def toggle_list_product(request, product_id):
#     product = get_object_or_404(Banner, id=product_id)
#     product.is_listed = not product.is_listed
#     product.save()
#     messages.success(request, f"{'Listed' if product.is_listed else 'Unlisted'} banner successfully.")
#     return redirect('customadmin:banner_list')
@never_cache
def admin_logout(request):
    logout(request)
    request.session.flush()
    response = redirect('admin_login')  # or use render if you don't want redirect
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return render(request, 'admin_login.html')


# views.py
from django.views.decorators.http import require_POST
# from .models import Products

# @require_POST
# def toggle_product_status(request, product_id):
#     product = get_object_or_404(Products, id=product_id)
#     product.is_listed = not product.is_listed  # Toggle the status
#     product.save()
#     action = "listed" if product.is_listed else "unlisted"
#     messages.success(request, f"Product '{product.name}' has been {action}.")
#     return redirect('customadmin:product_list')         

def toggle_product_status(request, product_id):
    product = get_object_or_404(Products, id=product_id)

    product.is_listed = not product.is_listed
    product.save()

    action = "listed" if product.is_listed else "unlisted"
    messages.success(request, f"Product has been successfully {action}.")

    return redirect(request.META.get('HTTP_REFERER', 'customadmin:product_list'))


####### Product End ####### 

######## Banner Section #######    
    
def banner_list(request):
    banner= Banner.objects.filter(is_active = True)
    search_query = request.GET.get('search', '')
    if search_query:
        banner= banner.filter(name__icontains=search_query)

    banner= banner.order_by('-created_at')  # sort by latest created

    paginator = Paginator(banner, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'banner/banner_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })


@admin_required
def add_banner(request):
    if request.method == "POST":
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if not name:
            messages.error(request, "Banner name cannot be empty.")
            return redirect('customadmin:add_banener')

        Banner.objects.create(name=name, image=image if image else 'banner/default_image.jpg')
        messages.success(request, "Category added successfully.")
        return redirect('customadmin:banner_list')

    return render(request, 'banner/add_banner.html')


@admin_required
def toggle_list_banner(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    banner.is_listed = not banner.is_listed
    banner.save()
    messages.success(request, f"{'Listed' if banner.is_listed else 'Unlisted'} banner successfully.")
    return redirect('customadmin:banner_list')


@admin_required
def edit_banner(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == "POST":
        name = request.POST.get('name')
        image = request.FILES.get('image')  

        if not name:
            messages.error(request, "Banner name cannot be empty.")
            return render(request, 'banner/edit_banner.html', {'banner': banner})

        banner.name = name

        if image:
            banner.image = image

        banner.save()
        messages.success(request, "Banner updated successfully.")
        return redirect('customadmin:banner_list')

    return render(request, 'banner/edit_banner.html', {'banner': banner})





@admin_required
def soft_delete_banner(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    banner.is_active = False
    banner.save()
    messages.success(request, "Banner deleted (soft) successfully.")
    return redirect('customadmin:banner_list')

###### Banner Ends #######


###### Brand Section #######
@admin_required
def brands(request):
    search_query = request.GET.get('search', '')
    
    brands_qs = Brand.objects.filter(is_active=True)  # ensure deleted brands aren't shown
    if search_query:
        brands_qs = brands_qs.filter(name__icontains=search_query)
    
    brands_qs = brands_qs.order_by('-created_at')
    paginator = Paginator(brands_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'brand/brands_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })

@admin_required
def add_brands(request):
    if request.method == "POST":
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if not name.strip():
            messages.error(request, "Category name cannot be empty.")
            return redirect('customadmin:brand_list')
        elif Brand.objects.filter(name__iexact=name.strip()):

            messages.error(request, "This already exist")
            print("This worked")
            return redirect('customadmin:add_brands')
    

        Brand.objects.create(name=name, image=image if image else 'category/default_image.jpg')
        messages.success(request, "Brand added successfully.")
        return redirect('customadmin:brands_list')

    return render(request, 'brand/add_brands.html')


# @admin_required
# def edit_brands(request, brand_id):
#     brand = get_object_or_404(Brand, id=brand_id)

#     if request.method == "POST":
#         name = request.POST.get('name')
#         offer = request.POST.get('offer_percentage')
#         image = request.FILES.get('brand_image')

#         if not name or offer is None:
#             return JsonResponse({'error': 'All fields are required'}, status=400)

#         try:
#             offer = int(offer)
#             if not (0 <= offer <= 100):
#                 raise ValueError
#         except ValueError:
#             return JsonResponse({'error': 'Offer must be a number between 0 and 100'}, status=400)

#         brand.name = name.strip()
#         brand.offer_percentage = offer
#         if image:
#             brand.image = image

#         brand.save()
#         return JsonResponse({'message': 'Brand updated successfully'})

#     # Handle GET request: show form
#     return render(request, 'customadmin/edit_brand.html', {'brand': brand})


@admin_required
def edit_brands(request, brand_id):
    brands = get_object_or_404(Brand, id=brand_id)

    if request.method == "POST":
        name = request.POST.get('name')
        image = request.POST.get('image')
        if name:
            brands.name = name
            brands.save()
            messages.success(request, "Brand updated successfully.")
            return redirect('customadmin:brands_list')
        else:
            messages.error(request, "Category name cannot be empty.")
        if image:
            brands.image = image
            brands.save()
            messages.success(request,'Image Added Successfully')

    return render(request, 'brand/edit_brands.html', {'category': brands})





@admin_required
def soft_delete_brands(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = False
    brand.save()
    messages.success(request, "Brands deleted (soft) successfully.")
    return redirect('customadmin:brands_list')

from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest

@require_POST
@admin_required
def toggle_active_status(request, brand_id):
    try:
        brand = Brand.objects.get(pk=brand_id)
        brand.is_listed = not brand.is_listed
        brand.save()
        return JsonResponse({'status': 'success', 'is_active': brand.is_active})
    except Brand.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Brand not found'}, status=404)



######## order list starts ######3



from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import render

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, F
from django.shortcuts import render

@admin_required
@never_cache
def admin_order_list_view(request):
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', '').strip()

    
    orders_list = Order.objects.select_related('user')\
        .prefetch_related('items__product_variant__product')\
        .order_by('-created_at')

    
    if search_query:
        query = Q(user__email__icontains=search_query) | \
                Q(items__product_variant__product__name__icontains=search_query) | \
                Q(user__first_name__icontains=search_query) | \
                Q(user__full_name__icontains=search_query)
        if search_query.isdigit():
            query |= Q(id=int(search_query))
        orders_list = orders_list.filter(query).distinct()

    # Sorting logic
    if sort_by == 'price_asc':
        
        orders_list = orders_list.order_by('total_amount')
    elif sort_by == 'price_desc':
        orders_list = orders_list.order_by('-total_amount')
    elif sort_by == 'name_asc':
        
        orders_list = orders_list.order_by('user__first_name')
    elif sort_by == 'name_desc':
        orders_list = orders_list.order_by('-user__first_name')
    else:
        
        orders_list = orders_list.order_by('-created_at')

    
    paginator = Paginator(orders_list, 5)
    page_number = request.GET.get('page')
    try:
        orders = paginator.page(page_number)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    context = {
        'orders': orders,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    return render(request, 'orders/admin_order.html', context)





@admin_required
@never_cache   
def admin_change_order_item_status_view(request, order_item_id):
    try:
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order = order_item.order

        if request.method == 'POST':
            new_status = request.POST.get('status', '').strip()

            if new_status not in dict(OrderItem.STATUS_CHOICES).keys():
                messages.error(request, "Invalid status selected.")
                return redirect('customadmin:admin_order_list_view')

            if new_status == 'cancelled':
                messages.error(request, "Cannot manually change status to cancelled.")
                return redirect('customadmin:admin_order_list_view')

            try:
                with transaction.atomic():
                    order_item.status = new_status
                    order_item.save()

                    try:
                        payment = order.payment
                        
                        if payment.payment_method == 'cod':
                            if new_status in ['shipped', 'delivered']:
                                payment.status = 'completed'
                            payment.save()

                    except Payment.DoesNotExist:
                        messages.warning(request, "No payment record found for this order.")

                    order_statuses = order.items.values_list('status', flat=True).distinct()
                    if len(order_statuses) == 1:
                        if new_status == 'delivered':
                            order.status = 'completed'
                            order.save()

                messages.success(request, f"Order item status updated to {new_status}.")
            
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

        return redirect('customadmin:admin_order_list_view')

    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('customadmin:admin_order_list_view')
    

@admin_required
@never_cache   
def admin_return_requests(request):
    return_requests = OrderItem.objects.filter(return_status="requested")
    return render(request, 'orders/admin_return_requests.html', {'return_requests': return_requests})

@admin_required
@never_cache
def admin_handle_return_request(request, item_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('customadmin:admin_return_requests')

    order_item = get_object_or_404(OrderItem, id=item_id)
    action = request.POST.get('action')

    if action not in ['approve', 'reject']:
        messages.error(request, "Invalid action.")
        return redirect('customadmin:admin_return_requests')

    try:
        with transaction.atomic():
            if action == 'approve':
                product_variant = order_item.product_variant
                product_variant.quantity_in_stock += order_item.quantity
                product_variant.save()

                order = order_item.order

                total_items = order.items.exclude(status__in=["returned", "cancelled"]).count()
                if total_items > 1:
                    per_item_shipping_charge = order.shipping_charge / total_items
                else:
                    per_item_shipping_charge = order.shipping_charge

                refund_amount = order_item.total_price + per_item_shipping_charge

               
                if order.coupon and order.coupon_discount:
                    coupon = order.coupon
                    remaining_items = order.items.exclude(id=order_item.id).exclude(status__in=["returned", "cancelled"])
                    remaining_total = sum(item.total_price for item in remaining_items)

                    if remaining_total < coupon.min_cart_value:
                     
                        refund_amount -= order.coupon_discount

                    
                        order.coupon = None
                        order.coupon_discount = 0
                        order.save()

             
                        UsedCoupon.objects.filter(user=order.user, coupon=coupon).delete()

                        messages.warning(
                            request,
                            "Coupon removed due to return. Discount has been adjusted in the refund."
                        )
                # === End Coupon Validation ===

                # Process refund
                payment = getattr(order, "payment", None)
                if payment and payment.status == "completed":
                    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=order.user)
                    wallet.add_amount(refund_amount, reason="Order Return Refund")
                    messages.success(request, f"Refund of ₹{refund_amount} added to wallet.")
                else:
                    messages.warning(request, "Payment not completed. Refund not processed.")

                # Update item status
                order_item.return_status = "approved"
                order_item.status = "returned"
                order_item.save()

                messages.success(request, "Return request approved successfully.")
            else:
                order_item.return_status = "rejected"
                order_item.save()
                messages.success(request, "Return request rejected.")

    except Exception as e:
        print(f"Error in processing return request: {e}")
        messages.error(request, "An error occurred while processing the return request.")

    return redirect('customadmin:admin_return_requests')




@admin_required
@never_cache
def sales(request):
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    total_revenue = Order.objects.filter(payment__status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(items__status='delivered').distinct().count()
    cancelled_orders = Order.objects.filter(items__status='cancelled').distinct().count()
    weekly_sales = Order.objects.filter(payment__status='completed', created_at__gte=last_7_days).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    monthly_sales = Order.objects.filter(payment__status='completed', created_at__gte=last_30_days).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    

    best_selling_products = OrderItem.objects.values('product_variant__product__name')\
        .annotate(total_sold=Sum('quantity'))\
        .order_by('-total_sold')[:5]
    
    payment_breakdown = Payment.objects.values('payment_method')\
        .annotate(total=Sum('amount'))\
        .order_by('-total')

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'best_selling_products': best_selling_products,
        'payment_breakdown': payment_breakdown,
    }
    return render(request, "sales/sale_report.html", context)


    



#dashboard
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook
from datetime import datetime, timedelta, time


@admin_required
@never_cache
def generate_pdf(request):
    orders = Order.objects.all()
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph('Sales Report', styles['Title'])
    elements.append(title)

    data = [['Order ID', 'User Email', 'Total Amount', 'Offer Percentage', 'Created At']]

    for order in orders:
        offer_percentages = [
            item.product_variant.product.offer_percentage 
            for item in order.items.all()
        ]
        avg_offer_percentage = round(sum(offer_percentages) / len(offer_percentages), 2) if offer_percentages else 0

        data.append([
            str(order.id),
            order.user.email,
            f"Rs {order.total_amount}",
            f"{avg_offer_percentage}%",
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    pdf.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
    return response


@admin_required
@never_cache
def generate_excel(request):
    orders = Order.objects.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    ws.append(['Order ID', 'User Email', 'Total Amount', 'Created At'])

    for order in orders:
        ws.append([
            order.id,
            order.user.email,
            order.total_amount,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
    return response


@admin_required
@never_cache
def sales_data(request):
    filter_type = request.GET.get('filter', 'month')
    today = timezone.now().date()

    if filter_type == 'today':
        start_date = today

        hours = range(24)
        labels = [f'{hour}:00' for hour in hours]
        values = []

        for hour in hours:
            hour_start = timezone.make_aware(datetime.combine(today, time(hour=hour)))
            hour_end = hour_start + timedelta(hours=1)
            hour_revenue = Order.objects.filter(
                created_at__gte=hour_start,
                created_at__lt=hour_end
            ).aggregate(total=Sum("total_amount"))["total"] or 0
            values.append(hour_revenue)

    elif filter_type == 'week':
        start_date = today - timedelta(days=6)  
        labels = []
        values = []

        for i in range(7):
            date = start_date + timedelta(days=i)
            labels.append(date.strftime('%a'))
            day_revenue = Order.objects.filter(
                created_at__date=date
            ).aggregate(total=Sum("total_amount"))["total"] or 0
            values.append(day_revenue)

    elif filter_type == 'month':
        start_date = today.replace(day=1)
        num_days = today.day
        labels = []
        values = []

        for i in range(num_days):
            date = start_date + timedelta(days=i)
            labels.append(date.strftime('%d'))
            day_revenue = Order.objects.filter(
                created_at__date=date
            ).aggregate(total=Sum("total_amount"))["total"] or 0
            values.append(day_revenue)

    elif filter_type == 'year':
        start_date = today.replace(month=1, day=1)
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        values = []

        for month in range(1, 13):
            month_start = today.replace(month=month, day=1)
            if month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month + 1, day=1)

            month_revenue = Order.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).aggregate(total=Sum("total_amount"))["total"] or 0
            values.append(month_revenue)

    else:
        start_date = today.replace(day=1)
        labels = []
        values = []

    orders_in_range = Order.objects.filter(created_at__date__gte=start_date)
    total_orders = total_orders = Order.objects.count()
    total_revenue = orders_in_range.aggregate(total=Sum("total_amount"))["total"] or 0

    top_selling_products = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .values("product_variant__product__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    top_selling_categories = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .values("product_variant__product__category__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    top_selling_brands = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .values("product_variant__product__brand__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    data = {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "labels": labels,
        "values": values,
        "top_selling_products": list(top_selling_products),
        "top_selling_categories": list(top_selling_categories),
        "top_selling_brands": list(top_selling_brands),
    }

    return JsonResponse(data)





@admin_required
@never_cache   
def coupon_management(request):

    coupons = Coupon.objects.all()
    coupons_list = Coupon.objects.all()

    page = request.GET.get('page', 1)
    paginator = Paginator(coupons_list, 10)  #

    try:
        coupons = paginator.page(page)
    except PageNotAnInteger:
        coupons = paginator.page(1)
    except EmptyPage:
        coupons = paginator.page(paginator.num_pages)

    if request.method == "POST":
        coupon_id = request.POST.get("coupon_id")
        code = request.POST.get("code")
        discount_percentage = request.POST.get("discount_percentage")  # Updated field name
        min_cart_value = request.POST.get("min_cart_value")
        start_date = request.POST.get("start_date")
        expiry_date = request.POST.get("expiry_date") or None
        is_active = request.POST.get("is_active") == "on"

        
        try:
            discount_percentage = float(discount_percentage)
            if not (1 <= discount_percentage <= 100):
                raise ValueError("Discount percentage must be between 1 and 100.")
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("coupon_management")

        if coupon_id:  
            coupon = get_object_or_404(Coupon, id=coupon_id)
            coupon.code = code
            coupon.discount_percentage = discount_percentage  
            coupon.min_cart_value = min_cart_value
            coupon.start_date = start_date
            coupon.expiry_date = expiry_date
            coupon.is_active = is_active
            coupon.save()
        else:  
            Coupon.objects.create(
                code=code,
                discount_percentage=discount_percentage,  
                min_cart_value=min_cart_value,
                start_date=start_date,
                expiry_date=expiry_date,
                is_active=is_active
            )

        return redirect("customadmin:coupon_management")

    return render(request, "coupon/manage_coupons.html", {"coupons": coupons})


@admin_required
@never_cache   
def get_coupon_details(request, coupon_id):
    """Fetch coupon details via AJAX for editing"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    data = {
        "id": coupon.id,
        "code": coupon.code,
        "discount_percentage": str(coupon.discount_percentage),  # Updated field name
        "min_cart_value": str(coupon.min_cart_value),
        "start_date": str(coupon.start_date),
        "expiry_date": str(coupon.expiry_date) if coupon.expiry_date else "",
        "is_active": coupon.is_active,
    }
    return JsonResponse(data)


@admin_required
@never_cache   
def delete_coupon(request, coupon_id):
    
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    return JsonResponse({"message": "Coupon deleted successfully"})

@admin_required
@never_cache
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == "POST":
        code = request.POST.get('code', '').strip()
        discount_percentage = request.POST.get('discount_percentage')
        min_cart_value = request.POST.get('min_cart_value')
        start_date = request.POST.get('start_date')
        expiry_date = request.POST.get('expiry_date')
        is_active = request.POST.get('is_active') == 'on'

        has_error = False

        if not code:
            messages.error(request, "Coupon code cannot be empty.")
            has_error = True
        elif Coupon.objects.filter(code__iexact=code).exclude(id=coupon_id).exists():
            messages.error(request, f"A coupon with the code '{code}' already exists.")
            has_error = True
        else:
            coupon.code = code

        try:
            coupon.discount_percentage = float(discount_percentage)
            coupon.min_cart_value = float(min_cart_value)
            coupon.start_date = start_date
            coupon.expiry_date = expiry_date or None
            coupon.is_active = is_active
        except ValueError:
            messages.error(request, "Please enter valid numbers for percentage and cart value.")
            has_error = True

        if not has_error:
            coupon.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect('customadmin:coupon_list')

    return render(request, 'coupon/manage_coupons.html', {'coupon': coupon})

 
