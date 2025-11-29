from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Cart, CartItem
from apps.product.models import Product, Size, Color

def get_or_create_cart(request):
    """Helper function to get or create cart for user/session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'session_id': None}
        )
    else:
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(
            session_id=request.session.session_key,
            user=None
        )
    return cart


def cart_view(request):
    """Display cart contents"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product', 'size', 'color').all()

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_items': cart.get_total_items(),
        'subtotal': cart.get_subtotal(),
        'total_price': cart.get_total_price(),
        'discount': cart.applied_discount,
    }
    return render(request, 'cart/cart.html', context)

@require_POST
def add_to_cart(request):
    try:
        """Add product to cart"""
        cart = get_or_create_cart(request)
        if not cart:
            messages.error(request, 'Could not create or retrieve cart.')
            return redirect('product_list')
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        size_id = request.POST.get('size')
        color_id = request.POST.get('color')
        size = None
        color = None

        
        # Get the product and check if it can be ordered
        product = get_object_or_404(Product, id=product_id, is_active=True)
        if product.sizes.exists():
            if not size_id == '':
                size = get_object_or_404(Size, id=size_id, product=product)
            else:
                messages.error(request, 'Please select a size.')
                return redirect('product_detail', slug=product.slug)
        if product.colors.exists():
            if not color_id == '':
                color = get_object_or_404(Color, id=color_id, product=product)
            else:
                messages.error(request, 'Please select a color.')
                return redirect('product_detail', slug=product.slug)

        if not product.can_order(quantity):
            messages.error(request, f'Sorry, {product.name} is out of stock or has insufficient quantity.')
            return redirect('product_detail', slug=product.slug)
        
        # If the Same product is already in the cart, update the quantity
        existing_item = cart.items.filter(product=product, size=size, color=color).first()
        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            messages.success(request, f'{product.name} quantity updated in cart.')
            return redirect('product_detail', slug=product.slug)

        
        # Create cart item
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            size=size,
            color=color
        )
        if request.POST.get('next') == 'checkout':
            return redirect('checkout')

        messages.success(request, f'{product.name} added to cart.')
        return redirect('product_detail', slug=product.slug)
    except Exception as e:
        messages.error(request, f'Error adding item to cart: {e}')
        return redirect('product_detail', slug=product.slug)

@require_POST
def increase_cart_item_quantity(request):
    """increas quantity by 1"""
    try:
        item_id = request.POST.get('item_id')
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        if cart_item.quantity >= cart_item.product.stock_quantity:
            messages.warning(request, "Stock limit up")
            return redirect('cart')
        cart_item.quantity += 1
        cart_item.save()
        return redirect('cart')

    except Exception as e:
        messages.error(request, f'Error updating item quantity in cart: {e}')
        return redirect('cart')
    
@require_POST
def decrease_cart_item_quantity(request):
    """decrease quantity by 1"""
    try:
        item_id = request.POST.get('item_id')
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        if cart_item.quantity == 1:
            messages.warning(request, "Can't decrease")
            return redirect('cart')
        cart_item.quantity -= 1
        cart_item.save()
        return redirect('cart')

    except Exception as e:
        messages.error(request, f'Error updating item quantity in cart: {e}')
        return redirect('cart')

@require_POST
def remove_from_cart(request):
    """Remove item from cart"""
    try:
        item_id = request.POST.get('item_id')
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f'{product_name} removed from cart.')
        return redirect('cart')

    except Exception as e:
        messages.error(request, f'Error removing item from cart: {e}')
        return redirect('cart')


@require_POST
def apply_promo_code(request):
    """Apply promo code to cart via AJAX"""
    try:
        cart = get_or_create_cart(request)
        promo_code = request.POST.get('promo_code', '').strip()

        if not promo_code:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a promo code'
            }, status=400)

        # Apply promo code
        success, message = cart.apply_promo_code(promo_code)

        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'data': {
                    'subtotal': float(cart.get_subtotal()),
                    'discount': float(cart.applied_discount),
                    'total': float(cart.get_total_price()),
                    'promo_code': cart.promo_code.code if cart.promo_code else None
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


@require_POST
def remove_promo_code(request):
    """Remove promo code from cart via AJAX"""
    try:
        cart = get_or_create_cart(request)
        cart.remove_promo_code()

        return JsonResponse({
            'success': True,
            'message': 'Promo code removed',
            'data': {
                'subtotal': float(cart.get_subtotal()),
                'discount': 0,
                'total': float(cart.get_subtotal()),
                'promo_code': None
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)