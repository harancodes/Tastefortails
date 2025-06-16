from django.db import models
from django.utils.safestring import mark_safe
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField
from django.utils.timezone import now
from decimal import Decimal, ROUND_HALF_UP


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    image = CloudinaryField('image')   
    is_active = models.BooleanField(default=True)
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    offer_percentage = models.PositiveIntegerField(default=0, help_text="Discount percentage for this category.")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['is_active'])]

    def category_image(self):
        return mark_safe('<img src="%s" width="50" height="50">' % (self.image.url))

    def __str__(self):
        return self.name
    

    def reapply_offers_to_variants(self):
        for product in self.products.all():
            for variant in product.variants.all():
                variant.save()


    def save(self, *args, **kwargs):
        offer_changed = False
        if self.pk:
            old_offer = Category.objects.get(pk=self.pk).offer_percentage
            offer_changed = old_offer != self.offer_percentage
        super().save(*args, **kwargs)
        if offer_changed:
            self.reapply_offers_to_variants()


class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    offer_percentage = models.PositiveIntegerField(default=0, help_text="Discount percentage for this brand.")
    image = CloudinaryField('image', default=True)
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name

    def reapply_offers_to_variants(self):
        for product in self.products.all():
            for variant in product.variants.all():
                variant.save()

    def save(self, *args, **kwargs):
        offer_changed = False
        if self.pk:
            old_offer = Brand.objects.get(pk=self.pk).offer_percentage
            offer_changed = old_offer != self.offer_percentage
        super().save(*args, **kwargs)
        if offer_changed:
            self.reapply_offers_to_variants()


class Products(models.Model):
    PRODUCT_TYPES = [
        ('dry', 'Dry'),
        ('wet', 'Wet'),
        ('gravy', 'Gravy'),
        ('milk_replacers', 'Milk Replacers'),
    ]

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    description = models.CharField(max_length=10000, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='dry')
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_listed = models.BooleanField(default=True)
    offer_percentage = models.PositiveIntegerField(default=0, help_text="Discount percentage for this product.")

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['is_active', 'slug'])]

    def thumbnail(self):
        img = self.images.filter(is_primary=True).first()
        return img.image.url if img else None
    
    def reapply_offers_to_variants(self):
        for variant in self.variants.all():
            variant.save()


    def save(self, *args, **kwargs):
        offer_changed = False
        if self.pk:
            old_offer = Products.objects.get(pk=self.pk).offer_percentage
            offer_changed = old_offer != self.offer_percentage
        if not self.slug or self.name_has_changed():
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        if offer_changed:
            self.reapply_offers_to_variants()


    def name_has_changed(self):
        if not self.pk:
            return True
        try:
            old_name = Products.objects.get(pk=self.pk).name
            return old_name != self.name
        except Products.DoesNotExist:
            return True

    def main_image(self):
        return self.images.filter(is_primary=True).first()

    def __str__(self):
        return self.name


class Variant(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='variants')
    weight = models.CharField(max_length=50)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    variant_price = models.DecimalField(max_digits=10, decimal_places=2)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['is_active'])]



    def apply_offer(self):
        original_price = Decimal(self.variant_price)

        product_offer = Decimal(self.product.offer_percentage or 0)
        category_offer = Decimal(getattr(self.product.category, 'offer_percentage', 0) or 0)
        brand_offer = Decimal(getattr(self.product.brand, 'offer_percentage', 0) or 0)

        best_offer = max(product_offer, category_offer, brand_offer)

        calculated_price = original_price
        if best_offer > 0:
            discount_amount = (best_offer / Decimal('100')) * original_price
            calculated_price = (original_price - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if self.sales_price != calculated_price:
            self.sales_price = calculated_price
            return True

        return False
    

    def save(self, *args, **kwargs):
        if self.apply_offer():
            super().save(*args, **kwargs)
    

    def get_discount_amount(self):
        if self.sales_price and self.variant_price and self.variant_price > self.sales_price:
            return round(float(self.variant_price) - float(self.sales_price), 2)
        return 0
    def get_discount_percentage(self):
        if self.sales_price and self.variant_price and self.variant_price > self.sales_price:
            discount = (float(self.variant_price) - float(self.sales_price)) / float(self.variant_price) * 100
            return round(discount)
        return 0 

    def __str__(self):
        return f"{self.product.name} - {self.weight}"


class ProductImage(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="images")
    image = CloudinaryField('image')
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-uploaded_at']
        indexes = [models.Index(fields=['is_primary', 'uploaded_at'])]

    def __str__(self):
        return f"Image of {self.product.name}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['created_at'])]

    def __str__(self):
        return f"Review by {self.user} on {self.product.name}"
