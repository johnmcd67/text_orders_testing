"""
JWT Authentication Middleware
FastAPI dependency for protecting routes with JWT tokens
"""

from fastapi import HTTPException, Depends, Header
from typing import Optional

from backend.utils.auth import verify_token, extract_token_from_header
from backend.services.user_service import find_user_by_email


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    FastAPI dependency for JWT authentication
    Extracts and verifies JWT token from Authorization header

    Args:
        authorization: Authorization header value (automatically injected by FastAPI)

    Returns:
        Current user dict

    Raises:
        HTTPException: If token is missing, invalid, or user not found
    """
    try:
        # Check if Authorization header exists
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail={'success': False, 'message': 'Authorization header is required', 'error': 'MISSING_AUTH_HEADER'}
            )

        # Extract token from header (format: "Bearer <token>")
        token = extract_token_from_header(authorization)

        if not token:
            raise HTTPException(
                status_code=401,
                detail={'success': False, 'message': 'Invalid Authorization header format. Expected: Bearer <token>', 'error': 'INVALID_AUTH_HEADER'}
            )

        # Verify token
        try:
            decoded = verify_token(token)
        except Exception as error:
            error_msg = str(error)
            if 'expired' in error_msg.lower():
                raise HTTPException(
                    status_code=401,
                    detail={'success': False, 'message': 'Token has expired', 'error': 'TOKEN_EXPIRED'}
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail={'success': False, 'message': 'Invalid token', 'error': 'TOKEN_INVALID'}
                )

        # Extract user information from token
        user_id = decoded.get('id')
        user_email = decoded.get('email')
        access_level = decoded.get('access_level')

        if not user_id or not user_email:
            raise HTTPException(
                status_code=401,
                detail={'success': False, 'message': 'Token payload is incomplete', 'error': 'TOKEN_INVALID_PAYLOAD'}
            )

        # Verify user still exists and is active
        user = await find_user_by_email(user_email)

        if not user:
            raise HTTPException(
                status_code=401,
                detail={'success': False, 'message': 'User not found', 'error': 'USER_NOT_FOUND'}
            )

        if not user.get('is_active'):
            raise HTTPException(
                status_code=403,
                detail={'success': False, 'message': 'User account is inactive', 'error': 'USER_INACTIVE'}
            )

        # Return user information (excluding sensitive data)
        return {
            'id': user['id'],
            'email': user['email'],
            'access_level': user['access_level'],
            'auth_method': user.get('auth_method'),
            'is_active': user.get('is_active')
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as error:
        print(f'Authentication error: {error}')
        raise HTTPException(
            status_code=500,
            detail={'success': False, 'message': 'Internal server error during authentication', 'error': 'AUTHENTICATION_ERROR'}
        )


async def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Optional authentication dependency
    Returns user if authenticated, None if not
    Does not raise exceptions for missing/invalid tokens

    Args:
        authorization: Authorization header value

    Returns:
        Current user dict or None
    """
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
    except Exception:
        return None
