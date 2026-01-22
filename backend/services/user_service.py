"""
User Service
Port of FD_WebPages backend/src/services/userService.js to Python
Handles user database operations
"""

import psycopg
from datetime import datetime
from backend.database import get_db_connection


async def find_user_by_email(email: str) -> dict:
    """
    Find user by email address

    Args:
        email: User email address

    Returns:
        User object or None if not found

    Raises:
        Exception: If database operation fails
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, password, access_level, created_at,
                       updated_at, microsoft_id, auth_method, is_active
                FROM public.users
                WHERE email = %s
                """,
                (email.lower(),)
            )
            row = cur.fetchone()

            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'password': row[2],
                    'access_level': row[3],
                    'created_at': row[4],
                    'updated_at': row[5],
                    'microsoft_id': row[6],
                    'auth_method': row[7],
                    'is_active': row[8]
                }

            return None

    except Exception as error:
        print(f'Error finding user by email: {error}')
        raise Exception('DATABASE_ERROR')
    finally:
        conn.close()


async def create_microsoft_user(microsoft_user: dict) -> dict:
    """
    Create new user with Microsoft authentication

    Args:
        microsoft_user: Microsoft user profile from Graph API

    Returns:
        Created user object

    Raises:
        Exception: If user creation fails
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert new user
            cur.execute(
                """
                INSERT INTO public.users (email, password, access_level, auth_method, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, access_level, created_at, updated_at, auth_method, is_active
                """,
                (
                    microsoft_user['email'].lower(),
                    '',  # Empty password for Microsoft users
                    1,  # Default basic user level
                    'microsoft',
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
            )
            row = cur.fetchone()
            conn.commit()

            return {
                'id': row[0],
                'email': row[1],
                'access_level': row[2],
                'created_at': row[3],
                'updated_at': row[4],
                'auth_method': row[5],
                'is_active': row[6]
            }

    except psycopg.errors.UniqueViolation:
        raise Exception('USER_EMAIL_EXISTS')
    except Exception as error:
        print(f'Error creating Microsoft user: {error}')
        raise Exception('DATABASE_ERROR')
    finally:
        conn.close()


def can_user_authenticate(user: dict) -> bool:
    """
    Check if user is active and can authenticate

    Args:
        user: User object

    Returns:
        True if user can authenticate
    """
    return user and user.get('is_active') == True


def create_user_payload(user: dict) -> dict:
    """
    Create user payload for JWT token (excluding sensitive data)

    Args:
        user: User object from database

    Returns:
        Clean user object for JWT and responses
    """
    return {
        'id': user['id'],
        'email': user['email'],
        'access_level': user['access_level'],
        'created_at': user['created_at'].isoformat() if user.get('created_at') else None,
        'updated_at': user['updated_at'].isoformat() if user.get('updated_at') else None,
        'auth_method': user['auth_method'],
        'is_active': user['is_active']
    }


async def authenticate_microsoft_user(microsoft_user: dict) -> dict:
    """
    Handle Microsoft user authentication flow

    Args:
        microsoft_user: Microsoft user profile from Graph API

    Returns:
        Authenticated user object

    Raises:
        Exception: If authentication fails
    """
    try:
        # Check if user exists by email
        user = await find_user_by_email(microsoft_user['email'])

        if user:
            # Existing user found
            if not can_user_authenticate(user):
                raise Exception('USER_INACTIVE')

            # Update auth_method if needed
            if user['auth_method'] != 'microsoft':
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE public.users
                            SET auth_method = %s, updated_at = %s
                            WHERE id = %s
                            RETURNING id, email, access_level, created_at, updated_at, auth_method, is_active
                            """,
                            ('microsoft', datetime.utcnow(), user['id'])
                        )
                        row = cur.fetchone()
                        conn.commit()

                        return {
                            'id': row[0],
                            'email': row[1],
                            'access_level': row[2],
                            'created_at': row[3],
                            'updated_at': row[4],
                            'auth_method': row[5],
                            'is_active': row[6]
                        }
                finally:
                    conn.close()

            return user

        # No existing user - create new one
        new_user = await create_microsoft_user(microsoft_user)
        return new_user

    except Exception as error:
        print(f'Error in Microsoft user authentication: {error}')
        raise error
