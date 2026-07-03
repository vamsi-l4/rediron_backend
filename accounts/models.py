from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)

    # ============================================
    # CLERK AUTHENTICATION (NEW)
    # ============================================
    # Store Clerk's user ID for user identification
    clerk_user_id = models.CharField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True,
        db_index=True,
        help_text="Clerk user ID from Clerk authentication service"
    )

    # Track who registered the user (nullable)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_users'
    )

    # Payment option: True for auto payment, False for manual
    auto_payment = models.BooleanField(default=True)

    # ============================================
    # OTP FIELDS (COMMENTED OUT - Clerk handles email verification)
    # ============================================
    # Old OTP fields - kept for backward compatibility and interview proof
    # With Clerk, email verification is handled by Clerk's built-in system
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
    # COMMENTED: Old OTP logic explanation:
    # Previously, OTP was sent via email for verification on login/signup
    # Now, Clerk handles all email verification natively
    # These fields remain in the model for interview discussion and gradual migration

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email


# ============================================
# OLD REFRESH TOKEN MODEL (COMMENTED USAGE)
# ============================================
class RefreshToken(models.Model):
    """
    OLD MODEL: Used for custom JWT refresh token management.
    DEPRECATED: Clerk handles session management automatically.
    Kept in database for backward compatibility.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry = models.DateTimeField()

    def __str__(self):
        return f"{self.user.email} - {self.token[:8]}... (exp {self.expiry})"

    """
    # COMMENTED: Old refresh token flow
    # This model was used to manage JWT refresh tokens
    # With Clerk, session and token management are handled by Clerk's backend
    # API endpoints should verify Clerk tokens instead of using this model
    """


# ============================================
# OTP MODEL (COMMENTED OUT - Clerk handles verification)
# ============================================
class OTP(models.Model):
    """
    OLD MODEL: Used for OTP-based email verification.
    DEPRECATED: Clerk handles email verification natively.
    Kept in database for backward compatibility and interview proof.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - OTP: {self.code} - Verified: {self.is_verified}"

    """
    # COMMENTED: Old OTP flow
    # Previously generated OTP codes and sent them via email
    # Now Clerk handles the entire email verification process
    # This model remains for database consistency and interview discussion
    """


class UserActivityData(models.Model):
    """
    Stores per-user activity data (gym, shop, subscriptions, workouts, etc.)
    Now identified by clerk_user_id instead of Django user ID.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_data'
    )
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Activity Data for {self.user.email}"


class TrialSubscription(models.Model):
    """
    Manages free trial subscriptions for users.
    Tracks trial status, expiration, and available features.
    """
    TRIAL_STATUS_CHOICES = [
        ('active', 'Active Trial'),
        ('expired', 'Expired'),
        ('upgraded', 'Upgraded to Premium'),
        ('cancelled', 'Cancelled'),
    ]
    RENEWAL_PREFERENCE_CHOICES = [
        ('auto', 'Auto-renew after trial'),
        ('manual', 'Manual renewal only'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trial_subscription'
    )
    status = models.CharField(
        max_length=20,
        choices=TRIAL_STATUS_CHOICES,
        default='active'
    )
    trial_used = models.BooleanField(default=True)
    renewal_preference = models.CharField(
        max_length=20,
        choices=RENEWAL_PREFERENCE_CHOICES,
        default='manual'
    )
    subscription_status = models.CharField(max_length=20, default='trial_active', db_index=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    features = models.JSONField(
        default=list,
        help_text="List of features available during trial",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Trial Subscription"
        verbose_name_plural = "Trial Subscriptions"
        ordering = ['-created_at']
    
    def __str__(self):
        days_left = (self.end_date - __import__('django.utils.timezone', fromlist=['now']).now()).days
        return f"{self.user.email} - {self.status} ({days_left} days left)"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.end_date
    
    def days_remaining(self):
        from django.utils import timezone
        remaining = (self.end_date - timezone.now()).days
        return max(0, remaining)
    
    def mark_expired(self):
        """Mark trial as expired if past end date"""
        if self.is_expired() and self.status == 'active':
            self.status = 'expired'
            self.is_active = False
            self.subscription_status = 'trial_expired'
            self.save(update_fields=['status', 'is_active', 'subscription_status', 'updated_at'])


class PaymentTransaction(models.Model):
    """
    Records all payment transactions for audit trail and reporting.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('trial', 'Free Trial'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payment_transactions'
    )
    payment_id = models.CharField(max_length=255, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='razorpay'
    )
    plan = models.CharField(
        max_length=50,
        default='premium',
        help_text="Subscription plan purchased"
    )
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.payment_id} ({self.status})"


