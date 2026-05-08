from django.urls import path
from . import views
from . import trial_views

urlpatterns = [
    # ====== PAYMENT ENDPOINTS ======
    path('razorpay-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('verify-razorpay-payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    
    # ====== TRIAL SUBSCRIPTION ENDPOINTS ======
    path('trial-status/', trial_views.get_trial_status, name='get_trial_status'),
    path('start-trial/', trial_views.start_trial, name='start_trial'),
    path('upgrade-trial/', trial_views.upgrade_trial, name='upgrade_trial'),
    path('payment-transaction/', trial_views.create_payment_transaction, name='create_payment_transaction'),
    path('payment-history/', trial_views.get_payment_history, name='get_payment_history'),

    # ====== AUTH ENDPOINTS ======
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('login/', views.custom_login, name='custom_login'),
    path('test/', views.test_view, name='test'),
    path('refresh/', views.refresh_token, name='refresh_token'),
    path('logout/', views.logout, name='logout'),

    # ====== USER ENDPOINTS (LEGACY) ======
    path('profile/', views.user_profile, name='user-profile'),
    path('profile/create/', views.create_profile, name='create-profile'),
    path('profile/update/', views.update_profile, name='update-profile'),
    path('sync-after-signup/', views.sync_user_after_signup, name='sync-after-signup'),
    path('activity/', views.user_activity_data, name='user-activity-data'),
    path('user/payment-option/', views.set_payment_option, name='set_payment_option'),
    path('welcome/', views.welcome, name='welcome'),
    
    # ====== PRODUCTION-GRADE PROFILE ENDPOINTS (NEW) ======
    # Clerk user profile initialization (CALLED AFTER CLERK LOGIN)
    path('initialize-profile/', views.initialize_user_profile, name='initialize-profile'),
    
    # Comprehensive profile
    path('profile-extended/', views.get_extended_profile, name='get-extended-profile'),
    path('profile-manage/', views.manage_profile, name='manage-profile'),
    
    # Address management
    path('addresses/', views.manage_addresses, name='list-create-addresses'),
    path('addresses/<int:address_id>/', views.manage_address_detail, name='get-update-delete-address'),
    
    # Fitness progress
    path('fitness-progress/', views.get_fitness_progress, name='get-fitness-progress'),
    path('fitness-progress/add/', views.add_fitness_progress, name='add-fitness-progress'),
    
    # Saved items
    path('saved-items/', views.manage_saved_items, name='get-save-items'),
    path('saved-items/<int:item_id>/', views.remove_saved_item, name='remove-saved-item'),
    
    # Payments
    path('payment-history/', views.get_payment_history, name='get-payment-history'),
    
    # Subscription
    path('gym-subscription/', views.get_gym_subscription, name='get-gym-subscription'),
]