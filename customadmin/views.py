from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
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

def block_superuser_navigation(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect(reverse('customadmin:admin_dashboard'))  
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    decorator = user_passes_test(lambda u: u.is_authenticated and u.is_staff)
    return decorator(view_func)



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

    # 🔧 Important: Always return something for GET or after failed POST
    return render(request, 'admin_login.html')



@admin_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("You are not authorized to access this page")
    return render(request, 'admin_dashboard.html')

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
        user.is_active = not user.is_active
        user.save()
        status = 'unblocked' if user.is_active else 'blocked'
        messages.success(request, f'User has been {status} successfully.')
    except User.DoesNotExist:
        messages.error(request, 'User not found.')

    return redirect('customadmin:user_list')

###### User Ends ######


###### Category Section ######


@admin_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if not name.strip():
            messages.error(request, "Category name cannot be empty.")
            return redirect('customadmin:add_category')
        elif Category.objects.filter(name__iexact=name.strip()):

            messages.error(request, "This already exist")
            print("This worked")
            return redirect('customadmin:add_category')
    

        Category.objects.create(name=name, image=image if image else 'category/default_image.jpg')
        messages.success(request, "Category added successfully.")
        return redirect('customadmin:category_list')

    return render(request, 'category/add_category.html')



@admin_required
def category_list(request):
    categories = Category.objects.filter(is_active=True) # 

    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(name__icontains=search_query)

    categories = categories.order_by('-created_at')  # sort by latest created

    paginator = Paginator(categories, 2)  # 10 per page
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
        name = request.POST.get('name')
        image = request.POST.get('image')
        if name:
            category.name = name
            category.save()
            messages.success(request, "Category updated successfully.")
            return redirect('customadmin:category_list')
        else:
            messages.error(request, "Category name cannot be empty.")
        if image:
            category.image = image
            category.save()
            messages.success(request,'Image Added Successfully')

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
from django.db.models import Sum, Min,F
from django.shortcuts import render
from django.db.models import FloatField




@admin_required
def product_list(request):
    # Base query to get active products
    products = Products.objects.filter(is_active=True).order_by('-created_at')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Sorting functionality
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('variants__variant_price')  # Sorting by variant price
    elif sort == 'price_desc':
        products = products.order_by('-variants__variant_price')
    elif sort == 'latest':
        products = products.order_by('-created_at')

    # Annotate products with total stock and total price
    products = products.annotate(
        total_stock=Sum('variants__quantity_in_stock'),  
        total_price=Sum(F('variants__variant_price') * F('variants__quantity_in_stock'), output_field=FloatField())  # Summing price * stock for each variant
    )
    

    # Pagination setup
    paginator = Paginator(products, 3)  # Show 5 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'products': products,
        'search_query': search_query,
    })



