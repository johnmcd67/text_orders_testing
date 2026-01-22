"""
JWT Authentication Utilities
Port of FD_WebPages backend/src/utils/auth.js to Python
"""

import os
from datetime import datetime, timedelta
from jose import jwt, JWTError


def generate_token(payload: dict) -> str:
    """
    Generate JWT token for user authentication

    Args:
        payload: User data to include in token (id, email, access_level)

    Returns:
        JWT token string

    Raises:
        Exception: If token generation fails
    """
    try:
        # Get JWT secret from environment
        jwt_secret = os.getenv('JWT_SECRET')
        if not jwt_secret:
            raise ValueError('JWT_SECRET environment variable not set')

        # Get expiration time from environment or default to 24 hours
        expires_in = os.getenv('JWT_EXPIRES_IN', '24h')

        # Convert expires_in string to timedelta
        # Support formats like "24h", "7d", "30m"
        if expires_in.endswith('h'):
            hours = int(expires_in[:-1])
            expiration = datetime.utcnow() + timedelta(hours=hours)
        elif expires_in.endswith('d'):
            days = int(expires_in[:-1])
            expiration = datetime.utcnow() + timedelta(days=days)
        elif expires_in.endswith('m'):
            minutes = int(expires_in[:-1])
            expiration = datetime.utcnow() + timedelta(minutes=minutes)
        else:
            # Default to 24 hours
            expiration = datetime.utcnow() + timedelta(hours=24)

        # Create token payload
        token_data = {
            **payload,
            'exp': expiration,
            'iat': datetime.utcnow(),
            'iss': 'order-intake-api'  # Issuer
        }

        # Generate token
        token = jwt.encode(token_data, jwt_secret, algorithm='HS256')
        return token

    except Exception as error:
        raise Exception(f'Token generation failed: {str(error)}')


def verify_token(token: str) -> dict:
    """
    Verify JWT token

    Args:
        token: JWT token to verify

    Returns:
        Decoded token payload

    Raises:
        Exception: If token verification fails
    """
    try:
        # Get JWT secret from environment
        jwt_secret = os.getenv('JWT_SECRET')
        if not jwt_secret:
            raise ValueError('JWT_SECRET environment variable not set')

        # Verify and decode token
        decoded = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        return decoded

    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.JWTError as error:
        raise Exception('Invalid token')
    except Exception as error:
        raise Exception(f'Token verification failed: {str(error)}')


def extract_token_from_header(auth_header: str) -> str:
    """
    Extract token from Authorization header

    Args:
        auth_header: Authorization header value

    Returns:
        Extracted token or None
    """
    if not auth_header:
        return None

    # Expected format: "Bearer <token>"
    parts = auth_header.split(' ')
    if len(parts) == 2 and parts[0] == 'Bearer':
        return parts[1]

    return None


def create_user_payload(user: dict) -> dict:
    """
    Create user payload for JWT token

    Args:
        user: User object from database

    Returns:
        Sanitized user payload for JWT
    """
    return {
        'id': user['id'],
        'email': user['email'],
        'access_level': user['access_level']
    }
