/**
 * Authentication Service
 * Manages JWT token and user data storage
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// LocalStorage keys
const TOKEN_KEY = 'authToken';
const USER_KEY = 'userData';

/**
 * Store authentication data (token + user)
 * @param token JWT token
 * @param user User data
 */
export const storeAuth = (token: string, user: any): void => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

/**
 * Get stored JWT token
 * @returns JWT token or null
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * Get stored user data
 * @returns User object or null
 */
export const getCurrentUser = (): any | null => {
  const userStr = localStorage.getItem(USER_KEY);
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (error) {
      console.error('Error parsing user data:', error);
      return null;
    }
  }
  return null;
};

/**
 * Check if user is authenticated
 * @returns True if token exists
 */
export const isAuthenticated = (): boolean => {
  const token = getToken();
  return token !== null && token !== '';
};

/**
 * Clear authentication data
 */
export const clearAuth = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

/**
 * Verify token with backend
 * @returns Promise that resolves if token is valid
 */
export const verifyToken = async (): Promise<void> => {
  const token = getToken();

  if (!token) {
    throw new Error('No token found');
  }

  try {
    const response = await axios.get(
      `${API_URL}/api/auth/verify`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.data.success) {
      throw new Error('Token verification failed');
    }
  } catch (error: any) {
    console.error('Token verification error:', error);

    if (error.response && error.response.status === 401) {
      // Token is invalid, clear auth data
      clearAuth();
    }

    throw error;
  }
};

/**
 * Refresh JWT token
 * @returns New JWT token
 */
export const refreshToken = async (): Promise<string> => {
  const token = getToken();

  if (!token) {
    throw new Error('No token found');
  }

  try {
    const response = await axios.post(
      `${API_URL}/api/auth/refresh`,
      {},
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (response.data.success) {
      const newToken = response.data.data.token;
      localStorage.setItem(TOKEN_KEY, newToken);
      return newToken;
    } else {
      throw new Error('Token refresh failed');
    }
  } catch (error: any) {
    console.error('Token refresh error:', error);

    if (error.response && error.response.status === 401) {
      // Token is invalid, clear auth data
      clearAuth();
    }

    throw error;
  }
};

export default {
  storeAuth,
  getToken,
  getCurrentUser,
  isAuthenticated,
  clearAuth,
  verifyToken,
  refreshToken
};
