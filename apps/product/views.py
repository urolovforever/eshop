from django.views.generic import ListView, DetailView
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator
from .models import Product, Category, Color

class ProductListView(ListView):
    """List all products with filtering and pagination"""
    model = Product
    template_name = 'product/products.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('colors', 'sizes')

        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(short_description__icontains=search_query)
            )

        # Category filtering
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Color filtering
        color_names = self.request.GET.getlist('color')
        if color_names:
            queryset = queryset.filter(colors__name__in=color_names).distinct()

        # Price filtering
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        # Sorting
        sort_by = self.request.GET.get('sort', 'newest')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Categories
        context['categories'] = Category.objects.all()

        # Get all unique colors from active products
        all_colors = Color.objects.filter(product__is_active=True).values('name', 'hex_code').distinct()
        context['available_colors'] = all_colors

        # Get price range
        price_range = Product.objects.filter(is_active=True).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        context['price_range'] = price_range

        # Current filters
        context['current_category'] = self.request.GET.get('category', '')
        context['selected_colors'] = self.request.GET.getlist('color')
        context['current_min_price'] = self.request.GET.get('min_price', '')
        context['current_max_price'] = self.request.GET.get('max_price', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['current_sort'] = self.request.GET.get('sort', 'newest')

        # Build query string for pagination
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            query_params.pop('page')
        context['query_string'] = query_params.urlencode()

        # Product count
        context['product_count'] = self.get_queryset().count()

        return context


class ProductDetailView(DetailView):
    """Detailed product view"""
    model = Product
    template_name = 'product/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        context['sizes'] = product.sizes.all()
        context['colors'] = product.colors.all()
        context['images'] = product.images.all()
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product.id)[:4]
        return context


class CategoryDetailView(DetailView):
    """Category detail view with products"""
    model = Category
    template_name = 'store/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()

        # Get products in this category with pagination
        products = Product.objects.filter(
            category=category,
            is_active=True
        ).order_by('name')

        paginator = Paginator(products, 12)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['products'] = page_obj
        context['product_count'] = products.count()
        return context


class NewArrivalsView(ListView):
    """View for new arrival products"""
    model = Product
    template_name = 'product/new_arrivals.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            is_new_arrival=True
        ).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'New Arrivals'
        return context


class OnSaleView(ListView):
    """View for products on sale"""
    model = Product
    template_name = 'product/on_sale.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            on_sale=True
        ).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'On Sale'
        return context
