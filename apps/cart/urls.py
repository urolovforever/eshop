from django.urls import path
from .views import *

app_name = 'cart'

urlpatterns = [
    path('', cart_view, name='cart_view'),
    path('add/', add_to_cart, name='add_to_cart'),
    path('quick-add/', quick_add_to_cart, name='quick_add_to_cart'),
    path('remove/', remove_from_cart, name='remove_from_cart'),
    path('increase/', increase_cart_item_quantity, name='increase_cart_item_quantity'),
    path('decrease/', decrease_cart_item_quantity, name='decrease_cart_item_quantity'),
    path('apply-promo/', apply_promo_code, name='apply_promo_code'),
    path('remove-promo/', remove_promo_code, name='remove_promo_code'),
]