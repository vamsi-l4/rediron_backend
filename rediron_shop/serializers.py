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
    product_variant = serializers.SerializerMethodField()
    product_variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), write_only=True, source='product_variant', required=False, allow_null=True
    )
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, source='product', required=False, allow_null=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product_variant', 'product_variant_id', 'product', 'product_id', 'quantity']

    def to_internal_value(self, data):
        mutable = data.copy()
        if 'cart_id' in mutable and 'cart' not in mutable:
            mutable['cart'] = mutable.get('cart_id')
        if 'product' in mutable and 'product_id' not in mutable:
            mutable['product_id'] = mutable.get('product')
        if 'product_variant' in mutable and 'product_variant_id' not in mutable:
            mutable['product_variant_id'] = mutable.get('product_variant')
        return super().to_internal_value(mutable)

    def validate(self, attrs):
        if not attrs.get('product') and not attrs.get('product_variant'):
            raise serializers.ValidationError("Either product_id or product_variant_id is required.")
        if attrs.get('product_variant') and not attrs.get('product'):
            attrs['product'] = attrs['product_variant'].product
        if attrs.get('cart') and self.context.get('request'):
            request = self.context.get('request')
            if request.user and request.user.is_authenticated and attrs['cart'].user_id and attrs['cart'].user_id != request.user.id:
                raise serializers.ValidationError("Cart does not belong to the current user.")
        return attrs

    def create(self, validated_data):
        cart = validated_data["cart"]
        product = validated_data.get("product")
        product_variant = validated_data.get("product_variant")
        quantity = validated_data.get("quantity") or 1

        existing = CartItem.objects.filter(
            cart=cart,
            product=product,
            product_variant=product_variant,
        ).first()
        if existing:
            existing.quantity += quantity
            existing.save(update_fields=["quantity"])
            return existing

        return super().create(validated_data)

    def get_product_variant(self, obj):
        if obj.product_variant:
            return ProductVariantSerializer(obj.product_variant, context=self.context).data
        if obj.product:
            product_data = ProductSerializer(obj.product, context=self.context).data
            return {
                'id': None,
                'variant_name': '',
                'price': obj.product.price,
                'inventory': 9999,
                'in_stock': obj.product.is_active,
                'product': product_data,
                'image': obj.product.image.url if obj.product.image else None,
            }
        return None

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

class OrderItemSerializer(serializers.ModelSerializer):
    product_variant = ProductVariantSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product_variant', 'product', 'product_name', 'product_image', 'quantity', 'price']

    def get_product_name(self, obj):
        if obj.product_variant:
            if hasattr(obj.product_variant, 'product') and obj.product_variant.product:
                return obj.product_variant.product.name
            return getattr(obj.product_variant, 'variant_name', None)
        if obj.product:
            return obj.product.name
        return None

    def get_product_image(self, obj):
        request = self.context.get('request')
        image_url = None
        if obj.product_variant and hasattr(obj.product_variant, 'product') and obj.product_variant.product:
            product = obj.product_variant.product
            if getattr(product, 'image', None) and hasattr(product.image, 'url'):
                image_url = product.image.url
        elif obj.product and hasattr(obj.product, 'image') and obj.product.image:
            image_url = obj.product.image.url
        if image_url and request:
            return request.build_absolute_uri(image_url)
        return image_url

class OrderSerializer(serializers.ModelSerializer):
    cart = CartSerializer(read_only=True)
    cart_id = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(), write_only=True, source='cart'
    )
    order_items = OrderItemSerializer(source='items', many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
    coupon = CouponSerializer(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(
        queryset=Coupon.objects.all(), write_only=True, source='coupon', allow_null=True, required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'cart', 'cart_id', 'name', 'mobile', 'email', 'shipping_address',
            'coupon', 'coupon_id', 'reward_points_used', 'status', 'placed_at',
            'total_amount', 'grand_total', 'order_items', 'items'
        ]

    def get_total_amount(self, obj):
        return sum(item.price * item.quantity for item in obj.items.all())

    def get_grand_total(self, obj):
        total = self.get_total_amount(obj)
        if obj.coupon and obj.coupon.discount_percent:
            total = total - ((total * obj.coupon.discount_percent) / 100)
        return max(total, 0)

    def create(self, validated_data):
        cart = validated_data.get('cart')
        order = Order.objects.create(**validated_data)
        if cart is not None:
            for cart_item in cart.items.all():
                price = cart_item.product_variant.price if cart_item.product_variant else (cart_item.product.price if cart_item.product else 0)
                OrderItem.objects.create(
                    order=order,
                    product_variant=cart_item.product_variant,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=price,
                )
        return order

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
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, source='product', required=False
    )

    class Meta:
        model = WishlistItem
        fields = ['id', 'wishlist', 'product', 'product_id', 'added_at']

    def to_internal_value(self, data):
        mutable = data.copy()
        if 'product' in mutable and 'product_id' not in mutable:
            mutable['product_id'] = mutable.get('product')
        return super().to_internal_value(mutable)

    def validate(self, attrs):
        wishlist = attrs.get('wishlist')
        product = attrs.get('product')
        request = self.context.get('request')

        if not product:
            raise serializers.ValidationError("product_id is required.")
        if request and request.user and request.user.is_authenticated and wishlist and wishlist.user_id and wishlist.user_id != request.user.id:
            raise serializers.ValidationError("Wishlist does not belong to the current user.")
        return attrs

    def create(self, validated_data):
        item, _ = WishlistItem.objects.get_or_create(
            wishlist=validated_data["wishlist"],
            product=validated_data["product"],
        )
        return item

# ---------- UserProfile ----------

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
