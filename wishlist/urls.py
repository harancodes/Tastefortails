from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name ='wishlist'

urlpatterns = [
    path('wishlist', views.wishlist_view, name='wishlist'),
    path('add/<int:variant_id>/', views.wishlist_add, name='add_to_wishlist'),
    path('remove/<int:variant_id>/', views.wishlist_remove, name='remove_from_wishlist'),
    path('status/', views.wishlist_status, name='wishlist_status')

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
