# views.py
from rest_framework.response import Response
from rest_framework import viewsets, permissions, filters
from django.conf import settings
from django.core.mail import send_mail
from django_filters.rest_framework import DjangoFilterBackend
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
from .serializers import (
    CategorySerializer, ProductSerializer, ProductVariantSerializer, ProductReviewSerializer, ProductImageSerializer,
    CartSerializer, CartItemSerializer, CouponSerializer, RewardPointSerializer, OrderSerializer,
    BlogPostSerializer, DealerSerializer, BusinessInquirySerializer, FAQSerializer,
    ContactUsSerializer, NewsletterSubscriptionSerializer,
    PrivacySerializer, TermsSerializer, RefundSerializer, AboutSerializer,
    SubcategorySerializer, BrandSerializer, OfferSerializer,
    OrderItemSerializer, PaymentMethodSerializer, PaymentIntentSerializer, PaymentLogSerializer,
    SubscriptionSerializer, UserActivityDataSerializer, UserAddressSerializer, UserReviewSerializer,
    WishlistSerializer, WishlistItemSerializer, UserProfileSerializer
)

# --- Category & Product ---

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['slug']
    search_fields = ['name', 'slug']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-date_added')
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'category__slug', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['price', 'mrp', 'discount_percent', 'rating', 'date_added']

class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all().order_by('product__name')
    serializer_class = ProductVariantSerializer

class ProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.all().order_by('-created_at')
    serializer_class = ProductReviewSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['product__name', 'reviewer_name']

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all().order_by('product', 'display_order')
    serializer_class = ProductImageSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['product__name', 'caption']

# --- Cart, CartItem, Coupon, Reward, Order ---

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user).order_by('-created_at')
        return Cart.objects.filter(user__isnull=True).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(cart)
            return Response(serializer.data, status=201 if created else 200)
        return super().create(request, *args, **kwargs)

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return CartItem.objects.filter(cart__user=self.request.user).order_by('cart__id')
        return CartItem.objects.filter(cart__user__isnull=True).order_by('cart__id')

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by('code')
    serializer_class = CouponSerializer

