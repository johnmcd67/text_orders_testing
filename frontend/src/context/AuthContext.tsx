/**
 * Authentication Context
 * Port of FD_WebPages frontend/src/context/AuthContext.js to TypeScript
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import type { ReactNode } from 'react';
import authService from '../services/authService';
import microsoftAuthService from '../services/microsoftAuthService';

// Define types
interface User {
  id: number;
  email: string;
  access_level: number;
  auth_method?: string;
  is_active?: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  loginWithMicrosoft: () => Promise<any>;
  logout: () => void;
}

// Create the Authentication Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Custom hook to use the Auth context
 * @returns Auth context value
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * Authentication Provider Component
 */
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  /**
   * Initialize authentication state on component mount
   */
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // First, check for Microsoft redirect response
        try {
          const microsoftResponse = await microsoftAuthService.handleRedirectResponse();
          if (microsoftResponse) {
            // Microsoft authentication successful
            authService.storeAuth(microsoftResponse.token, microsoftResponse.user);
            setUser(microsoftResponse.user);
            setIsAuthenticated(true);
            setLoading(false);

            // Navigate to dashboard if we're on the login page
            if (window.location.pathname === '/login') {
              window.location.href = '/';
            }
            return;
          }
        } catch (error) {
          console.error('Microsoft redirect handling error:', error);
        }

        // Check if user has stored authentication data
        if (authService.isAuthenticated()) {
          const userData = authService.getCurrentUser();

          // Verify token is still valid BEFORE setting authenticated state
          try {
            await authService.verifyToken();
            // Only set authenticated state if verification succeeds
            setUser(userData);
            setIsAuthenticated(true);
          } catch (error) {
            // Token is invalid, clear auth state silently without API call
            console.warn('Token verification failed:', error);
            authService.clearAuth();
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        // Clear auth state silently without API call
        authService.clearAuth();
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []); // Empty dependency array is correct here

  /**
   * Microsoft login with popup
   * @returns Microsoft authentication response
   */
  const loginWithMicrosoft = async () => {
    try {
      setLoading(true);
      const response = await microsoftAuthService.signInWithPopup();

      // Store authentication data
      authService.storeAuth(response.token, response.user);

      const userData = response.user;
      setUser(userData);
      setIsAuthenticated(true);

      return response;
    } catch (error) {
      console.error('Microsoft login error:', error);
      setUser(null);
      setIsAuthenticated(false);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Logout user
   */
  const logout = async () => {
    try {
      setLoading(true);
      // Sign out from Microsoft
      await microsoftAuthService.signOut();
    } catch (error) {
      console.error('Microsoft sign out error:', error);
    } finally {
      // Clear local auth state
      authService.clearAuth();
      setUser(null);
      setIsAuthenticated(false);
      setLoading(false);

      // Redirect to login page
      window.location.href = '/login';
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated,
    loginWithMicrosoft,
    logout
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