@admin_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        product_type = request.POST.get('product_type')

        # Validate fields
        if not all([name, category_id, product_type]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('customadmin:add_product')

        # Variant values
        variants_weight = request.POST.getlist('variants_weight[]')
        variants_price = request.POST.getlist('variants_price[]')
        variants_stock = request.POST.getlist('variants_stock[]')

        # Clean variant data
        variants_weight = [w.strip() for w in variants_weight if w.strip()]
        variants_price = [p.strip() for p in variants_price if p.strip()]
        variants_stock = [s.strip() for s in variants_stock if s.strip()]

        if not all([variants_weight, variants_price, variants_stock]):
            messages.error(request, "At least one variant is required.")
            return redirect('customadmin:add_product')

        try:
            total_stock = sum(int(s) for s in variants_stock if s)
            min_price = min(float(p) for p in variants_price if p)
        except ValueError:
            messages.error(request, "Variant prices and stock must be valid numbers.")
            return redirect('customadmin:add_product')

        # Create product (no price field here because it's on the Variant model)
        product = Products.objects.create(
            name=name,
            description=description,
            category_id=category_id,
            brand_id=brand_id or None,
            product_type=product_type,
            stock=total_stock,  # Total stock across all variants
            is_active=True,
        )

        # Create variants
        for w, p, s in zip(variants_weight, variants_price, variants_stock):
            if w and p and s:
                Variant.objects.create(
                    product=product,
                    weight=w,
                    variant_price=float(p),
                    quantity_in_stock=int(s),
                )

        # Handle Main Image
        main_image = request.FILES.get('main_image')
        if main_image:
            ProductImage.objects.create(product=product, image=main_image, is_primary=True)

        # Handle other images
        for i in range(1, 4):
            other_image = request.FILES.get(f'other_image_{i}')
            if other_image:
                ProductImage.objects.create(product=product, image=other_image, is_primary=False)

        messages.success(request, f"Product '{product.name}' added successfully.")
        return redirect('customadmin:product_list')

    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    return render(request, 'products/add_product.html', {
        'categories': categories,
        'brands': brands,
    })


@admin_required
def edit_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)

    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        product_type = request.POST.get('product_type')
        stock = request.POST.get('stock')

        # Validation
        if not all([name, category_id, product_type, stock]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('customadmin:edit_product', product_id=product.id)

        try:
            stock = int(stock)
        except ValueError:
            messages.error(request, "Stock must be a number.")
            return redirect('customadmin:edit_product', product_id=product.id)

        # Update product
        product.name = name
        product.description = description
        product.category_id = category_id
        product.brand_id = brand_id if brand_id else None
        product.product_type = product_type
        product.stock = stock
        product.save()

        # Update or create variants
        variants_ids = request.POST.getlist('variant_ids[]')
        variants_weight = request.POST.getlist('variants_weight[]')
        variants_price = request.POST.getlist('variants_price[]')
        variants_stock = request.POST.getlist('variants_stock[]')

        for v_id, w, p, s in zip(variants_ids, variants_weight, variants_price, variants_stock):
            if w.strip() and p.strip() and s.strip():
                if v_id:  # Update existing
                    variant = Variant.objects.filter(id=v_id, product=product).first()
                    if variant:
                        variant.weight = w.strip()
                        variant.variant_price = float(p)
                        variant.quantity_in_stock = int(s)
                        variant.save()
                else:  # Create new
                    Variant.objects.create(
                        product=product,
                        weight=w.strip(),
                        variant_price=float(p),
                        quantity_in_stock=int(s),
                        is_active=True,
                    )

        # Update main image
        main_image = request.FILES.get('main_image')
        if main_image:
            ProductImage.objects.filter(product=product, is_primary=True).delete()
            ProductImage.objects.create(product=product, image=main_image, is_primary=True)

        # Replace other images
        ProductImage.objects.filter(product=product, is_primary=False).delete()
        for i in range(1, 4):
            other_image = request.FILES.get(f'other_image_{i}')
            if other_image:
                ProductImage.objects.create(product=product, image=other_image, is_primary=False)

        messages.success(request, f"Product '{name}' updated successfully.")
        return redirect('customadmin:product_list')

    # GET request
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



@admin_required
@never_cache
def block_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    product.is_blocked = not product.is_blocked  # Toggling the block status
    product.save()
    status = 'blocked' if product.is_blocked else 'unblocked'
    messages.success(request, f"{product.name} has been {status} successfully.")
    return redirect('customadmin:product_list')



def admin_logout(request):
    logout(request)
    return render(request, 'admin_login.html')


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test
from product.models import Products


@csrf_exempt  
@require_http_methods(["POST"])
@admin_required
def toggle_product_status(request, product_id):
    if not request.is_ajax():
        return JsonResponse(
            {'success': False, 'error': 'Bad request method'}, 
            status=400
        )

    try:
        product = Products.objects.get(id=product_id)
        product.is_active = not product.is_active
        product.save()
        
        return JsonResponse({
            'success': True,
            'is_active': product.is_active,
            'message': f"Product {'activated' if product.is_active else 'deactivated'} successfully"
        })

    except Products.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Product not found'},
            status=404
        )
        
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500
        )
####### Product Section ####### 

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
            return redirect('customadmin:add_category')
        elif Brand.objects.filter(name__iexact=name.strip()):

            messages.error(request, "This already exist")
            print("This worked")
            return redirect('customadmin:add_brands')
    

        Brand.objects.create(name=name, image=image if image else 'category/default_image.jpg')
        messages.success(request, "Category added successfully.")
        return redirect('customadmin:brands')

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
            messages.success(request, "Category updated successfully.")
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
    brand.is_deleted = True
    brand.save()
    messages.success(request, "Brands deleted (soft) successfully.")
    return redirect('customadmin:brands')

from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest

@require_POST
@admin_required
def toggle_active_status(request, brand_id):
    try:
        brand = Brand.objects.get(pk=brand_id)
        brand.is_active = not brand.is_active
        brand.save()
        return JsonResponse({'status': 'success', 'is_active': brand.is_active})
    except Brand.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Brand not found'}, status=404)

