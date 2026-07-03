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

CATEGORY_IMAGE_FALLBACKS = {
    "accessories": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=600&q=80",
    "cardio": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&q=80",
    "core": "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=600&q=80",
    "footwear": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
    "gym-wear": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=80",
    "healthy-foods": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=600&q=80",
    "proteins": "https://images.unsplash.com/photo-1612487529431-2da0571c87ef?w=600&q=80",
    "strength": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&q=80",
    "supplements": "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?w=600&q=80",
    "vitamins": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&q=80",
}

PRODUCT_IMAGE_FALLBACKS = {
    "nike-metcon-9-training-shoes-black-white": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=900&q=80",
    "adidas-ultraboost-5x-running-shoes-core-black": "https://images.unsplash.com/photo-1600185365926-3a2ce3cdb9eb?w=900&q=80",
    "nike-romaleos-4-weightlifting-shoes-black": "https://images.unsplash.com/photo-1543508282-6319a3e2621f?w=900&q=80",
    "nike-pegasus-41-running-shoes-wolf-grey": "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=900&q=80",
    "adidas-solarglide-6-running-shoes-signal-orange": "https://images.unsplash.com/photo-1605408499391-6368c628ef42?w=900&q=80",
    "adidas-adipower-iii-weightlifting-shoes-black": "https://images.unsplash.com/photo-1556906781-9a412961c28c?w=900&q=80",
    "nike-free-metcon-6-training-shoes-dark-teal": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=900&q=80",
    "nike-vomero-17-running-shoes-white-platinum": "https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=900&q=80",
    "myprotein-impact-whey-protein-chocolate-smooth": "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?w=900&q=80",
    "optimum-nutrition-gold-standard-100-whey-double-rich-chocolate": "https://images.unsplash.com/photo-1622484211148-b2f5a3e3d90b?w=900&q=80",
    "muscleblaze-biozyme-performance-whey-rich-chocolate": "https://images.unsplash.com/photo-1615485500834-bc10199bc727?w=900&q=80",
    "gnc-pro-performance-100-whey-vanilla": "https://images.unsplash.com/photo-1579722820308-d74e571900a9?w=900&q=80",
}

FOOTWEAR_KEYWORD_IMAGES = (
    ("ultraboost", "https://images.unsplash.com/photo-1600185365926-3a2ce3cdb9eb?w=900&q=80"),
    ("romaleos", "https://images.unsplash.com/photo-1543508282-6319a3e2621f?w=900&q=80"),
    ("pegasus", "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=900&q=80"),
    ("solarglide", "https://images.unsplash.com/photo-1605408499391-6368c628ef42?w=900&q=80"),
    ("adipower", "https://images.unsplash.com/photo-1556906781-9a412961c28c?w=900&q=80"),
    ("free metcon", "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=900&q=80"),
    ("vomero", "https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=900&q=80"),
    ("metcon", "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=900&q=80"),
)

class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = '__all__'

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        request = self.context.get('request', None)
        if obj.image_url:
            return obj.image_url
        if obj.image and hasattr(obj.image, 'path') and obj.image.storage.exists(obj.image.name):
            return self._absolute_url(request, obj.image.url)
        return CATEGORY_IMAGE_FALLBACKS.get(obj.slug)

    def get_product_count(self, obj):
        return getattr(obj, 'product_count', None) or obj.products.filter(is_active=True).count()

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

class SubcategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)

    class Meta:
        model = Subcategory
        fields = '__all__'

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        request = self.context.get('request', None)
        if obj.image_url:
            return obj.image_url
        if obj.image and hasattr(obj.image, 'url'):
            return self._absolute_url(request, obj.image.url)
        return None

    def get_product_count(self, obj):
        return getattr(obj, 'product_count', None) or obj.products.filter(is_active=True).count()

