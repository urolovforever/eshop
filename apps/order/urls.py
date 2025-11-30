from django.urls import path
from .views import *

app_name = 'checkout'

urlpatterns = [
    path('', order_list, name='order_list'),
    path('checkout/', checkout_view, name='checkout'),
    path('confirmation/<str:order_number>/', confirmation, name='confirmation'),
    path('<int:pk>/', order_detail, name='order_detail'),
    # path('<int:pk>/cancel/', order_cancel, name='order_cancel'),
]