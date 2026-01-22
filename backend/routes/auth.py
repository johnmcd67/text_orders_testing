"""
Authentication Routes
Port of FD_WebPages backend/src/controllers/authController.js to FastAPI
"""

import os
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional

from backend.utils.auth import generate_token, create_user_payload as create_jwt_payload
from backend.middleware.microsoft_auth import verify_microsoft_token_dependency, validate_microsoft_account
from backend.services.user_service import authenticate_microsoft_user, create_user_payload
from backend.middleware.auth import get_current_user


# Create FastAPI router
router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response models
class MicrosoftAuthRequest(BaseModel):
    accessToken: str
    account: Optional[dict] = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/microsoft", response_model=AuthResponse)
async def microsoft_auth(request: Request):
    """
    Authenticate user with Microsoft Office 365

    Flow:
    1. Frontend sends Microsoft access token
    2. Verify token with Microsoft Graph API
    3. Get/create user in database
    4. Generate JWT token
    5. Return user + JWT
    """
    try:
        # Verify Microsoft token and get user profile (using dependency)
        microsoft_user = await verify_microsoft_token_dependency(request)

        # Get request body to check for account data
        body = await request.json()
        account = body.get('account')

        # Validate account data if provided
        validated_account = None
        if account:
            try:
                validated_account = validate_microsoft_account(account)
            except HTTPException as error:
                raise error

        # Authenticate or create user using the Microsoft profile
        user = await authenticate_microsoft_user(microsoft_user)

        if not user:
            raise HTTPException(
                status_code=500,
                detail={'success': False, 'message': 'Failed to authenticate Microsoft user', 'error': 'AUTHENTICATION_FAILED'}
            )

        # Create user payload for response (excluding sensitive data)
        user_response = create_user_payload(user)

        # Generate JWT token using existing auth utilities
        token_payload = create_jwt_payload(user_response)
        token = generate_token(token_payload)

        # Get expiration time from environment
        expires_in = os.getenv('JWT_EXPIRES_IN', '24h')

        return {
            'success': True,
            'message': 'Microsoft authentication successful',
            'data': {
                'user': user_response,
                'token': token,
                'expiresIn': expires_in,
                'authMethod': 'microsoft'
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as error:
        error_msg = str(error)
        print(f'Microsoft authentication error: {error_msg}')

        # Handle specific authentication errors
        status_code = 500
        error_code = 'MICROSOFT_AUTH_ERROR'
        message = 'Microsoft authentication failed'

        if error_msg == 'USER_INACTIVE':
            status_code = 403
            error_code = 'USER_INACTIVE'
            message = 'User account is inactive'
        elif error_msg == 'USER_EMAIL_EXISTS':
            status_code = 409
            error_code = 'USER_EMAIL_EXISTS'
            message = 'User with this email already exists'
        elif error_msg == 'DATABASE_ERROR':
            status_code = 500
            error_code = 'DATABASE_ERROR'
            message = 'Database operation failed'
        elif error_msg == 'AUTHENTICATION_ERROR':
            status_code = 500
            error_code = 'AUTHENTICATION_ERROR'
            message = 'Authentication process failed'

        raise HTTPException(
            status_code=status_code,
            detail={'success': False, 'message': message, 'error': error_code}
        )


@router.get("/profile", response_model=AuthResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile (protected route)
    Requires valid JWT token
    """
    try:
        return {
            'success': True,
            'message': 'Profile retrieved successfully',
            'data': {
                'user': current_user
            }
        }

    except Exception as error:
        print(f'Get profile error: {error}')
        raise HTTPException(
            status_code=500,
            detail={'success': False, 'message': 'Internal server error while retrieving profile', 'error': 'PROFILE_ERROR'}
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Refresh JWT token (protected route)
    Requires valid JWT token
    """
    try:
        # Generate new JWT token
        token_payload = create_jwt_payload(current_user)
        token = generate_token(token_payload)

        # Get expiration time from environment
        expires_in = os.getenv('JWT_EXPIRES_IN', '24h')

        return {
            'success': True,
            'message': 'Token refreshed successfully',
            'data': {
                'token': token,
                'expiresIn': expires_in
            }
        }

    except Exception as error:
        print(f'Token refresh error: {error}')
        raise HTTPException(
            status_code=500,
            detail={'success': False, 'message': 'Internal server error during token refresh', 'error': 'TOKEN_REFRESH_ERROR'}
        )


@router.get("/verify", response_model=AuthResponse)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify token validity (protected route)
    Requires valid JWT token
    """
    try:
        return {
            'success': True,
            'message': 'Token is valid',
            'data': {
                'user': current_user
            }
        }

    except Exception as error:
        print(f'Token verification error: {error}')
        raise HTTPException(
            status_code=500,
            detail={'success': False, 'message': 'Token verification failed', 'error': 'TOKEN_VERIFICATION_ERROR'}
        )
