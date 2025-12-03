# templatetags/ecommerce_tags.py

from django import template
from django.db.models import Count, Sum, Avg, Q
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse
from decimal import Decimal
import json

from apps.product.models import Product, Category
from  apps.order.models import Order
from apps.cart.models import Cart, CartItem

register = template.Library()


# =============================================================================
# INCLUSION TAGS - Render template fragments
# =============================================================================

@register.inclusion_tag('product/product_card.html')
def product_card(product):
    """Render a product card"""
    return {
        'product': product,
    }


@register.inclusion_tag('ecommerce/tags/category_menu.html')
def category_menu(current_category=None):
    """Render category navigation menu"""
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0)
    
    return {
        'categories': categories,
        'current_category': current_category,
    }


@register.inclusion_tag('ecommerce/tags/cart_summary.html', takes_context=True)
def cart_summary(context):
    """Render cart summary widget"""
    request = context['request']
    cart = None
    
    if request.user.is_authenticated:
        cart = getattr(request.user, 'cart', None)
    else:
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id).first()
    
    if cart:
        total_items = cart.get_total_items()
        total_price = cart.get_total_price()
    else:
        total_items = 0
        total_price = Decimal('0.00')
    
    return {
        'cart': cart,
        'total_items': total_items,
        'total_price': total_price,
        'request': request,
    }


@register.inclusion_tag('ecommerce/tags/product_filters.html')
def product_filters(category=None, price_range=None, in_stock_only=False):
    """Render product filtering options"""
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    
    # Price ranges
    price_ranges = [
        (0, 25, "Under $25"),
        (25, 50, "$25 - $50"),
        (50, 100, "$50 - $100"),
        (100, 200, "$100 - $200"),
        (200, None, "Over $200"),
    ]
    
    return {
        'categories': categories,
        'price_ranges': price_ranges,
        'current_category': category,
        'current_price_range': price_range,
        'in_stock_only': in_stock_only,
    }


@register.inclusion_tag('ecommerce/tags/breadcrumb.html')
def breadcrumb(items):
    """Render breadcrumb navigation"""
    return {'items': items}


@register.inclusion_tag('ecommerce/tags/product_gallery.html')
def product_gallery(product):
    """Render product image gallery"""
    images = product.get_all_images()
    primary_image = product.get_primary_image()
    
    return {
        'product': product,
        'images': images,
        'primary_image': primary_image,
    }


@register.inclusion_tag('ecommerce/tags/related_products.html')
def related_products(product, limit=4):
    """Show related products from same category"""
    related = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:limit]
    
    return {
        'products': related,
        'title': f"More from {product.category.name}",
    }


@register.inclusion_tag('ecommerce/tags/order_status_badge.html')
def order_status_badge(order):
    """Render order status badge"""
    status_config = {
        'pending': {'class': 'warning', 'icon': 'clock'},
        'confirmed': {'class': 'info', 'icon': 'check'},
        'processing': {'class': 'primary', 'icon': 'cog'},
        'shipped': {'class': 'success', 'icon': 'truck'},
        'delivered': {'class': 'success', 'icon': 'check-circle'},
        'cancelled': {'class': 'danger', 'icon': 'times'},
    }
    
    config = status_config.get(order.status, {'class': 'secondary', 'icon': 'question'})
    
    return {
        'order': order,
        'badge_class': config['class'],
        'icon': config['icon'],
    }




# =============================================================================
# SIMPLE TAGS - Return values directly
# =============================================================================

@register.simple_tag
def get_featured_products(limit=8):
    """Get featured products (latest active products)"""
    return Product.objects.filter(is_active=True).order_by('-created_at')[:limit]


@register.simple_tag
def get_popular_products(limit=8):
    """Get popular products based on order frequency"""
    return Product.objects.filter(is_active=True).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:limit]


@register.simple_tag
def get_low_stock_products(threshold=10):
    """Get products with low stock"""
    return Product.objects.filter(
        is_active=True,
        stock_quantity__lte=threshold,
        stock_quantity__gt=0
    )


@register.simple_tag
def get_cart_item_count(request):
    """Get total items in user's cart"""
    if request.user.is_authenticated:
        cart = getattr(request.user, 'cart', None)
        return cart.get_total_items() if cart else 0
    else:
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id).first()
            return cart.get_total_items() if cart else 0
    return 0


@register.simple_tag
def get_wishlist_item_count(request):
    """Get total items in user's wishlist"""
    from main.models import Wishlist
    if request.user.is_authenticated:
        return Wishlist.objects.filter(user=request.user).count()
    return 0


@register.simple_tag
def get_user_orders(user, limit=5):
    """Get user's recent orders"""
    if user.is_authenticated:
        return user.get_orders()[:limit]
    return []


@register.simple_tag
def calculate_savings(original_price, sale_price):
    """Calculate savings amount and percentage"""
    if original_price and sale_price and original_price > sale_price:
        savings = original_price - sale_price
        percentage = (savings / original_price) * 100
        return {
            'amount': savings,
            'percentage': round(percentage, 1)
        }
    return None


@register.simple_tag
def get_category_tree():
    """Get hierarchical category structure"""
    return Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('name')



