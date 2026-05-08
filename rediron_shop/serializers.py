# serializers.py

from rest_framework import serializers
from .models import (
    Category, Product, ProductVariant, ProductReview, ProductImage,
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

# ---------- Product Section ----------

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'caption', 'display_order']

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        request = self.context.get('request', None)
        if obj.image and hasattr(obj.image, 'url'):
            return self._absolute_url(request, obj.image.url)
        return None

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'

class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source='category'
    )
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_id', 'name', 'slug', 'description',
            'image', 'mrp', 'price', 'discount_percent', 'rating', 'is_active', 'date_added',
            'variants', 'reviews', 'gallery_images',
            # New equipment detail fields
            'video_url', 'key_features', 'specifications', 'benefits', 
            'perfect_for', 'additional_stats'
        ]

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        request = self.context.get('request', None)
        if obj.image and hasattr(obj.image, 'url'):
            return self._absolute_url(request, obj.image.url)
        return None

# ---------- Cart, Orders, Coupon, Reward ----------

class CartItemSerializer(serializers.ModelSerializer):
    product_variant = ProductVariantSerializer(read_only=True)
    product_variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), write_only=True, source='product_variant'
    )

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product_variant', 'product_variant_id', 'quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'created_at', 'updated_at', 'items']

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class RewardPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardPoint
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    cart = CartSerializer(read_only=True)
    cart_id = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(), write_only=True, source='cart'
    )
    coupon = CouponSerializer(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(
        queryset=Coupon.objects.all(), write_only=True, source='coupon', allow_null=True, required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'cart', 'cart_id', 'name', 'mobile', 'email', 'shipping_address',
            'coupon', 'coupon_id', 'reward_points_used', 'status', 'placed_at'
        ]

# ---------- Blog ----------

class BlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = '__all__'

# ---------- Dealer ----------

class DealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealer
        fields = '__all__'

# ---------- Business Inquiry ----------

class BusinessInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessInquiry
        fields = '__all__'

# ---------- FAQ ----------

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'

# ---------- Contact ----------

class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = '__all__'

# ---------- Newsletter ----------

class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscription
        fields = '__all__'

# ---------- Static Pages ----------

class PrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = Privacy
        fields = '__all__'

class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terms
        fields = '__all__'

class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = '__all__'

class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = About
        fields = '__all__'

# ---------- Subcategory ----------

class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = '__all__'

# ---------- Brand ----------

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

# ---------- Offer ----------

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = '__all__'

# ---------- OrderItem ----------

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

# ---------- PaymentMethod ----------

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'

# ---------- PaymentIntent ----------

class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = '__all__'

# ---------- PaymentLog ----------

class PaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = '__all__'

# ---------- Subscription ----------

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'

# ---------- UserActivityData ----------

class UserActivityDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityData
        fields = '__all__'

# ---------- UserAddress ----------

class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = '__all__'

# ---------- UserReview ----------

class UserReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReview
        fields = '__all__'

# ---------- Wishlist ----------

class WishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = '__all__'

# ---------- WishlistItem ----------

class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = '__all__'

# ---------- UserProfile ----------

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
