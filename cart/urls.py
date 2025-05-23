from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


app_name = 'cart'

urlpatterns = [
    path('cart_view/', views.view_cart, name='view_cart'),
    path('add_to_cart/<int:variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-quantity/', views.update_quantity, name='update_quantity'),
    path('remove-item/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),   
    path('checkout/buy_now/<int:variant_id>/', views.buy_now, name='buy_now'),
    # path('razorpay_payment_success/', views.razorpay_payment_success, name='razorpay_payment_success'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    # path('create_razorpay_order/', views.create_razorpay_order, name='create_razorpay_order'),
    # path('verify_razorpay_payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'), 
    # path('pay-later/<int:order_id>/', views.pay_later, name='pay_later'),
    # path('retry-payment/<int:order_id>/', views.retry_payment, name='retry_payment'),
    # path('verify-payment/<int:order_id>/', views.verify_payment, name='verify_payment'),
    # path("apply-coupon/", views.apply_coupon, name="apply_coupon"),
    # path('remove-coupon/', views.remove_coupon, name='remove_coupon')
      path('update-variant/', views.update_variant, name='update_variant'),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