@register.simple_tag
def stock_status(product, show_stock_count=False):
    """Return HTML badge for stock status"""
    if product.stock_quantity == 0:
        return mark_safe('<span class="text-red-600 text-sm ml-2">Out of Stock</span>')
    if show_stock_count:
        if product.stock_quantity < 10:
            return mark_safe(f'<span class="text-yellow-600 text-sm ml-2">Only {product.stock_quantity} left</span>')
        return mark_safe(f'<span class="text-green-600 text-sm ml-2">{product.stock_quantity} In Stock</span>')
    
    return mark_safe('<span class="text-green-600 text-sm ml-2">In Stock</span>')


# =============================================================================
# FILTERS - Transform values
# =============================================================================

@register.filter
def taka(value):
    """Format value as so'm (Uzbek currency)"""
    try:
        # Format number with space as thousand separator
        num = int(value)
        # Convert to string and add spaces every 3 digits from right
        num_str = str(num)
        # Reverse the string, add spaces, then reverse back
        formatted = ' '.join([num_str[::-1][i:i+3] for i in range(0, len(num_str), 3)])[::-1]
        return f"{formatted} so'm"
    except (ValueError, TypeError):
        return "0 so'm"


@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if total == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def multiply(*args):
    """Multiply all values"""
    try:
        result = 1
        for value in args:
            result *= float(value)
        return result
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """Subtract two values"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def in_stock_class(product):
    """Return CSS class based on stock status"""
    if product.stock_quantity == 0:
        return 'out-of-stock'
    elif product.stock_quantity < 10:
        return 'low-stock'
    else:
        return 'in-stock'



@register.filter
def order_status_class(status):
    """Return CSS class for order status"""
    status_classes = {
        'pending': 'warning',
        'confirmed': 'info',
        'processing': 'primary',
        'shipped': 'success',
        'delivered': 'success',
        'cancelled': 'danger',
    }
    return status_classes.get(status, 'secondary')


@register.filter
def rating_stars(rating):
    """Convert rating to star HTML"""
    try:
        rating = float(rating)
        full_stars = int(rating)
        half_star = rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)
        
        html = '★' * full_stars
        if half_star:
            html += '☆'
        html += '☆' * empty_stars
        
        return mark_safe(f'<span class="rating-stars">{html}</span>')
    except (ValueError, TypeError):
        return mark_safe('<span class="rating-stars">☆☆☆☆☆</span>')


@register.filter
def json_encode(value):
    """Encode value as JSON for JavaScript"""
    return mark_safe(json.dumps(value))


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    return dictionary.get(key)


@register.filter
def has_size_variants(product):
    """Check if product has size variants"""
    return product.sizes.exists()


@register.filter
def has_color_variants(product):
    """Check if product has color variants"""
    return product.colors.exists()


@register.filter
def is_in_wishlist(product, user):
    """Check if product is in user's wishlist"""
    from main.models import Wishlist
    if user.is_authenticated:
        return Wishlist.objects.filter(user=user, product=product).exists()
    return False


@register.filter
def format_phone(phone):
    """Format phone number"""
    try:
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, str(phone)))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return phone
    except:
        return phone


@register.filter
def days_since(date):
    """Calculate days since a date"""
    try:
        from django.utils import timezone
        delta = timezone.now().date() - date
        return delta.days
    except:
        return 0


@register.filter
def shipping_status(order):
    """Get shipping status description"""
    if order.status == 'shipped' and order.shipped_at:
        from django.utils import timezone
        days = (timezone.now().date() - order.shipped_at.date()).days
        if days == 0:
            return "Shipped today"
        elif days == 1:
            return "Shipped yesterday"
        else:
            return f"Shipped {days} days ago"
    elif order.status == 'delivered':
        return "Delivered"
    elif order.status in ['confirmed', 'processing']:
        return "Preparing for shipment"
    else:
        return "Not shipped"


# =============================================================================
# ASSIGNMENT TAGS - Set template variables
# =============================================================================

@register.simple_tag(takes_context=True)
def set_var(context, name, value):
    """Set a template variable"""
    context[name] = value
    return ''


@register.simple_tag
def config(name, default=None):
    """Get Django setting value"""
    from main.models import Config
    config = Config.objects.first()
    if config:
        return getattr(config, name, default)
    return default


@register.simple_tag
def query_string(request, **kwargs):
    """Build query string from current request and additional parameters"""
    query_dict = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            query_dict.pop(key, None)
        else:
            query_dict[key] = value
    return query_dict.urlencode()


# =============================================================================
# CUSTOM FILTERS FOR FORMS
# =============================================================================

@register.filter
def add_class(field, css_class):
    """Add CSS class to form field"""
    return field.as_widget(attrs={'class': css_class})


@register.filter
def add_placeholder(field, placeholder):
    """Add placeholder to form field"""
    return field.as_widget(attrs={'placeholder': placeholder})


@register.filter
def field_type(field):
    """Get form field type"""
    return field.field.widget.__class__.__name__.lower()


# =============================================================================
# CONDITIONAL TAGS
# =============================================================================

@register.simple_tag
def if_user_can_edit(user, obj):
    """Check if user can edit object"""
    if user.is_superuser:
        return True
    if hasattr(obj, 'user') and obj.user == user:
        return True
    return False


@register.simple_tag
def active_class(request, pattern):
    """Return 'active' if URL matches pattern"""
    from django.urls import resolve
    from django.urls.exceptions import Resolver404
    
    try:
        current_url = resolve(request.path_info).url_name
        if current_url == pattern:
            return 'active'
    except Resolver404:
        pass
    return ''