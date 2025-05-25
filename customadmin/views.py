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

    return render(request, 'admin_login.html')



@admin_required
@never_cache
def admin_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("You are not authorized to access this page")
    
    # total_user = User.objects.aggregate(Sum('points'))['points__sum']
    
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

        # Check if name is empty
        if not name.strip():
            messages.error(request, "Category name cannot be empty.")
            return redirect('customadmin:add_category')

        # Check if category already exists
        if Category.objects.filter(name__iexact=name.strip()).exists():
            messages.error(request, "This category already exists.")
            return redirect('customadmin:add_category')

        default_image = 'category/default_image.jpg'  

        # Create the category object with the uploaded image or default image
        Category.objects.create(name=name.strip(), image=image if image else default_image)

        # Success message
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

        has_error = False

        if not name:
            messages.error(request, "Category name cannot be empty.")
            has_error = True
        elif Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
            messages.error(request, f"A category with the name '{name}' already exists.")
            has_error = True
        else:
            category.name = name

        if image:
            category.image = image

        if not has_error:
            category.save()
            messages.success(request, "Category updated successfully.")
            return redirect('customadmin:category_list')

        # If there's an error, fall through and re-render the form with messages

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

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
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

            
            if not all([name, category_id, product_type]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('customadmin:add_product')

            
            if Products.objects.filter(name__iexact=name).exists():
                messages.error(request, f"A product with the name '{name}' already exists.")
                return redirect('customadmin:add_product')

            
            variants_weight = request.POST.getlist('variants_weight[]')
            variants_price = request.POST.getlist('variants_price[]')
            variants_stock = request.POST.getlist('variants_stock[]')

            
            variants_weight = [w.strip() for w in variants_weight if w.strip()]
            variants_price = [p.strip() for p in variants_price if p.strip()]
            variants_stock = [s.strip() for s in variants_stock if s.strip()]

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

            try:
                total_stock = sum(int(s) for s in variants_stock if s)
                min_price = min(float(p) for p in variants_price if p)
            except ValueError:
                messages.error(request, "Variant prices and stock must be valid numbers.")
                return redirect('customadmin:add_product')

            # Create product
            product = Products.objects.create(
                name=name,
                description=description,
                category_id=category_id,
                brand_id=brand_id or None,
                product_type=product_type,
                stock=total_stock,
                is_active=True,
            )

            
            for w, p, s in zip(variants_weight, variants_price, variants_stock):
                if w and p and s:
                    Variant.objects.create(
                        product=product,
                        weight=w,
                        variant_price=float(p),
                        quantity_in_stock=int(s),
                    )

            
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

    # Handle GET request
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
                    if float(p) < 0:
                        messages.error(request, "Variant price cannot be negative.")
                        return redirect('customadmin:edit_product', product_id=product.id)
                    if int(s) < 0:
                        messages.error(request, "Variant stock cannot be negative.")
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
                            variant.save()
                            updated_variant_ids.append(v_id)
                    else:
                        variant = Variant.objects.create(
                            product=product,
                            weight=w,
                            variant_price=price,
                            quantity_in_stock=stock,
                        )
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

def admin_logout(request):
    logout(request)
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

    # Base queryset with related optimization
    orders_list = Order.objects.select_related('user')\
        .prefetch_related('items__product_variant__product')\
        .order_by('-created_at')

    # Search filter
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
        # Order by total amount ascending (assumed total_amount field)
        orders_list = orders_list.order_by('total_amount')
    elif sort_by == 'price_desc':
        orders_list = orders_list.order_by('-total_amount')
    elif sort_by == 'name_asc':
        # Sort by user's first name ascending
        orders_list = orders_list.order_by('user__first_name')
    elif sort_by == 'name_desc':
        orders_list = orders_list.order_by('-user__first_name')
    else:
        # Default ordering
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
        # Fetch the order item with related order and payment
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order = order_item.order

        if request.method == 'POST':
            new_status = request.POST.get('status', '').strip()

            # Validate status choice
            if new_status not in dict(OrderItem.STATUS_CHOICES).keys():
                messages.error(request, "Invalid status selected.")
                return redirect('customadmin:admin_order_list_view')

            # Prevent changing to 'cancelled' status
            if new_status == 'cancelled':
                messages.error(request, "Cannot manually change status to cancelled.")
                return redirect('customadmin:admin_order_list_view')

            # Comprehensive Status Change Logic
            try:
                with transaction.atomic():
                    # Update Order Item Status
                    order_item.status = new_status
                    order_item.save()

                    # Handle Payment Status for COD Orders
                    try:
                        payment = order.payment
                        
                        # Update payment status based on order item status and payment method
                        if payment.payment_method == 'cod':
                            if new_status in ['shipped', 'delivered']:
                                payment.status = 'completed'
                            payment.save()

                    except Payment.DoesNotExist:
                        # Log or handle case where payment doesn't exist
                        messages.warning(request, "No payment record found for this order.")

                    # Optional: Update overall order status if all items are in same status
                    order_statuses = order.items.values_list('status', flat=True).distinct()
                    if len(order_statuses) == 1:
                        # If all items have same status, potentially update order status
                        if new_status == 'delivered':
                            # Mark order as fully delivered
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
        return redirect('customamdin:admin_return_requests')

    try:
        with transaction.atomic():
            if action == 'approve':
                # **1. Restock the product**
                product_variant = order_item.product_variant
                product_variant.stock += order_item.quantity
                product_variant.save()

                # **2. Calculate Refund (Item Price + Shipping Share)**
                order = order_item.order
                total_items = order.items.filter(status__in=["pending", "processing", "shipped", "delivered"]).count()

                if total_items > 1:
                    per_item_shipping_charge = order.shipping_charge / Decimal(total_items)
                else:
                    per_item_shipping_charge = order.shipping_charge  # If only one item, refund full shipping charge

                refund_amount = (order_item.product_variant.product.variant_price * Decimal(order_item.quantity)) + per_item_shipping_charge

                # **3. Check if the order has a valid payment**
                payment = getattr(order, "payment", None)  # Safely get the payment attribute
                if payment and payment.status == "completed":
                    wallet, _ = Wallet.objects.get_or_create(user=order.user)
                    wallet.add_amount(refund_amount, reason="Order Return Refund")
                else:
                    messages.warning(request, "Order has no valid payment. Refund not processed.")

                # **4. Mark the order item as returned**
                order_item.return_status = "approved"
                order_item.status = "returned"
                order_item.save()

                messages.success(request, "Return request approved. Refund processed if payment exists.")
            else:
                order_item.return_status = "rejected"
                order_item.save()
                messages.success(request, "Return request rejected.")

    except Exception as e:
        print(f"Exception: {e}")  # Debugging
        messages.error(request, "An error occurred while processing the return request.")

    return redirect('customadmin:admin_return_requests')


