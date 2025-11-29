from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category', kwargs={'slug': self.slug})


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    sku = models.CharField(max_length=50, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    on_sale = models.BooleanField(default=False)
    discount_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0-100). Only applicable when on_sale is True."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    def get_sale_price(self):
        """Calculate and return the sale price if product is on sale"""
        if self.on_sale and self.discount_percentage > 0:
            discount_amount = (self.price * self.discount_percentage) / 100
            return int(self.price - discount_amount)
        return self.price

    def get_savings_amount(self):
        """Calculate the amount saved if product is on sale"""
        if self.on_sale and self.discount_percentage > 0:
            return int((self.price * self.discount_percentage) / 100)
        return 0

    def is_in_stock(self):
        """Check if product is in stock"""
        return self.stock_quantity > 0

    def can_order(self, quantity=1):
        """Check if quantity can be ordered"""
        return self.is_active and self.stock_quantity >= quantity

    def get_primary_image_url(self):
        """Get primary product image URL"""
        return self.images.filter(is_primary=True).first().image.url
    
    def get_primary_image(self):
        """Get primary product image"""
        return self.images.filter(is_primary=True).first()


    def get_all_images(self):
        """Get all product images"""
        return self.images.all()

    def reduce_stock(self, quantity):
        """Reduce stock quantity"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save()
            return True
        return False

    def increase_stock(self, quantity):
        """Increase stock quantity"""
        self.stock_quantity += quantity
        self.save()


class Size(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.name}"


class Color(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='colors')
    name = models.CharField(max_length=50)
    hex_code = models.CharField(max_length=7, blank=True)

    class Meta:
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.name}"


class Image(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} - Image"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            Image.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

