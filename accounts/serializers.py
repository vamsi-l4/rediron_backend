from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UserActivityData, UserProfile, Address, FitnessProgress,
    SavedItem, GymSubscription, PaymentTransaction
)

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'name')

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            name=validated_data['name'],
            is_active=False,
            is_verified=False
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'profile_image')
        read_only_fields = ('email',)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        profile_image = validated_data.get('profile_image', None)
        if profile_image is not None:
            instance.profile_image = profile_image
        instance.save()
        return instance


class UserActivityDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityData
        fields = ('data',)

# ============================================
# PRODUCTION-GRADE PROFILE SERIALIZERS (NEW)
# ============================================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Extended user profile with complete fitnes and personal information.
    """
    profile_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = (
            'id', 'user', 'phone_number', 'date_of_birth', 'gender', 'bio',
            'is_email_verified', 'profile_image', 'is_complete',
            'weight', 'height', 'fitness_goal', 'experience_level',
            'preferred_language', 'timezone', 'receive_notifications',
            'receive_emails', 'last_login', 'created_at', 'updated_at',
            'profile_completion'
        )
        read_only_fields = ('id', 'user', 'is_email_verified', 'created_at', 'updated_at')
    
    def get_profile_completion(self, obj):
        """Return profile completion percentage"""
        return obj.complete_percentage()


class AddressSerializer(serializers.ModelSerializer):
    """
    User address management for shipping and billing.
    """
    class Meta:
        model = Address
        fields = (
            'id', 'user', 'address_type', 'recipient_name', 'phone', 'street_address', 'city',
            'state', 'postal_code', 'country', 'is_primary',
            'is_default_shipping', 'is_default_billing', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def validate(self, data):
        """Prevent multiple primary addresses"""
        user = self.context['request'].user
        if data.get('is_primary'):
            # Keep a single default address on both creation and updates.
            addresses = Address.objects.filter(user=user, is_primary=True)
            if self.instance:
                addresses = addresses.exclude(pk=self.instance.pk)
            addresses.update(is_primary=False, is_default_shipping=False)
        return data


class FitnessProgressSerializer(serializers.ModelSerializer):
    """
    Track fitness progress over time.
    """
    class Meta:
        model = FitnessProgress
        fields = (
            'id', 'user', 'date_recorded', 'weight', 'body_fat_percentage',
            'muscle_mass', 'chest_circumference', 'waist_circumference',
            'hip_circumference', 'notes', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')


class GymSubscriptionSerializer(serializers.ModelSerializer):
    """
    Gym membership subscription details.
    """
    is_active = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = GymSubscription
        fields = (
            'id', 'user', 'plan', 'status', 'price', 'start_date',
            'end_date', 'auto_renewal', 'payment_method', 'created_at',
            'updated_at', 'is_active', 'days_remaining'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_days_remaining(self, obj):
        return obj.days_remaining()


class SavedItemSerializer(serializers.ModelSerializer):
    """
    Saved articles, workouts, products (bookmarks/wishlist).
    """
    class Meta:
        model = SavedItem
        fields = (
            'id', 'user', 'item_type', 'item_id', 'item_title',
            'item_description', 'saved_at'
        )
        read_only_fields = ('id', 'user', 'saved_at')


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Payment transaction history.
    """
    class Meta:
        model = PaymentTransaction
        fields = (
            'id', 'user', 'payment_id', 'amount', 'currency', 'status',
            'method', 'plan', 'description', 'metadata', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class ExtendedUserSerializer(serializers.ModelSerializer):
    """
    Complete user data with all related profile information.
    Used for the comprehensive profile endpoint.
    """
    profile = UserProfileSerializer(read_only=True)
    addresses = AddressSerializer(many=True, read_only=True)
    gym_subscription = GymSubscriptionSerializer(read_only=True)
    fitness_progress = FitnessProgressSerializer(many=True, read_only=True)
    saved_items = SavedItemSerializer(many=True, read_only=True)
    payment_transactions = PaymentTransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'profile_image', 'clerk_user_id',
            'is_active', 'is_verified', 'auto_payment',
            'profile', 'addresses', 'gym_subscription', 'fitness_progress',
            'saved_items', 'payment_transactions'
        )
        read_only_fields = ('id', 'email', 'clerk_user_id')
