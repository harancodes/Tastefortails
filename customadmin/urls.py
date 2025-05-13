from .views import user_list, block_user
from django.conf import settings
from django.conf.urls.static import static
from customadmin import views
from django.urls import path
from  . import views
app_name = 'customadmin'

urlpatterns = [
    path('', views.admin_login, name='customadmin_home'),  
    path('users/', views.user_list, name='user_list'),
    path('users/block/<int:user_id>/', views.block_user, name='block_user'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:category_id>/', views.edit_category, name='edit_category'),  
    # path('categories/delete/<int:category_id>/', views.soft_delete_category, name='delete_category'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),

    # path('products/toggle/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
path('products/delete/<int:product_id>/', views.soft_delete_product, name='soft_delete_product'),
path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),

    
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
     path('categories/toggle/<int:category_id>/', views.toggle_list_category, name='toggle_list_category'),
      path('categories/delete/<int:category_id>/', views.soft_delete_category, name='soft_delete_category'),
    #   path('banner/' ,views.banner_list , name='banner_list'),
      path('banner/', views.banner_list, name='banner_list'),
      path('banner', views.add_banner, name='add_banner'),
      path('banner/toggle-list/<int:banner_id>/', views.toggle_list_banner, name='toggle_list_banner'),
path('banner/edit/<int:banner_id>/', views.edit_banner, name='edit_banner'),
path('banner/delete/<int:banner_id>', views.soft_delete_banner, name='soft_delete_banner'),
path('brands/add/', views.add_brands, name='add_brands'),
path('brands/', views.brands, name='brands_list'),


path('brands/toggle-active/<int:brand_id>/', views.toggle_active_status, name='toggle_active_status'),
path('brands/delete/<int:brand_id>/', views.soft_delete_brands, name='soft_delete_brands'),
path('brands/edit/<int:brand_id>/', views.edit_brands, name='edit_brands'),


path('products/<int:product_id>/toggle/', views.toggle_product_status, name='toggle_product_status'),








]

   

