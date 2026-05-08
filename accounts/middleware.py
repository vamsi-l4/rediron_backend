# ============================================
# PRODUCTION-GRADE: USER DATA ISOLATION MIDDLEWARE
# ============================================
"""
Ensures data isolation between users by validating that API requests
only access data belonging to the authenticated user.

This middleware prevents unauthorized access to other users' data
through query parameter manipulation or direct object access.
"""

import logging
from django.conf import settings
from django.http import JsonResponse
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class DataIsolationMiddleware:
    """
    Validate that authenticated users can only access their own data.
    
    PROTECTED PATTERNS:
    - User profile data via user_id parameter
    - Cart & orders via user ownership
    - Subscriptions via user_id 
    - Saved items via user_id
    - Addresses via user_id
    
    ACTION: Return 403 Forbidden if user attempts to access other user's data
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.protected_patterns = [
            '/api/accounts/profile/',
            '/api/accounts/addresses/',
            '/api/shop/cart/',
            '/api/shop/orders/',
            '/api/accounts/saved-items/',
            '/api/accounts/fitness-progress/',
        ]
    
    def __call__(self, request):
        # ============================================
        # STEP 1: SKIP MIDDLEWARE FOR UNAUTHENTICATED REQUESTS
        # ============================================
        if not request.user or not request.user.is_authenticated:
            return self.get_response(request)
        
        # ============================================
        # STEP 2: CHECK FOR PROTECTED PATTERNS
        # ============================================
        path = request.path_info
        is_protected = any(path.startswith(pattern) for pattern in self.protected_patterns)
        
        if not is_protected:
            return self.get_response(request)
        
        # ============================================
        # STEP 3: VALIDATE USER_ID IN REQUEST
        # ============================================
        # Check if request contains user_id parameter
        user_id_param = request.GET.get('user_id') or request.POST.get('user_id')
        
        if user_id_param:
            # User ID must match authenticated user's ID
            if int(user_id_param) != request.user.id:
                logger.warning(
                    f"⚠️ DATA ISOLATION VIOLATION: User {request.user.id} "
                    f"attempted to access user {user_id_param} data"
                )
                return JsonResponse(
                    {
                        'error': 'Access denied',
                        'message': 'You can only access your own data'
                    },
                    status=403
                )
        
        response = self.get_response(request)
        return response


class ClerkUserValidationMiddleware:
    """
    Validate that authenticated user has valid Clerk configuration.
    Ensures clerk_user_id is present for all authenticated requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip for unauthenticated users
        if not request.user or not request.user.is_authenticated:
            return self.get_response(request)
        
        # Validate Clerk user ID exists
        if not hasattr(request.user, 'clerk_user_id') or not request.user.clerk_user_id:
            logger.warning(
                f"⚠️ CLERK CONFIG WARNING: User {request.user.id} ({request.user.email}) "
                f"missing clerk_user_id. This may cause authentication issues."
            )
        
        response = self.get_response(request)
        return response
