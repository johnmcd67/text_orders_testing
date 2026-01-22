"""
Microsoft Authentication Middleware
Port of FD_WebPages backend/src/middleware/microsoftAuth.js to Python/FastAPI
"""

import requests
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# Microsoft Graph API endpoints
MICROSOFT_GRAPH_BASE_URL = 'https://graph.microsoft.com/v1.0'
MICROSOFT_GRAPH_ME_ENDPOINT = f'{MICROSOFT_GRAPH_BASE_URL}/me'

# Security scheme for extracting Bearer token
security = HTTPBearer()


async def verify_microsoft_token(access_token: str) -> dict:
    """
    Verify Microsoft access token and extract user profile

    Args:
        access_token: Microsoft access token from MSAL

    Returns:
        User profile from Microsoft Graph

    Raises:
        HTTPException: If token verification fails
    """
    try:
        # Call Microsoft Graph /me endpoint to verify token and get user info
        response = requests.get(
            MICROSOFT_GRAPH_ME_ENDPOINT,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            timeout=10  # 10 second timeout
        )

        # Handle different error status codes
        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail={'message': 'Invalid Microsoft access token', 'error': 'MICROSOFT_TOKEN_INVALID'}
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail={'message': 'Microsoft token has insufficient permissions', 'error': 'MICROSOFT_TOKEN_INSUFFICIENT_SCOPE'}
            )
        elif response.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail={'message': 'Microsoft API rate limit exceeded', 'error': 'MICROSOFT_API_RATE_LIMIT'}
            )
        elif response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail={'message': 'Microsoft API returned an error', 'error': 'MICROSOFT_API_ERROR'}
            )

        return response.json()

    except requests.Timeout:
        raise HTTPException(
            status_code=408,
            detail={'message': 'Microsoft API request timeout', 'error': 'MICROSOFT_API_TIMEOUT'}
        )
    except requests.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail={'message': 'Unable to connect to Microsoft services', 'error': 'MICROSOFT_API_CONNECTION_ERROR'}
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={'message': f'Microsoft token verification failed: {str(error)}', 'error': 'MICROSOFT_TOKEN_VERIFICATION_FAILED'}
        )


async def verify_microsoft_token_dependency(request: Request) -> dict:
    """
    FastAPI dependency to verify Microsoft access token and extract user information
    This validates the Microsoft token but doesn't authenticate the user in our system

    Args:
        request: FastAPI request object

    Returns:
        Microsoft user profile with normalized email

    Raises:
        HTTPException: If token verification fails
    """
    try:
        # Get request body
        body = await request.json()
        access_token = body.get('accessToken')

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail={'message': 'Microsoft access token is required', 'error': 'MISSING_MICROSOFT_TOKEN'}
            )

        # Verify token with Microsoft Graph API
        microsoft_user = await verify_microsoft_token(access_token)

        # Validate required fields from Microsoft Graph response
        if not microsoft_user.get('mail') and not microsoft_user.get('userPrincipalName'):
            raise HTTPException(
                status_code=400,
                detail={'message': 'Microsoft user profile missing email information', 'error': 'MICROSOFT_EMAIL_MISSING'}
            )

        # Extract user information from Microsoft Graph response
        user_email = microsoft_user.get('mail') or microsoft_user.get('userPrincipalName')
        display_name = microsoft_user.get('displayName', '')
        given_name = microsoft_user.get('givenName', '')
        surname = microsoft_user.get('surname', '')

        # Return Microsoft user information
        return {
            'email': user_email.lower(),  # Normalize email to lowercase
            'displayName': display_name,
            'givenName': given_name,
            'surname': surname,
            'rawProfile': microsoft_user
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={'message': f'Microsoft token verification failed: {str(error)}', 'error': 'MICROSOFT_TOKEN_VERIFICATION_FAILED'}
        )


def validate_microsoft_account(account: dict) -> dict:
    """
    Validate Microsoft account data from MSAL

    Args:
        account: Account object from MSAL

    Returns:
        Validated account information

    Raises:
        HTTPException: If account data is invalid
    """
    if not account:
        raise HTTPException(
            status_code=400,
            detail={'message': 'Microsoft account data is required', 'error': 'MICROSOFT_ACCOUNT_MISSING'}
        )

    if not account.get('username'):
        raise HTTPException(
            status_code=400,
            detail={'message': 'Microsoft account username is missing', 'error': 'MICROSOFT_ACCOUNT_USERNAME_MISSING'}
        )

    return {
        'username': account['username'].lower(),
        'name': account.get('name', ''),
        'localAccountId': account.get('localAccountId', ''),
        'homeAccountId': account.get('homeAccountId', ''),
        'environment': account.get('environment', '')
    }