class RewardPointViewSet(viewsets.ModelViewSet):
    queryset = RewardPoint.objects.all().order_by('-points')
    serializer_class = RewardPointSerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'mobile', 'email']
    ordering_fields = ['placed_at', 'status']

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return Order.objects.filter(user=self.request.user).order_by('-placed_at')
        return Order.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Create order from cart with inventory validation
        """
        from rest_framework.response import Response
        from rest_framework import status
        
        cart_id = request.data.get('cart_id')
        if not cart_id:
            return Response({'error': 'cart_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.user and request.user.is_authenticated and cart.user_id and cart.user_id != request.user.id:
            return Response({'error': 'Cart does not belong to the current user'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if cart has items
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate inventory for all items
        out_of_stock_items = []
        for cart_item in cart.items.all():
            if cart_item.product_variant:
                variant = cart_item.product_variant
                if not variant.in_stock:
                    out_of_stock_items.append({
                        'id': cart_item.id,
                        'name': variant.product.name,
                        'variant': variant.variant_name,
                        'reason': 'out_of_stock'
                    })
                elif cart_item.quantity > variant.inventory:
                    out_of_stock_items.append({
                        'id': cart_item.id,
                        'name': variant.product.name,
                        'variant': variant.variant_name,
                        'reason': 'insufficient_inventory',
                        'available': variant.inventory
                    })
            elif cart_item.product:
                if not cart_item.product.is_active:
                    out_of_stock_items.append({
                        'id': cart_item.id,
                        'name': cart_item.product.name,
                        'variant': 'N/A',
                        'reason': 'out_of_stock'
                    })
        
        if out_of_stock_items:
            return Response({
                'error': 'Some items are out of stock',
                'out_of_stock_items': out_of_stock_items
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the order using serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Add user if authenticated
        if request.user and request.user.is_authenticated:
            serializer.validated_data['user'] = request.user
        
        order = serializer.save()
        
        # Decrease inventory for each ordered item
        for cart_item in cart.items.all():
            if cart_item.product_variant:
                variant = cart_item.product_variant
                variant.inventory -= cart_item.quantity
                variant.save()
        
        # Clear cart items after successful order
        cart.items.all().delete()

        self.send_order_confirmation(order)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def send_order_confirmation(self, order):
        recipient = order.email or (order.user.email if order.user else "")
        if not recipient:
            return

        item_lines = []
        total = 0
        for item in order.items.all():
            name = item.product_variant.product.name if item.product_variant else (item.product.name if item.product else "Product")
            line_total = item.price * item.quantity
            total += line_total
            item_lines.append(f"- {name} x {item.quantity}: ₹{line_total}")

        subject = f"RedIron order #{order.id} confirmed"
        message = (
            f"Hi {order.name},\n\n"
            f"Your RedIron order #{order.id} has been placed successfully.\n\n"
            "Order items:\n"
            f"{chr(10).join(item_lines) if item_lines else '- Order items confirmed'}\n\n"
            f"Shipping address:\n{order.shipping_address}\n\n"
            f"Order total: ₹{total}\n"
            f"Status: {order.status}\n\n"
            "Thank you for shopping with RedIron."
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
        try:
            send_mail(subject, message, from_email, [recipient], fail_silently=True)
        except Exception:
            pass

# --- Blog & Dealer ---

class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all().order_by('-published_at')
    serializer_class = BlogPostSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'tags']
    ordering_fields = ['published_at']

class DealerViewSet(viewsets.ModelViewSet):
    queryset = Dealer.objects.all().order_by('state', 'city')
    serializer_class = DealerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'city', 'state', 'phone', 'email']
    ordering_fields = ['state', 'city']

# --- Business Inquiry, FAQ, Contact, Newsletter ---

class BusinessInquiryViewSet(viewsets.ModelViewSet):
    queryset = BusinessInquiry.objects.all().order_by('-submitted_at')
    serializer_class = BusinessInquirySerializer

class FAQViewSet(viewsets.ModelViewSet):
    queryset = FAQ.objects.all().order_by('question')
    serializer_class = FAQSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['question', 'category']

class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.all().order_by('-submitted_at')
    serializer_class = ContactUsSerializer

class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all().order_by('-subscribed_at')
    serializer_class = NewsletterSubscriptionSerializer

# ---------- Static Pages ----------

class PrivacyViewSet(viewsets.ModelViewSet):
    queryset = Privacy.objects.all()
    serializer_class = PrivacySerializer

class TermsViewSet(viewsets.ModelViewSet):
    queryset = Terms.objects.all()
    serializer_class = TermsSerializer

class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer

class AboutViewSet(viewsets.ModelViewSet):
    queryset = About.objects.all()
    serializer_class = AboutSerializer

# ---------- Subcategory ----------

class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all().order_by('name')
    serializer_class = SubcategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

# ---------- Brand ----------

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

# ---------- Offer ----------

class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.all().order_by('-valid_to')
    serializer_class = OfferSerializer

# ---------- OrderItem ----------

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all().order_by('order__id')
    serializer_class = OrderItemSerializer

# ---------- PaymentMethod ----------

class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all().order_by('name')
    serializer_class = PaymentMethodSerializer

# ---------- PaymentIntent ----------

class PaymentIntentViewSet(viewsets.ModelViewSet):
    queryset = PaymentIntent.objects.all().order_by('-created_at')
    serializer_class = PaymentIntentSerializer

# ---------- PaymentLog ----------

class PaymentLogViewSet(viewsets.ModelViewSet):
    queryset = PaymentLog.objects.all().order_by('-timestamp')
    serializer_class = PaymentLogSerializer

# ---------- Subscription ----------

class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all().order_by('-start_date')
    serializer_class = SubscriptionSerializer

# ---------- UserActivityData ----------

class UserActivityDataViewSet(viewsets.ModelViewSet):
    queryset = UserActivityData.objects.all().order_by('-timestamp')
    serializer_class = UserActivityDataSerializer

# ---------- UserAddress ----------

class UserAddressViewSet(viewsets.ModelViewSet):
    queryset = UserAddress.objects.all().order_by('user__email')
    serializer_class = UserAddressSerializer

# ---------- UserReview ----------

class UserReviewViewSet(viewsets.ModelViewSet):
    queryset = UserReview.objects.all().order_by('-created_at')
    serializer_class = UserReviewSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['product__name', 'user__email']

# ---------- Wishlist ----------

class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return Wishlist.objects.filter(user=self.request.user).order_by('-created_at')
        return Wishlist.objects.none()

    def create(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            wishlist, created = Wishlist.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(wishlist)
            return Response(serializer.data, status=201 if created else 200)
        return Response({'error': 'Authentication is required for wishlist.'}, status=403)

# ---------- WishlistItem ----------

class WishlistItemViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistItemSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return WishlistItem.objects.filter(wishlist__user=self.request.user).order_by('-added_at')
        return WishlistItem.objects.none()

# ---------- UserProfile ----------

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all().order_by('user__email')
    serializer_class = UserProfileSerializer
