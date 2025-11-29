from django.db import models
from django.core.validators import MinValueValidator
from apps.product.models import Product, Size, Color



class Cart(models.Model):
    user = models.OneToOneField('main.User', on_delete=models.CASCADE, null=True, blank=True, related_name='cart')
    session_id = models.CharField(max_length=40, null=True, blank=True)
    promo_code = models.ForeignKey('order.PromoCode', on_delete=models.SET_NULL, null=True, blank=True)
    applied_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.user.username if self.user else self.session_id}"

    def get_total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    def get_subtotal(self):
        """Calculate subtotal price of all items in cart (before discount)"""
        return sum(item.get_total_price() for item in self.items.all())

    def get_total_price(self):
        """Calculate total price after discount"""
        subtotal = self.get_subtotal()
        return max(subtotal - self.applied_discount, 0)

    def apply_promo_code(self, promo_code):
        """Apply promo code to cart"""
        from apps.order.models import PromoCode

        # Get promo code
        try:
            promo = PromoCode.objects.get(code=promo_code.upper())
        except PromoCode.DoesNotExist:
            return False, "Invalid promo code"

        # Check if promo can be applied
        subtotal = self.get_subtotal()
        can_apply, message = promo.can_apply(subtotal)
        if not can_apply:
            return False, message

        # Calculate and apply discount
        discount = promo.calculate_discount(subtotal)
        self.promo_code = promo
        self.applied_discount = discount
        self.save()

        return True, f"Promo code applied! You saved ৳{discount}"

    def remove_promo_code(self):
        """Remove promo code from cart"""
        self.promo_code = None
        self.applied_discount = 0
        self.save()

    def clear_cart(self):
        """Remove all items from cart"""
        self.items.all().delete()
        self.remove_promo_code()

    def add_item(self, product, quantity=1, size=None, color=None):
        """Add item to cart or update quantity if exists"""
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            size=size,
            color=color,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        # Revalidate promo code if one is applied
        if self.promo_code:
            self.apply_promo_code(self.promo_code.code)

        return cart_item


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self):
        """Calculate total price for this cart item"""
        return self.product.price * self.quantity

    def can_add_quantity(self, additional_quantity=1):
        """Check if additional quantity can be added"""
        return self.product.can_order(self.quantity + additional_quantity)

