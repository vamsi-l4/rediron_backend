# models.py

from django.db import models
from django.utils import timezone
import json

# ---------- Product & Category Section ----------

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):  
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)
    
    # ===== NEW: Equipment Details Fields =====
    video_url = models.URLField(blank=True, null=True, help_text="YouTube video URL for equipment")
    
    # JSON fields for structured data
    key_features = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of key features with icons. E.g., [{'title': 'Feature 1', 'description': 'Desc', 'icon': 'heart'}]"
    )
    
    specifications = models.JSONField(
        default=list,
        blank=True,
        help_text="Equipment specifications. E.g., [{'label': 'Motor Power', 'value': '4.0 HP'}, ...]"
    )
    
    benefits = models.JSONField(
        default=list,
        blank=True,
        help_text="List of benefits/advantages. E.g., [{'title': 'Benefit 1', 'description': 'Desc'}]"
    )
    
    perfect_for = models.JSONField(
        default=list,
        blank=True,
        help_text="Use cases. E.g., [{'label': 'Weight Loss', 'icon': 'target'}, ...]"
    )
    
    # Optional: Additional stats beyond rating
    additional_stats = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional stat cards. E.g., [{'label': 'Max Weight', 'value': '150 KG', 'icon': 'weight'}]"
    )

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    variant_name = models.CharField(max_length=100) # e.g. '2.2 lb - Double Rich Chocolate'
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    in_stock = models.BooleanField(default=True)
    inventory = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.product.name} - {self.variant_name}"


class ProductImage(models.Model):
    """Gallery images for product detail page"""
    product = models.ForeignKey(Product, related_name='gallery_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['display_order']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.display_order}"


# ---------- Reviews & Ratings ----------

class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    reviewer_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# ---------- Cart & Order Management ----------
# ============================================
# UPDATED FOR CLERK AUTHENTICATION
# All models now link to CustomUser (which has clerk_user_id)
# UserProfile can be accessed via user.profile
# ============================================

class Cart(models.Model):
    """
    Shopping cart per user, linked via CustomUser FK.
    The user's UserProfile contains all user-related data.
    """
    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='cart',
        help_text="Link to CustomUser with clerk_user_id",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.email}"

class CartItem(models.Model):
    """Cart items linked to a cart"""
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        try:
            name = self.product_variant.variant_name if self.product_variant else self.product.name
            user_email = self.cart.user.email if self.cart.user else "Guest"
            return f"{user_email} - {name} x{self.quantity}"
        except:
            return f"CartItem {self.id}"

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=120)
    discount_percent = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

class RewardPoint(models.Model):
    name = models.CharField(max_length=120)   # For identification, if not linked to user
    points = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

ORDER_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Processing', 'Processing'),
    ('Shipped', 'Shipped'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled')
]

class Order(models.Model):
    """
    Production-grade Order model linked to CustomUser (Clerk authenticated user).
    All user data filtering is done via user.clerk_user_id.
    """
    # Link to authenticated user via Clerk
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="Clerk authenticated user who placed the order",
        null=True,
        blank=True
    )
    
    # Order details
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='Pending',
        db_index=True
    )
    
    # Shipping & Contact
    name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=15)
    email = models.EmailField()
    shipping_address = models.TextField()
    
    # Coupon & Rewards
    coupon = models.ForeignKey(Coupon, blank=True, null=True, on_delete=models.SET_NULL)
    reward_points_used = models.PositiveIntegerField(default=0)
    
    # Timestamps
    placed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-placed_at']
        indexes = [
            models.Index(fields=['user', '-placed_at']),
        ]
    
    def __str__(self):
        return f"Order {self.id} - {self.user.email} ({self.status})"

# ---------- Blog Section ----------

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    image = models.ImageField(upload_to='blogs/', blank=True)
    author = models.CharField(max_length=120)
    tags = models.CharField(max_length=200, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# ---------- Dealer/Partner Directory ----------

class Dealer(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

# ---------- Business Inquiry ----------

class BusinessInquiry(models.Model):
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=80)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    details = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

# ---------- FAQ Section ----------

class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=100, blank=True)