class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = '__all__'

    def get_product_count(self, obj):
        return getattr(obj, 'product_count', None) or obj.products.filter(is_active=True).count()

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source='category'
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(), write_only=True, source='subcategory', required=False, allow_null=True
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), write_only=True, source='brand', required=False, allow_null=True
    )
    image = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_id', 'subcategory', 'subcategory_id', 'brand', 'brand_id',
            'product_type', 'name', 'slug', 'description', 'short_description',
            'image', 'featured_image_url', 'mrp', 'price', 'discount_percent', 'rating',
            'stock', 'sku', 'tags', 'in_stock', 'is_active', 'date_added',
            'variants', 'reviews', 'gallery_images',
            # New equipment detail fields
            'video_url', 'key_features', 'specifications', 'benefits', 
            'perfect_for', 'additional_stats',
            # Ecommerce type-specific fields
            'nutrition', 'clothing', 'footwear', 'accessory'
        ]

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        request = self.context.get('request', None)
        if obj.slug in PRODUCT_IMAGE_FALLBACKS:
            return PRODUCT_IMAGE_FALLBACKS[obj.slug]
        if obj.product_type == "footwear":
            product_name = obj.name.lower()
            for keyword, image_url in FOOTWEAR_KEYWORD_IMAGES:
                if keyword in product_name:
                    return image_url
        if obj.featured_image_url:
            return obj.featured_image_url
        if obj.image and hasattr(obj.image, 'url'):
            return self._absolute_url(request, obj.image.url)
        return None

    def get_short_description(self, obj):
        if not obj.description:
            return ""
        text = " ".join(str(obj.description).split())
        return text if len(text) <= 150 else f"{text[:147].rstrip()}..."

    def get_in_stock(self, obj):
        return obj.is_active and (obj.stock > 0 or obj.variants.filter(in_stock=True, inventory__gt=0).exists())

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
        if self.instance is not None and self.partial:
            product = attrs.get('product', getattr(self.instance, 'product', None))
            product_variant = attrs.get('product_variant', getattr(self.instance, 'product_variant', None))
            attrs['product'] = product
            attrs['product_variant'] = product_variant
        if not attrs.get('product') and not attrs.get('product_variant'):
            raise serializers.ValidationError("Either product_id or product_variant_id is required.")
        quantity = attrs.get('quantity')
        if quantity is not None and quantity < 1:
            raise serializers.ValidationError({"quantity": "Quantity must be at least 1."})
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
        read_only_fields = ['order']

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
        product = obj.product_variant.product if obj.product_variant and obj.product_variant.product else obj.product
        if product:
            if product.slug in PRODUCT_IMAGE_FALLBACKS:
                return PRODUCT_IMAGE_FALLBACKS[product.slug]
            if product.product_type == "footwear":
                product_name = product.name.lower()
                for keyword, fallback in FOOTWEAR_KEYWORD_IMAGES:
                    if keyword in product_name:
                        return fallback
            if product.featured_image_url:
                return product.featured_image_url
            if getattr(product, 'image', None) and hasattr(product.image, 'url'):
                image_url = product.image.url
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
    order_number = serializers.SerializerMethodField()
    coupon = CouponSerializer(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(
        queryset=Coupon.objects.all(), write_only=True, source='coupon', allow_null=True, required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'cart', 'cart_id', 'name', 'mobile', 'email', 'shipping_address',
            'payment_method', 'cancellation_reason', 'cancellation_notes',
            'coupon', 'coupon_id', 'reward_points_used', 'status', 'placed_at',
            'total_amount', 'grand_total', 'order_number', 'order_items', 'items'
        ]

    def get_total_amount(self, obj):
        return sum(item.price * item.quantity for item in obj.items.all())

    def get_grand_total(self, obj):
        total = self.get_total_amount(obj)
        if obj.coupon and obj.coupon.discount_percent:
            total = total - ((total * obj.coupon.discount_percent) / 100)
        return max(total, 0)

    def get_order_number(self, obj):
        return f"RI-{obj.id:06d}"

    def create(self, validated_data):
        cart = validated_data.get('cart')
        order = Order.objects.create(**validated_data)
        if cart is not None:
            for cart_item in cart.items.all():
                price = cart_item.product_variant.price if cart_item.product_variant else (cart_item.product.price if cart_item.product else 0)
                product = cart_item.product_variant.product if cart_item.product_variant and not cart_item.product else cart_item.product
                OrderItem.objects.create(
                    order=order,
                    product_variant=cart_item.product_variant,
                    product=product,
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
    company = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    message = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = BusinessInquiry
        fields = ['id', 'name', 'country', 'mobile', 'email', 'details', 'submitted_at', 'company', 'phone', 'message']
        read_only_fields = ['id', 'submitted_at']
        extra_kwargs = {
            'country': {'required': False, 'allow_blank': True},
            'mobile': {'required': False, 'allow_blank': True},
            'details': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = attrs.pop('company', '')
        phone = attrs.pop('phone', '')
        message = attrs.pop('message', '')
        if company and not attrs.get('country'):
            attrs['country'] = company
        if phone and not attrs.get('mobile'):
            attrs['mobile'] = phone
        if message and not attrs.get('details'):
            attrs['details'] = message
        return attrs

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
