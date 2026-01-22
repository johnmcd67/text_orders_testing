/**
 * MSAL Configuration for Office 365 Authentication
 * Port of FD_WebPages frontend/src/utils/msalConfig.js to TypeScript
 */

import { PublicClientApplication, LogLevel } from '@azure/msal-browser';

/**
 * MSAL Configuration
 */
const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || '',
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID || 'common'}`,
    redirectUri: window.location.origin + '/',  // Ensure it includes the trailing slash
    postLogoutRedirectUri: window.location.origin,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation: 'localStorage', // This configures where your cache will be stored
    storeAuthStateInCookie: false, // Set this to "true" if you are having issues on IE11 or Edge
  },
  system: {
    loggerOptions: {
      loggerCallback: (level: LogLevel, message: string, containsPii: boolean) => {
        if (containsPii) {
          return;
        }
        switch (level) {
          case LogLevel.Error:
            console.error(message);
            return;
          case LogLevel.Info:
            console.info(message);
            return;
          case LogLevel.Verbose:
            console.debug(message);
            return;
          case LogLevel.Warning:
            console.warn(message);
            return;
        }
      },
    },
  },
};

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 */
export const loginRequest = {
  scopes: ['User.Read'],
};

/**
 * Scopes for silent token acquisition
 */
export const tokenRequest = {
  scopes: ['User.Read'],
  forceRefresh: false, // Set this to "true" to skip a cached token and go to the server to get a new token
};

/**
 * Initialize the MSAL instance to be exported and used in other components
 */
export const msalInstance = new PublicClientApplication(msalConfig);

// MSAL v3 requires explicit initialization
let msalInitialized = false;
let initializationPromise: Promise<void> | null = null;

/**
 * Initialize MSAL instance (required for v3.x)
 */
export const initializeMsal = async (): Promise<void> => {
  if (msalInitialized) {
    return;
  }

  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = msalInstance.initialize().then(() => {
    msalInitialized = true;

    // Handle the response from redirect flow after initialization
    return msalInstance.handleRedirectPromise().then((response) => {
      if (response !== null) {
        console.log('MSAL redirect response:', response);
      }
    }).catch((error) => {
      console.error('MSAL redirect error:', error);
    });
  });

  return initializationPromise;
};

// Start initialization immediately
initializeMsal();

export default msalConfig;
