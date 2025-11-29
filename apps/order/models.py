from django.db import models
from django.core.validators import MinValueValidator
from main.models import User
from apps.product.models import Product, Size, Color

class Address(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    district = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return f'Name: {self.name}\n\n Phone:{self.phone}\n\n Email:{self.email if self.email else "No Email"}\n\n Address: {self.district}, {self.address}'
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    address = models.ForeignKey(Address, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number"""
        import random
        while True:
            order_number = f"ORD-{random.randint(1000000, 9999999)}"
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number

    def get_total_items(self):
        """Get total number of items in order"""
        return sum(item.quantity for item in self.items.all())

    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']

    def cancel_order(self):
        """Cancel order and restore stock"""
        if self.can_cancel():
            # Restore stock for all items
            for item in self.items.all():
                item.product.increase_stock(item.quantity)
            
            self.status = 'cancelled'
            self.save()
            return True
        return False

    def mark_as_shipped(self):
        """Mark order as shipped"""
        from django.utils import timezone
        self.status = 'shipped'
        self.shipped_at = timezone.now()
        self.save()

    @classmethod
    def create_from_cart(cls, cart, address, shipping_cost=0):
        """Create order from cart"""
        if not cart.items.exists():
            return None

        # Calculate totals
        subtotal = cart.get_total_price()
        total_amount = subtotal + shipping_cost

        # Create order
        order = cls.objects.create(
            user=cart.user,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            total_amount=total_amount,
            address=address
        )

        # Create order items and reduce stock
        for cart_item in cart.items.all():
            if cart_item.product.can_order(cart_item.quantity):
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    size=cart_item.size,
                    color=cart_item.color
                )
                cart_item.product.reduce_stock(cart_item.quantity)
            else:
                # If any item can't be ordered, delete the order
                order.delete()
                return None

        # Clear cart after successful order
        cart.clear_cart()
        return order


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.product.name}(size: {self.size}, color: {self.color}) x {self.quantity}"

    def get_total_price(self):
        """Calculate total price for this order item"""
        return self.product.price * self.quantity

