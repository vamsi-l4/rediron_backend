# admin.py

from django.contrib import admin
from .models import (
    Category, Product, ProductVariant, ProductReview,
    Cart, CartItem, Coupon, RewardPoint, Order,
    BlogPost, Dealer, BusinessInquiry, FAQ,
    ContactUs, NewsletterSubscription,
    Privacy, Terms, Refund, About,
    Subcategory, Brand, Offer,
    OrderItem, PaymentMethod, PaymentIntent, PaymentLog,
    Subscription, UserActivityData, UserAddress, UserReview,
    Wishlist, WishlistItem
)
from accounts.models import UserProfile

# ----- Product Section -----

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class ProductReviewInline(admin.StackedInline):
    model = ProductReview
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'mrp', 'discount_percent', 'rating', 'is_active', 'date_added')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description', 'category__name')
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductReviewInline]

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant_name', 'sku', 'price', 'in_stock', 'inventory')
    list_filter = ('product', 'in_stock')
    search_fields = ('product__name', 'variant_name', 'sku')

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'reviewer_name', 'rating', 'created_at')
    search_fields = ('product__name', 'reviewer_name')
    list_filter = ('product',)

# ----- Cart, Order, Coupon -----

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at')
    inlines = [CartItemInline]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product_variant', 'quantity')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'discount_percent', 'active', 'valid_from', 'valid_to')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')

@admin.register(RewardPoint)
class RewardPointAdmin(admin.ModelAdmin):
    list_display = ('name', 'points', 'last_updated')
    search_fields = ('name',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'mobile', 'email', 'shipping_address', 'status', 'placed_at')
    list_filter = ('status', 'placed_at')
    search_fields = ('name', 'mobile', 'email', 'shipping_address')

# ----- Blog & Dealer -----

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'slug')
    list_filter = ('published_at',)
    search_fields = ('title', 'content', 'tags')
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'city', 'state', 'phone', 'email', 'is_active')
    list_filter = ('state', 'is_active')
    search_fields = ('name', 'address', 'city', 'state', 'phone', 'email')

# ----- Inquiry, FAQ, Contact, Newsletter -----

@admin.register(BusinessInquiry)
class BusinessInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'mobile', 'email', 'submitted_at')
    search_fields = ('name', 'country', 'mobile', 'email')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category')
    search_fields = ('question', 'category')

@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'message', 'submitted_at')
    search_fields = ('name', 'email', 'subject', 'message')

@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)

# ---------- Static Pages ----------

@admin.register(Privacy)
class PrivacyAdmin(admin.ModelAdmin):
    list_display = ('title', 'updated_at')

@admin.register(Terms)
class TermsAdmin(admin.ModelAdmin):
    list_display = ('title', 'updated_at')

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('title', 'updated_at')

@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ('title', 'updated_at')

# ---------- Subcategory ----------

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')
    search_fields = ('name', 'category__name')
    prepopulated_fields = {"slug": ("name",)}

# ---------- Brand ----------

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'website')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}

# ---------- Offer ----------

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'discount_percent', 'active', 'valid_from', 'valid_to')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('title', 'description')

# ---------- OrderItem ----------

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_variant', 'quantity', 'price')
    search_fields = ('order__id', 'product_variant__variant_name')

# ---------- PaymentMethod ----------

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'method', 'is_active')
    list_filter = ('method', 'is_active')
    search_fields = ('name',)

# ---------- PaymentIntent ----------

@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__id', 'razorpay_order_id', 'razorpay_payment_id')

# ---------- PaymentLog ----------

@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('payment_intent', 'event', 'timestamp')
    search_fields = ('payment_intent__id', 'event')

# ---------- Subscription ----------

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'active', 'start_date', 'end_date')
    list_filter = ('plan', 'active', 'start_date', 'end_date')
    search_fields = ('user__email',)

# ---------- UserActivityData ----------

@admin.register(UserActivityData)
class UserActivityDataAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp')
    search_fields = ('user__email', 'activity_type')

# ---------- UserAddress ----------

@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_type', 'name', 'city', 'state', 'is_default')
    list_filter = ('address_type', 'is_default')
    search_fields = ('user__email', 'name', 'city', 'state')

# ---------- UserReview ----------

@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at')
    search_fields = ('user__email', 'product__name')

# ---------- Wishlist ----------

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__email',)

# ---------- WishlistItem ----------

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'added_at')
    search_fields = ('wishlist__user__email', 'product__name')

# ---------- UserProfile ----------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'gender', 'is_complete', 'created_at')
    search_fields = ('user__email', 'phone_number')
