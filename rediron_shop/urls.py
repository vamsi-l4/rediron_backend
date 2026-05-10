from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('shop-categories', views.CategoryViewSet, basename='shop-categories')
router.register('shop-products', views.ProductViewSet, basename='shop-products')
router.register('shop-variants', views.ProductVariantViewSet, basename='shop-variants')
router.register('shop-reviews', views.ProductReviewViewSet, basename='shop-reviews')
router.register('shop-product-images', views.ProductImageViewSet, basename='shop-product-images')
router.register('shop-carts', views.CartViewSet, basename='shop-carts')
router.register('shop-cartitems', views.CartItemViewSet, basename='shop-cartitems')
router.register('shop-coupons', views.CouponViewSet, basename='shop-coupons')
router.register('shop-rewards', views.RewardPointViewSet, basename='shop-rewards')
router.register('shop-orders', views.OrderViewSet, basename='shop-orders')
router.register('shop-blogs', views.BlogPostViewSet, basename='shop-blogs')
router.register('shop-dealers', views.DealerViewSet, basename='shop-dealers')
router.register('shop-business-inquiries', views.BusinessInquiryViewSet, basename='shop-business-inquiries')
router.register('shop-faqs', views.FAQViewSet, basename='shop-faqs')
router.register('shop-contacts', views.ContactUsViewSet, basename='shop-contacts')
router.register('shop-newsletter', views.NewsletterSubscriptionViewSet, basename='shop-newsletter')
router.register('shop-subcategories', views.SubcategoryViewSet, basename='shop-subcategories')
router.register('shop-brands', views.BrandViewSet, basename='shop-brands')
router.register('shop-offers', views.OfferViewSet, basename='shop-offers')
router.register('shop-orderitems', views.OrderItemViewSet, basename='shop-orderitems')
router.register('shop-paymentmethods', views.PaymentMethodViewSet, basename='shop-paymentmethods')
router.register('shop-paymentintents', views.PaymentIntentViewSet, basename='shop-paymentintents')
router.register('shop-paymentlogs', views.PaymentLogViewSet, basename='shop-paymentlogs')
router.register('shop-subscriptions', views.SubscriptionViewSet, basename='shop-subscriptions')
router.register('shop-useractivitydata', views.UserActivityDataViewSet, basename='shop-useractivitydata')
router.register('shop-useraddresses', views.UserAddressViewSet, basename='shop-useraddresses')
router.register('shop-userreviews', views.UserReviewViewSet, basename='shop-userreviews')
router.register('shop-wishlists', views.WishlistViewSet, basename='shop-wishlists')
router.register('shop-wishlistitems', views.WishlistItemViewSet, basename='shop-wishlistitems')
router.register('shop-userprofiles', views.UserProfileViewSet, basename='shop-userprofiles')
router.register('shop-privacy', views.PrivacyViewSet, basename='shop-privacy')
router.register('shop-terms', views.TermsViewSet, basename='shop-terms')
router.register('shop-refund', views.RefundViewSet, basename='shop-refund')
router.register('shop-about', views.AboutViewSet, basename='shop-about')

urlpatterns = [
    path('', include(router.urls)),
]