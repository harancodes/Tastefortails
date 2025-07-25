from django.urls import path
from . import views
from product.views import product_detail_view
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from .import context_processors
# from .views import ProductAPI

app_name = 'user_profile'


urlpatterns = [

    # path('brand/', views.brand_list, name='brand_list'),  # Brand list page
    # path('brand/<int:brand_id>/', views.brand_products, name='brand_products'),
    # path('products/' , views.all_products , name = 'all_products'),
    # path('about/',views.about_us , name = 'about'),


    


    # path('search/', views.search_products, name='search_products'),
    # path('<int:id>/', product_detail_view, name='product_detail'),
    path("update-profile-image/", views.update_profile_image, name="update_profile_image"),
    path('request-email-verification/', views.request_email_verification, name='request_email_verification'),
     path('verify-email/', views.verify_email, name='verify_email'),
    #    path('update-2fa/', views.update_2fa, name='update_2fa'),

    path('account-overview/', views.account_overview, name='account_overview'),
    path("manage-address/", views.manage_address, name="manage_address"),
    path("add_address/", views.add_address, name="add_address"),
    path("edit-address/<int:address_id>/", views.edit_address, name="edit_address"),
    path("delete-address/<int:address_id>/", views.delete_address, name="delete_address"),
    path('orders/', views.order_list_view, name='order_list'),
    # path('invoice/<int:item_id>/', views.generate_invoice, name='generate_invoice'),
    path('orders/item/<int:item_id>/', views.order_item_detail, name='order_item_detail'),
    path('orders/item/<int:item_id>/cancel/', views.cancel_order_item, name='cancel_order_item'),
    path('orders/item/<int:item_id>/return/', views.return_order_item, name='return_order_item'),
    path("wallet/", views.wallet_view, name="wallet_page"),
    path('submit-review/<int:order_item_id>/', views.submit_review, name='submit_review'),
    # path('api/products/', ProductAPI.as_view(), name='product_api')

path('orders/search/', views.search_products, name='search_orders'),
  path('referral/', views.referral_profile_view, name='referral_profile'),
  # urls.py
path('cancel-product/<int:order_id>/', views.cancel_product_items, name='cancel_product_items'),

path('invoice/a/<int:order_id>/', views.generate_order_invoice, name='generate_order_invoice'),
path("ajax/get-counts/", views.ajax_get_counts, name="ajax_get_counts"),

  path('notifications/', views.notification_list, name='user_notifications'),
   path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
     path('notifications/toggle/<int:notification_id>/', views.toggle_notification, name='toggle_notification'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
      path('wallet/add-money/', views.add_money_to_wallet, name='wallet_add_money'),
       path("wallet/deduct-money/", views.deduct_money_from_wallet, name="wallet_deduct_money"),
]








if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