# ---------- Contact/Support ----------

class ContactUs(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=120)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

# ---------- Newsletter ----------

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

# ---------- Static Pages ----------

class Privacy(models.Model):
    title = models.CharField(max_length=200, default="Privacy Policy")
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Terms(models.Model):
    title = models.CharField(max_length=200, default="Terms & Conditions")
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Refund(models.Model):
    title = models.CharField(max_length=200, default="Return & Refund Policy")
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class About(models.Model):
    title = models.CharField(max_length=200, default="About Us")
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# ---------- Subcategory ----------

class Subcategory(models.Model):
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='subcategories/', blank=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

# ---------- Brand ----------

class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name

# ---------- Offer ----------

class Offer(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    discount_percent = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    applicable_products = models.ManyToManyField(Product, blank=True)

    def __str__(self):
        return self.title

# ---------- OrderItem ----------

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order

    def __str__(self):
        name = self.product_variant.variant_name if self.product_variant else (self.product.name if self.product else "Unknown")
        return f"{self.order.id} - {name}"

# ---------- PaymentMethod ----------

class PaymentMethod(models.Model):
    METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('cod', 'Cash on Delivery'),
        ('netbanking', 'Net Banking'),
    ]
    name = models.CharField(max_length=100)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# ---------- PaymentIntent ----------

class PaymentIntent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    order = models.ForeignKey(Order, related_name='payment_intents', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PaymentIntent {self.id} - {self.status}"

# ---------- PaymentLog ----------

class PaymentLog(models.Model):
    payment_intent = models.ForeignKey(PaymentIntent, related_name='logs', on_delete=models.CASCADE)
    event = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.id} - {self.event}"

# ---------- Subscription ----------

class Subscription(models.Model):
    """
    Production-grade Subscription model for gym/premium features.
    Linked to CustomUser (Clerk authenticated user) via ForeignKey.
    """
    PLAN_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='subscriptions',
        help_text="Clerk authenticated user",
        null=True,
        blank=True
    )
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        db_index=True
    )
    active = models.BooleanField(default=True, db_index=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['active', 'end_date']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan} ({'Active' if self.active else 'Inactive'})"

# ---------- UserActivityData ----------

class UserActivityData(models.Model):
    """Activity tracking per user, linked to Clerk authenticated user"""
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='shop_activity_data',
        null=True,
        blank=True
    )
    activity_type = models.CharField(max_length=100)
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.activity_type}"

# ---------- UserAddress ----------

class UserAddress(models.Model):
    """User addresses for OOdelivery and billing, linked to Clerk authenticated user"""
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='shop_addresses',
        null=True,
        blank=True
    )
    address_type = models.CharField(max_length=20, default='home')
    name = models.CharField(max_length=120)
    address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.address_type}"

# ---------- UserReview ----------

class UserReview(models.Model):
    """User product reviews, linked to Clerk authenticated user"""
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='shop_reviews',
        null=True,
        blank=True
    )
    product = models.ForeignKey(Product, related_name='user_reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"

# ---------- Wishlist ----------

class Wishlist(models.Model):
    """Wishlist per user, linked to Clerk authenticated user"""
    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='wishlist',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist - {self.user.email}"

# ---------- WishlistItem ----------

class WishlistItem(models.Model):
    """Items in user's wishlist"""
    wishlist = models.ForeignKey(Wishlist, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wishlist.user.email} - {self.product.name}"

# ============================================
# COMMENTED: UserProfile moved to accounts.models
# ============================================
# UserProfile was previously defined here, but is now centralized
# in accounts.models.UserProfile for all user data management.
# This model is kept commented for backward compatibility and migration reference.
#
# OLD IMPLEMENTATION (USE accounts.models.UserProfile INSTEAD):
"""
class UserProfile(models.Model):
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile - {self.user.email}"
"""
