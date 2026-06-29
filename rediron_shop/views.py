# views.py
from rest_framework.response import Response
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from django.conf import settings
from django.core.mail import send_mail
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count, Q
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
    queryset = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('name')
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['slug']
    search_fields = ['name', 'slug']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'subcategory', 'brand').prefetch_related(
        'variants', 'reviews', 'gallery_images'
    ).all().order_by('-date_added')
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'brand__name', 'sku']
    ordering_fields = ['price', 'mrp', 'discount_percent', 'rating', 'date_added', 'stock']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        catalog = params.get('catalog') or params.get('product_catalog')
        if catalog in ['shop', 'ecommerce', 'retail']:
            queryset = queryset.filter(is_active=True)

        category = params.get('category')
        if category:
            if str(category).isdigit():
                queryset = queryset.filter(category_id=category)
            else:
                queryset = queryset.filter(category__slug=category)

        subcategory = params.get('subcategory')
        if subcategory:
            if str(subcategory).isdigit():
                queryset = queryset.filter(subcategory_id=subcategory)
            else:
                queryset = queryset.filter(subcategory__slug=subcategory)

        brand = params.get('brand')
        if brand:
            if str(brand).isdigit():
                queryset = queryset.filter(brand_id=brand)
            else:
                queryset = queryset.filter(brand__slug=brand)

        product_type = params.get('product_type')
        if product_type:
            queryset = queryset.filter(product_type=product_type)

        is_active = params.get('is_active')
        if is_active is not None:
            active = str(is_active).lower() in ['1', 'true', 'yes']
            queryset = queryset.filter(is_active=active)

        min_price = params.get('min_price') or params.get('price_min') or params.get('price__gte')
        max_price = params.get('max_price') or params.get('price_max') or params.get('price__lte')
        min_rating = params.get('rating') or params.get('min_rating') or params.get('rating__gte')
        min_discount = params.get('discount') or params.get('discount_percent__gte')
        stock = params.get('stock') or params.get('in_stock')
        tags = params.get('tags') or params.get('tag')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        if min_discount:
            queryset = queryset.filter(discount_percent__gte=min_discount)
        if stock:
            truthy = str(stock).lower() in ['1', 'true', 'yes', 'available', 'in_stock']
            queryset = queryset.filter(stock__gt=0) if truthy else queryset.filter(stock=0)
        if tags:
            for tag in [part.strip() for part in str(tags).split(',') if part.strip()]:
                queryset = queryset.filter(tags__icontains=tag)

        sort_aliases = {
            'newest': '-date_added',
            'latest': '-date_added',
            'price_low': 'price',
            'price_high': '-price',
            'top_rated': '-rating',
            'popular': '-rating',
            'discount': '-discount_percent',
        }
        sort = params.get('sort')
        if sort in sort_aliases and 'ordering' not in params:
            queryset = queryset.order_by(sort_aliases[sort])

        return queryset.distinct()

    def _active_products(self):
        return self.filter_queryset(self.get_queryset().filter(is_active=True))

    def _paginated_response(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        queryset = self._active_products().order_by('-rating', '-discount_percent', '-date_added')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        queryset = self._active_products().order_by('-date_added')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='top-rated')
    def top_rated(self, request):
        queryset = self._active_products().order_by('-rating', '-date_added')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='discounts')
    def discounts(self, request):
        queryset = self._active_products().filter(discount_percent__gt=0).order_by('-discount_percent', '-rating')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='recommended')
    def recommended(self, request):
        queryset = self._active_products().filter(Q(rating__gte=4) | Q(discount_percent__gte=20)).order_by('-rating', '-stock')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='category/(?P<slug>[^/.]+)')
    def category_products(self, request, slug=None):
        queryset = self._active_products().filter(category__slug=slug).order_by('-rating', '-date_added')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='subcategory/(?P<slug>[^/.]+)')
    def subcategory_products(self, request, slug=None):
        queryset = self._active_products().filter(subcategory__slug=slug).order_by('-rating', '-date_added')
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path='search')
    def search_products(self, request):
        term = request.query_params.get('q') or request.query_params.get('search') or ''
        queryset = self._active_products()
        if term:
            queryset = queryset.filter(
                Q(name__icontains=term) |
                Q(description__icontains=term) |
                Q(category__name__icontains=term) |
                Q(subcategory__name__icontains=term) |
                Q(brand__name__icontains=term) |
                Q(tags__icontains=term)
            )
        return self._paginated_response(queryset.order_by('-rating', '-date_added'))

    @action(detail=True, methods=['get'], url_path='related')
    def related(self, request, pk=None):
        product = self.get_object()
        queryset = Product.objects.select_related('category', 'subcategory', 'brand').filter(
            is_active=True
        ).exclude(pk=product.pk).filter(
            Q(category=product.category) |
            Q(subcategory=product.subcategory) |
            Q(brand=product.brand)
        ).order_by('-rating', '-date_added')
        serializer = self.get_serializer(queryset[:8], many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=['post'], url_path='add')
    def add(self, request):
        product_id = request.data.get('product_id') or request.data.get('product')
        variant_id = request.data.get('product_variant_id') or request.data.get('product_variant')
        quantity = int(request.data.get('quantity') or 1)

        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)

        product = None
        product_variant = None
        if variant_id:
            try:
                product_variant = ProductVariant.objects.select_related('product').get(id=variant_id)
                product = product_variant.product
            except ProductVariant.DoesNotExist:
                return Response({'error': 'Product variant not found.'}, status=status.HTTP_404_NOT_FOUND)
        elif product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if product_variant:
            if not product_variant.in_stock:
                return Response({'error': 'Selected variant is out of stock.'}, status=status.HTTP_400_BAD_REQUEST)
            if quantity > product_variant.inventory:
                return Response({'error': 'Insufficient inventory.', 'available': product_variant.inventory}, status=status.HTTP_400_BAD_REQUEST)
        elif not product.is_active:
            return Response({'error': 'Product is not active.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user and request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
        else:
            cart_id = request.data.get('cart_id') or request.data.get('cart')
            cart = Cart.objects.filter(id=cart_id, user__isnull=True).first() if cart_id else None
            if not cart:
                cart = Cart.objects.create()

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            product_variant=product_variant,
            defaults={'quantity': quantity},
        )
        if not created:
            new_quantity = item.quantity + quantity
            if product_variant and new_quantity > product_variant.inventory:
                return Response({'error': 'Insufficient inventory.', 'available': product_variant.inventory}, status=status.HTTP_400_BAD_REQUEST)
            item.quantity = new_quantity
            item.save(update_fields=['quantity'])

        return Response({
            'cart': CartSerializer(cart, context={'request': request}).data,
            'item': CartItemSerializer(item, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create order from cart with inventory validation.
        """
        cart_id = request.data.get('cart_id')
        if not cart_id:
            return Response({'error': 'cart_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.select_for_update().get(id=cart_id)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.user and request.user.is_authenticated and cart.user_id and cart.user_id != request.user.id:
            return Response({'error': 'Cart does not belong to the current user'}, status=status.HTTP_403_FORBIDDEN)

        cart_items = list(cart.items.select_related('product', 'product_variant__product').all())
        if not cart_items:
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        out_of_stock_items = []
        for cart_item in cart_items:
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
            elif cart_item.product and not cart_item.product.is_active:
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

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user and request.user.is_authenticated:
            serializer.validated_data['user'] = request.user

        order = serializer.save()

        for cart_item in cart_items:
            if cart_item.product_variant:
                variant = cart_item.product_variant
                variant.inventory -= cart_item.quantity
                variant.save(update_fields=['inventory'])

        cart.items.all().delete()

        transaction.on_commit(lambda: self.send_order_confirmation(order))

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

    @action(detail=True, methods=['post'], url_path='cancel')
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = self.get_queryset().select_for_update().filter(pk=pk).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.status in ['Shipped', 'Delivered', 'Cancelled']:
            return Response(
                {'error': f'Orders with status {order.status} cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'Cancelled'
        order.save(update_fields=['status', 'updated_at'])

        for item in order.items.select_related('product_variant').all():
            if item.product_variant:
                item.product_variant.inventory += item.quantity
                item.product_variant.save(update_fields=['inventory'])

        transaction.on_commit(lambda: self.send_order_cancellation(order))
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def send_order_cancellation(self, order):
        recipient = order.email or (order.user.email if order.user else "")
        if not recipient:
            return

        subject = f"RedIron order #{order.id} cancelled"
        message = (
            f"Hi {order.name},\n\n"
            f"Your RedIron order #{order.id} has been cancelled.\n\n"
            "If payment was already captured, our support team will process the eligible refund as per the return and refund policy.\n\n"
            "Need help? Contact support@rediron.com with your order ID.\n\n"
            "Team RedIron"
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
    queryset = Subcategory.objects.select_related('category').annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('name')
    serializer_class = SubcategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'category__slug', 'slug']
    search_fields = ['name']

# ---------- Brand ----------

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('name')
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
            queryset = WishlistItem.objects.filter(wishlist__user=self.request.user).order_by('-added_at')
            product = self.request.query_params.get('product') or self.request.query_params.get('product_id')
            wishlist = self.request.query_params.get('wishlist')
            if product:
                queryset = queryset.filter(product_id=product)
            if wishlist:
                queryset = queryset.filter(wishlist_id=wishlist)
            return queryset
        return WishlistItem.objects.none()

    @action(detail=False, methods=['post'], url_path='add')
    def add(self, request):
        if not (request.user and request.user.is_authenticated):
            return Response({'error': 'Authentication is required for wishlist.'}, status=status.HTTP_403_FORBIDDEN)

        product_id = request.data.get('product_id') or request.data.get('product')
        if not product_id:
            return Response({'error': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        return Response({
            'wishlist': wishlist.id,
            'item': WishlistItemSerializer(item, context={'request': request}).data,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

# ---------- UserProfile ----------

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all().order_by('user__email')
    serializer_class = UserProfileSerializer
