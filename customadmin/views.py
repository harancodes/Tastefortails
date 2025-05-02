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




def admin_required(view_func):
    decorator = user_passes_test(lambda u: u.is_authenticated and u.is_staff)
    return decorator(view_func)


@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('customadmin:admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('customadmin:admin_dashboard')  
        else:
            messages.error(request, "Invalid username or password")
            return redirect('customadmin:admin_login')  


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

    paginator = Paginator(users, 10)
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



@admin_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if not name:
            messages.error(request, "Category name cannot be empty.")
            return redirect('customadmin:add_category')

        Category.objects.create(name=name, image=image if image else 'category/default_image.jpg')
        messages.success(request, "Category added successfully.")
        return redirect('customadmin:category_list')

    return render(request, 'add_category.html')



@admin_required
def category_list(request):
    categories = Category.objects.filter(is_active=True) # 

    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(name__icontains=search_query)

    categories = categories.order_by('-created_at')  # sort by latest created

    paginator = Paginator(categories, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'category_list.html', {
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

    return render(request, 'edit_category.html', {'category': category})



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


@admin_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')  # optional
        product_type = request.POST.get('product_type')
        stock = request.POST.get('stock')
        is_active = request.POST.get('is_active', 'on') == 'on'

        # Validate required fields
        if not all([name, category_id, product_type, stock]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('customadmin:add_product')

        try:
            stock = int(stock)
        except ValueError:
            messages.error(request, "Stock must be a number.")
            return redirect('customadmin:add_product')

        # Create product
        product = Products.objects.create(
            name=name,
            description=description,
            category_id=category_id,
            brand_id=brand_id if brand_id else None,
            product_type=product_type,
            stock=stock,
            is_active=is_active,
        )

        # Handle variants (optional)
        variants_weight = request.POST.getlist('variants_weight[]')
        variants_price = request.POST.getlist('variants_price[]')
        variants_stock = request.POST.getlist('variants_stock[]')

        for w, p, s in zip(variants_weight, variants_price, variants_stock):
            if w.strip() and p.strip() and s.strip():
                try:
                    Variant.objects.create(
                        product=product,
                        weight=w.strip(),
                        variant_price=float(p),
                        quantity_in_stock=int(s),
                        is_active=True,
                    )
                except Exception as e:
                    # Log or handle errors if needed
                    pass

        
        main_image = request.FILES.get('main_image')
        if main_image:
            ProductImage.objects.create(
                product=product,
                image=main_image,
                is_primary=True,
            )


        for i in range(1, 4):  
            other_image = request.FILES.get(f'other_image_{i}')
            if other_image:
                ProductImage.objects.create(
                    product=product,
                    image=other_image,
                    is_primary=False,
                )

        messages.success(request, f"Product '{name}' added successfully.")
        return redirect('customadmin:product_list')


    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    return render(request, 'admin_product_add_edit.html', {
        'categories': categories,
        'brands': brands,
    })


@admin_required
def product_list(request):
    products = Products.objects.filter(is_active=True).order_by('-created_at')
    
    
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'latest':
        products = products.order_by('-created_at')

    
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(request, 'admin_product.html', {
        'products': products,
        'search_query': search_query,
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