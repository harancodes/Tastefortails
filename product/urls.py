from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'products'

urlpatterns = [
    path('list/', views.product_list_view, name='list'),  
    path('<slug:slug>/', views.product_detail_view, name='detail'),
    path('about', views.about, name='about'),
    #  path('product/<int:id>/', views.product_detail_view, name='product_detail_view'),
    # Consider adding other useful URLs:
    # path('category/<slug:category_slug>/', views.category_view, name='category'),
    # path('brand/<slug:brand_slug>/', views.brand_view, name='brand'),
    # path('search/', views.search_view, name='search'),
]

# Only add static/media URL patterns in DEBUG mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)