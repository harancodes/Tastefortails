from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name ='wishlist'

urlpatterns = [
    path('wishlist', views.wishlist_view, name='wishlist'),
    path('add/<int:variant_id>/', views.wishlist_add, name='add_to_wishlist'),
    path('remove/<int:variant_id>/', views.wishlist_remove, name='remove_from_wishlist'),
    path('status/', views.wishlist_status, name='wishlist_status'),

    # path('count/', views.wishlist_item_count, name='wishlist_item_count'),
    #     path('count/', views.cart_item_count, name='cart_item_count'),



]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