# ============================================
# PRODUCTION-GRADE PROFILE MODELS (NEW)
# ============================================
class UserProfile(models.Model):
    """
    Comprehensive user profile linked to Clerk authentication.
    Stores all user information separate from authentication credentials.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Personal Information
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="User's contact phone number"
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        blank=True
    )
    bio = models.TextField(blank=True, help_text="User bio/description")
    
    # Profile Metadata
    is_email_verified = models.BooleanField(default=True, help_text="Email verified via Clerk")
    profile_image = models.ImageField(
        upload_to='profiles/%Y/%m/',
        null=True,
        blank=True,
        help_text="User profile picture"
    )
    profile_image_data = models.TextField(
        blank=True,
        help_text="Permanent data URL copy of the current profile picture"
    )
    profile_image_mime = models.CharField(max_length=80, blank=True)
    is_complete = models.BooleanField(default=False, help_text="Profile completion status")
    
    # Fitness Information
    weight = models.FloatField(null=True, blank=True, help_text="Weight in kg")
    height = models.FloatField(null=True, blank=True, help_text="Height in cm")
    fitness_goal = models.CharField(
        max_length=50,
        choices=[
            ('weight_loss', 'Weight Loss'),
            ('muscle_gain', 'Muscle Gain'),
            ('endurance', 'Endurance'),
            ('flexibility', 'Flexibility'),
            ('maintenance', 'Maintenance'),
        ],
        blank=True
    )
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        blank=True
    )
    
    # Social & Preferences
    preferred_language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    receive_notifications = models.BooleanField(default=True)
    receive_emails = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Profile of {self.user.email}"
    
    def complete_percentage(self):
        """Calculate profile completion percentage"""
        fields = [
            self.phone_number,
            self.date_of_birth,
            self.gender,
            self.weight,
            self.height,
            self.fitness_goal,
        ]
        filled = sum(1 for field in fields if field)
        return int((filled / len(fields)) * 100)


class Address(models.Model):
    """
    User addresses for delivery and billing (ecommerce).
    """
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default='home'
    )
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    
    is_primary = models.BooleanField(default=False)
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.address_type} ({self.city})"
    
    def full_address(self):
        """Return formatted full address"""
        return f"{self.street_address}, {self.city}, {self.state} {self.postal_code}, {self.country}"


class GymSubscription(models.Model):
    """
    Active subscription for gym membership plans.
    """
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    PLAN_CHOICES = [
        ('basic', 'Basic - 1 Month'),
        ('standard', 'Standard - 3 Months'),
        ('premium', 'Premium - 12 Months'),
        ('family', 'Family Plan'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gym_subscription'
    )
    
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='active')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    
    auto_renewal = models.BooleanField(default=True)
    payment_method = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Gym Subscription"
        verbose_name_plural = "Gym Subscriptions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.plan} ({self.status})"
    
    def is_active(self):
        return self.status == 'active' and timezone.now() < self.end_date
    
    def days_remaining(self):
        remaining = (self.end_date - timezone.now()).days
        return max(0, remaining)


class FitnessProgress(models.Model):
    """
    Tracks user's fitness progress over time.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fitness_progress'
    )
    
    date_recorded = models.DateField(auto_now_add=True)
    weight = models.FloatField(null=True, blank=True, help_text="Weight in kg")
    body_fat_percentage = models.FloatField(null=True, blank=True)
    muscle_mass = models.FloatField(null=True, blank=True, help_text="Muscle mass in kg")
    chest_circumference = models.FloatField(null=True, blank=True, help_text="in cm")
    waist_circumference = models.FloatField(null=True, blank=True, help_text="in cm")
    hip_circumference = models.FloatField(null=True, blank=True, help_text="in cm")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Fitness Progress"
        verbose_name_plural = "Fitness Progress Records"
        ordering = ['-date_recorded']
    
    def __str__(self):
        return f"{self.user.email} - {self.date_recorded}"


class SavedItem(models.Model):
    """
    Tracks saved articles, workouts, products (wishlist/bookmarks).
    """
    ITEM_TYPE_CHOICES = [
        ('article', 'Article'),
        ('workout', 'Workout'),
        ('product', 'Product'),
        ('nutrition', 'Nutrition'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_items'
    )
    
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    item_id = models.IntegerField()  # ID of the article/workout/product
    item_title = models.CharField(max_length=255)
    item_description = models.TextField(blank=True)
    
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Saved Item"
        verbose_name_plural = "Saved Items"
        ordering = ['-saved_at']
        unique_together = ['user', 'item_type', 'item_id']
    
    def __str__(self):
        return f"{self.user.email} - saved {self.item_type}: {self.item_title}"


