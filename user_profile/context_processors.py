from cart.models import Cart
from wishlist.models import Wishlist

def get_cart_item_count(request):
    cart_item_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item_count = cart.items.count()  
    return {"cart_item_count": cart_item_count}


def get_wishlist_item_count(request):
    wishlist_item_count = 0
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_item_count = wishlist.items.count()
    return {"wishlist_item_count" : wishlist_item_count}
