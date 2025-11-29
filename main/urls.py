from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('robots.txt', include('robots.urls')),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/count/', views.get_wishlist_count, name='wishlist_count'),
    path('product/', include('apps.product.urls'), name='product'),
    path('cart/', include('apps.cart.urls'), name='cart'),
    path('checkout/', include('apps.order.urls'), name='checkout'),
]
# serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

