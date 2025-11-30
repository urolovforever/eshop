from django.urls import path
from .views import ProductListView, ProductDetailView, NewArrivalsView, OnSaleView

app_name = 'product'

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('new-arrivals/', NewArrivalsView.as_view(), name='new_arrivals'),
    path('on-sale/', OnSaleView.as_view(), name='on_sale'),
    path('<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
]