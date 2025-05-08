from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count, Min, Max
from django.core.paginator import Paginator
from .models import Products, Category, Brand


from django.db.models import Avg
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Products, Category  


from django.shortcuts import render
from django.db.models import Q, Min
from .models import Products, Brand, Category

def product_list_view(request):
    search_query = request.GET.get('search', '')
    brand_filter = request.GET.get('brand', '')
    category_filter = request.GET.get('category', '')
    price_filter = request.GET.get('price', '')  # e.g., "100-500"
    sort_by = request.GET.get('sort', '')
    page_number = request.GET.get('page')

    

    # Annotate products with the lowest variant_price
    products = Products.objects.filter(is_active=True) \
        .select_related('brand', 'category') \
        .prefetch_related('variants', 'images') \
        .annotate(min_price=Min('variants__variant_price'))

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    if brand_filter:
        products = products.filter(brand__id=brand_filter)

    if category_filter:
        products = products.filter(category__id=category_filter)

    if price_filter:
        try:
            min_p, max_p = map(float, price_filter.split('-'))
            products = products.filter(min_price__gte=min_p, min_price__lte=max_p)
        except ValueError:
            pass  # Invalid price input

    if sort_by == 'price_asc':
        products = products.order_by('min_price')
    elif sort_by == 'price_desc':
        products = products.order_by('-min_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 5)  # 10 products per page
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj, 
        # 'products': products,
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
from .models import Products

logger = logging.getLogger(__name__)

from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
import logging
from .models import Products

logger = logging.getLogger(__name__)

def product_detail_view(request, slug):
    logger.info(f"Loading product details for slug: {slug}")
    
    try:
        # Fetch the product and related data
        product = get_object_or_404(
            Products.objects.select_related('brand', 'category')
                            .prefetch_related('variants', 'reviews__user', 'images'),
            slug=slug,
            is_active=True
        )
        
        logger.info(f"Found product: {product.name} (ID: {product.id})")

        # Primary image logic
        images = list(product.images.all())
        primary_image = product.images.filter(is_primary=True).first() or (images[0] if images else None)
        if primary_image:
            logger.info(f"Primary image URL: {primary_image.image.url}")
        else:
            logger.warning("No primary image found")

        # Variants
        variants = product.variants.all()
        if not variants:
            logger.warning("No variants found")

        # Reviews and ratings
        reviews = product.reviews.all().order_by('-created_at')
        average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0


        # stock = product.stock.all()

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
            if not sim_product.images.exists():
                logger.warning(f"Similar product {sim_product.id} has no images")
            else:
                logger.info(f"Similar product {sim_product.name} primary image: {sim_product.thumbnail()}")

        context = {
            'product': product,
            'variants': variants,
            'primary_image': primary_image,
            'images': images,
            'reviews': reviews,
            'average_rating': average_rating,
            'rating_counts': rating_counts,
            'similar_products': similar_products,
        }

        return render(request, 'product_details.html', context)

    except Exception as e:
        logger.error(f"Error loading product detail: {str(e)}")
        raise


def about(request):
    return render(request, 'about.html')