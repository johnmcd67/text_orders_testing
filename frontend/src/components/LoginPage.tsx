/**
 * Login Page Component
 * Provides Microsoft Office 365 authentication
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LanguageToggle } from './LanguageToggle';

export default function LoginPage() {
  const navigate = useNavigate();
  const { t } = useTranslation(['login', 'common']);
  const { loginWithMicrosoft } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMicrosoftLogin = async () => {
    try {
      setLoading(true);
      setError(null);

      await loginWithMicrosoft();

      // Navigate to landing page
      navigate('/');
    } catch (err: any) {
      console.error('Login error:', err);
      const errorMessage = err.message || err.errorCode || 'Login failed. Please try again.';
      setError(errorMessage);

      // Log additional error details for debugging
      if (err.errorCode) {
        console.error('MSAL error code:', err.errorCode);
      }
      if (err.stack) {
        console.error('Error stack:', err.stack);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        backgroundColor: '#e5e7eb',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          backgroundColor: 'white',
          borderRadius: '16px',
          padding: '48px 40px',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
          position: 'relative',
        }}
      >
        {/* Language Toggle - Top Right */}
        <div style={{ position: 'absolute', top: '16px', right: '16px' }}>
          <LanguageToggle />
        </div>

        {/* Header Section */}
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <img
            src="/FD_logotipo.svg"
            alt="F&D In Shower Tray"
            style={{
              width: '180px',
              height: 'auto',
              marginBottom: '8px',
            }}
          />
          <h1
            style={{
              fontSize: '26px',
              fontWeight: '700',
              color: '#1a1a1a',
              margin: '0',
              fontFamily: 'Segoe UI, system-ui, -apple-system, sans-serif',
            }}
          >
            {t('login:title')}
          </h1>
        </div>

        {/* Error Message */}
        {error && (
          <div
            style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              color: '#b91c1c',
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '24px',
              fontSize: '14px',
            }}
          >
            {error}
          </div>
        )}

        {/* Sign In Button */}
        <button
          onClick={handleMicrosoftLogin}
          disabled={loading}
          style={{
            width: '100%',
            height: '48px',
            backgroundColor: '#0078d4',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '16px',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            opacity: loading ? 0.7 : 1,
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!loading) e.currentTarget.style.backgroundColor = '#106ebe';
          }}
          onMouseLeave={(e) => {
            if (!loading) e.currentTarget.style.backgroundColor = '#0078d4';
          }}
        >
          {loading ? (
            <>
              <svg
                style={{ animation: 'spin 1s linear infinite', width: '20px', height: '20px' }}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  style={{ opacity: 0.25 }}
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  style={{ opacity: 0.75 }}
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              {t('common:status.signingIn')}
            </>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="1" y="1" width="9" height="9" fill="#F25022" />
                <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
                <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
                <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
              </svg>
              {t('login:buttons.signIn')}
            </>
          )}
        </button>

        {/* Enterprise Authentication Info */}
        <div
          style={{
            marginTop: '32px',
            padding: '20px',
            backgroundColor: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            textAlign: 'center',
          }}
        >
          <h3
            style={{
              fontSize: '12px',
              fontWeight: '700',
              color: '#4b5563',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              margin: '0 0 8px 0',
            }}
          >
            {t('login:enterprise.title')}
          </h3>
          <p
            style={{
              fontSize: '13px',
              color: '#6b7280',
              margin: '0',
              lineHeight: '1.5',
            }}
          >
            {t('login:enterprise.description')}
          </p>
        </div>
      </div>

      {/* Keyframe animation for spinner */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
