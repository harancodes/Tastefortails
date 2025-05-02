from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from .models import Products, Category, Brand


from django.db.models import Avg
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Products, Category  # Include your relevant models

def product_list_view(request):
    # Start with only active products
    search_query = request.GET.get('search', '')
    brand_filter = request.GET.get('brand', '')
    category_filter = request.GET.get('category', '')
    price_filter = request.GET.get('price', '')
    sort_by = request.GET.get('sort', '')

    # Initial queryset for active products
    products = Products.objects.filter(is_active=True)

    # Search filter
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Brand filter
    if brand_filter:
        products = products.filter(brand__id=brand_filter)

    # Category filter
    if category_filter:
        products = products.filter(category__id=category_filter)

    # Price filter
    if price_filter:
        try:
            if '-' in price_filter:
                min_price, max_price = price_filter.split('-')
                if min_price:
                    products = products.filter(sales_price__gte=int(min_price))
                if max_price:
                    products = products.filter(sales_price__lte=int(max_price))
        except ValueError:
            pass

    # Sorting options
    if sort_by == 'price_asc':
        products = products.order_by('sales_price')
    elif sort_by == 'price_desc':
        products = products.order_by('-sales_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')

    # Context for rendering product list
    context = {
        'products': products,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
        'search_query': search_query,
        'brand_filter': brand_filter,
        'category_filter': category_filter,
        'price_filter': price_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'product_list.html', context)





from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
import logging

# from pro.models import Products  # Adjust import path as needed

logger = logging.getLogger(__name__)

def product_detail_view(request, slug):
    # Log start of view processing
    logger.info(f"Loading product details for slug: {slug}")
    
    try:
        # Get the product with all related data
        product = get_object_or_404(
            Products.objects.select_related('brand', 'category')
                            .prefetch_related('variants', 'reviews__user', 'images'),
            slug=slug,
            is_active=True
        )
        
        logger.info(f"Found product: {product.name} (ID: {product.id})")
        
        
        # Get product images
        images = list(product.images.all())
        primary_image = product.images.filter(is_primary=True).first()
        
        if not images:
            logger.warning(f"No images found for product {product.id}")
        else:
            logger.info(f"Found {len(images)} images for product {product.id}")
        
        if not primary_image and images:
            primary_image = images[0]
            logger.info("Using first image as primary image")

        # Get variants
        variants = list(product.variants.all())
        if not variants:
            logger.warning(f"No variants found for product {product.id}")
        else:
            logger.info(f"Found {len(variants)} variants for product {product.id}")

        # Reviews & ratings
        reviews = product.reviews.all().order_by('-created_at')
        average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        rating_counts = []
        total_reviews = reviews.count()
        if total_reviews > 0:
            for i in range(5, 0, -1):
                count = reviews.filter(rating=i).count()
                percentage = (count / total_reviews) * 100
                rating_counts.append({
                    'rating': i,
                    'count': count,
                    'percentage': percentage
                })

        # Similar products
        similar_products = (
            Products.objects.filter(category=product.category, is_active=True)
            .exclude(id=product.id)
            .select_related('brand')
            .prefetch_related('variants', 'images')[:4]
        )

        for sim_product in similar_products:
            if not sim_product.images.all():
                logger.warning(f"Similar product {sim_product.id} has no images")

        # features_str = product.features or ""
        # product_features = [f.strip() for f in features_str.split(",") if f.strip()]

        # Final context
        context = {
            'product': product,
            'variants': variants,
            'reviews': reviews,
            'average_rating': average_rating,
            'rating_counts': rating_counts,
            'similar_products': similar_products,
            'images': images,
            'primary_image': primary_image,
            # 'product_features': product_features
        }

        logger.info("Successfully prepared context for product detail template")
        return render(request, 'product_details.html', context)

    except Exception as e:
        logger.error(f"Error loading product detail: {str(e)}")
        raise


#e
def about(request):
    return render(request, 'about.html')