from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate
from django.contrib import messages
from authentication.models import CustomUser
from .models import Wishlist, WishlistItem, Variant
from authentication.views import block_superuser_navigation
from django.http import JsonResponse
from product.models import Products, Variant
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from product.views import login_required_custom
from django.core.paginator import Paginator

@block_superuser_navigation
@never_cache
@login_required_custom

def wishlist_view(request):
    # Get all wishlist items for the logged-in user
    wishlist_items = WishlistItem.objects.filter(wishlist__user=request.user).select_related('variant', 'variant__product', 'variant__product__brand')

    # Pagination setup (e.g., 12 items per page)
    paginator = Paginator(wishlist_items, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all variant IDs in wishlist to mark hearts in template
    wishlist_ids = wishlist_items.values_list('variant_id', flat=True)

    context = {
        'page_obj': page_obj,
        'wishlist_ids': list(wishlist_ids),
    }
    return render(request, 'wishlist.html', context)



@block_superuser_navigation
@never_cache
@login_required_custom
def wishlist_add(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(Variant, id=variant_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        try:
            wishlist_item, created = WishlistItem.objects.get_or_create(
                wishlist=wishlist,
                variant=variant
            )
            if created:
                return JsonResponse({'success': True, 'message': 'Added to wishlist'})
            else:
                return JsonResponse({'success': True, 'message': 'Item already in wishlist'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@block_superuser_navigation
@never_cache
@login_required_custom
def wishlist_remove(request, variant_id):
    if request.method == 'POST':
        wishlist = Wishlist.objects.get(user=request.user)
        item = get_object_or_404(WishlistItem, wishlist=wishlist, variant_id=variant_id)
        item.delete()
        return JsonResponse({'success': True, 'message': 'Removed from wishlist'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)



@block_superuser_navigation  
@never_cache
@login_required_custom
def wishlist_status(request):
    """Return a list of product variant IDs in the user's wishlist"""
    wishlist_items = WishlistItem.objects.filter(
        wishlist__user=request.user
    ).values_list('variant_id', flat=True)

    return JsonResponse({'items': list(wishlist_items)})




        













