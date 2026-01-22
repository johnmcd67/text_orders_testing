/**
 * Microsoft Authentication Service
 * Handles MSAL authentication and backend JWT token exchange
 */

import axios from 'axios';
import { msalInstance, loginRequest, initializeMsal } from '../utils/msalConfig';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Sign in with Microsoft using popup
 * @returns Authentication response with user and token
 */
export const signInWithPopup = async (): Promise<{user: any, token: string, expiresIn: string}> => {
  try {
    // Validate environment variables
    const clientId = import.meta.env.VITE_AZURE_CLIENT_ID;
    const tenantId = import.meta.env.VITE_AZURE_TENANT_ID;

    if (!clientId || !tenantId) {
      throw new Error('Azure configuration missing. Please set VITE_AZURE_CLIENT_ID and VITE_AZURE_TENANT_ID in your .env file.');
    }

    // Ensure MSAL is initialized
    await initializeMsal();

    // Perform popup login
    const loginResponse = await msalInstance.loginPopup(loginRequest);

    // Get Microsoft access token
    const accessToken = loginResponse.accessToken;
    const account = loginResponse.account;

    // Authenticate with backend to get JWT token
    const backendResponse = await authenticateWithBackend(accessToken, account);

    return backendResponse;
  } catch (error: any) {
    console.error('Microsoft popup login error:', error);
    throw new Error(error.message || 'Microsoft login failed');
  }
};

/**
 * Sign in with Microsoft using redirect
 * @returns Promise that resolves after redirect initiation
 */
export const signInWithRedirect = async (): Promise<void> => {
  try {
    // Ensure MSAL is initialized
    await initializeMsal();

    // Perform redirect login
    await msalInstance.loginRedirect(loginRequest);
  } catch (error: any) {
    console.error('Microsoft redirect login error:', error);
    throw new Error(error.message || 'Microsoft redirect login failed');
  }
};

/**
 * Handle redirect response after Microsoft authentication
 * @returns Authentication response if redirect succeeded, null otherwise
 */
export const handleRedirectResponse = async (): Promise<{user: any, token: string, expiresIn: string} | null> => {
  try {
    // Ensure MSAL is initialized
    await initializeMsal();

    // Handle redirect promise
    const redirectResponse = await msalInstance.handleRedirectPromise();

    if (redirectResponse) {
      const accessToken = redirectResponse.accessToken;
      const account = redirectResponse.account;

      // Authenticate with backend to get JWT token
      const backendResponse = await authenticateWithBackend(accessToken, account);

      return backendResponse;
    }

    return null;
  } catch (error: any) {
    console.error('Handle redirect error:', error);
    throw new Error(error.message || 'Failed to handle redirect response');
  }
};

/**
 * Get Microsoft access token (silently or via interaction)
 * @returns Microsoft access token
 */
export const getAccessToken = async (): Promise<string> => {
  try {
    // Ensure MSAL is initialized
    await initializeMsal();

    const accounts = msalInstance.getAllAccounts();

    if (accounts.length === 0) {
      throw new Error('No accounts found. Please login first.');
    }

    const account = accounts[0];

    // Try to acquire token silently
    try {
      const response = await msalInstance.acquireTokenSilent({
        ...loginRequest,
        account: account
      });

      return response.accessToken;
    } catch (error) {
      // Silent acquisition failed, use popup
      const response = await msalInstance.acquireTokenPopup(loginRequest);
      return response.accessToken;
    }
  } catch (error: any) {
    console.error('Get access token error:', error);
    throw new Error(error.message || 'Failed to get access token');
  }
};

/**
 * Authenticate with backend API using Microsoft access token
 * @param accessToken Microsoft access token
 * @param account Microsoft account info
 * @returns Backend authentication response with JWT token
 */
const authenticateWithBackend = async (
  accessToken: string,
  account: any
): Promise<{user: any, token: string, expiresIn: string}> => {
  try {
    const response = await axios.post(
      `${API_URL}/api/auth/microsoft`,
      {
        accessToken,
        account: account ? {
          username: account.username,
          name: account.name,
          localAccountId: account.localAccountId,
          homeAccountId: account.homeAccountId,
          environment: account.environment
        } : null
      },
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    if (response.data.success) {
      return {
        user: response.data.data.user,
        token: response.data.data.token,
        expiresIn: response.data.data.expiresIn
      };
    } else {
      throw new Error(response.data.message || 'Backend authentication failed');
    }
  } catch (error: any) {
    console.error('Backend authentication error:', error);

    if (error.response) {
      const errorMessage = error.response.data?.message || 'Backend authentication failed';
      throw new Error(errorMessage);
    }

    throw new Error(error.message || 'Failed to authenticate with backend');
  }
};

/**
 * Sign out from Microsoft and clear local session
 */
export const signOut = async (): Promise<void> => {
  try {
    // Ensure MSAL is initialized
    await initializeMsal();

    const accounts = msalInstance.getAllAccounts();

    if (accounts.length > 0) {
      await msalInstance.logoutPopup({
        account: accounts[0]
      });
    }
  } catch (error: any) {
    console.error('Sign out error:', error);
    throw new Error(error.message || 'Sign out failed');
  }
};

export default {
  signInWithPopup,
  signInWithRedirect,
  handleRedirectResponse,
  getAccessToken,
  signOut
};
