import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { LanguageToggle } from '@/components/LanguageToggle';
import { LogOut } from 'lucide-react';

export const LandingPage = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { t } = useTranslation(['landing', 'common']);

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#f5f5f5' }}>
      {/* Blue Header Bar */}
      <header
        style={{
          backgroundColor: '#2196F3',
          padding: '24px 32px',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div className="container mx-auto max-w-7xl flex items-center justify-center relative">
          <div style={{ position: 'absolute', left: 0 }}>
            <LanguageToggle />
          </div>
          <h1
            style={{
              color: 'white',
              fontSize: '1.75rem',
              fontWeight: '500',
              margin: 0,
              letterSpacing: '-0.01em',
              textAlign: 'center',
            }}
          >
            {t('landing:title')}
          </h1>
          <Button
            onClick={logout}
            variant="outline"
            style={{
              position: 'absolute',
              right: 0,
              height: '40px',
              minHeight: '40px',
              backgroundColor: 'white',
              color: '#1976D2',
              fontWeight: '600',
              border: '2px solid white',
              borderRadius: '6px',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-blue-50"
          >
            <LogOut className="mr-2 h-4 w-4" />
            {t('common:buttons.logout')}
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-start" style={{ padding: '0 24px', paddingTop: '20vh' }}>
        {/* Action Buttons */}
        <div className="flex justify-center" style={{ gap: '48px' }}>
          <Button
            onClick={() => navigate('/order-processing')}
            style={{
              height: '72px',
              minHeight: '72px',
              minWidth: '270px',
              paddingLeft: '24px',
              paddingRight: '24px',
              backgroundColor: 'white',
              color: '#1976D2',
              fontWeight: '600',
              fontSize: '1.425rem',
              border: '2px solid #1976D2',
              borderRadius: '9px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-blue-50 hover:shadow-md"
          >
            {t('landing:buttons.orderProcessing')}
          </Button>

          <Button
            onClick={() => navigate('/view-prompts')}
            style={{
              height: '72px',
              minHeight: '72px',
              minWidth: '270px',
              paddingLeft: '24px',
              paddingRight: '24px',
              backgroundColor: 'white',
              color: '#1976D2',
              fontWeight: '600',
              fontSize: '1.425rem',
              border: '2px solid #1976D2',
              borderRadius: '9px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-blue-50 hover:shadow-md"
          >
            {t('landing:buttons.viewPrompts')}
          </Button>

          <Button
            onClick={() => navigate('/history')}
            style={{
              height: '72px',
              minHeight: '72px',
              minWidth: '270px',
              paddingLeft: '24px',
              paddingRight: '24px',
              backgroundColor: 'white',
              color: '#1976D2',
              fontWeight: '600',
              fontSize: '1.425rem',
              border: '2px solid #1976D2',
              borderRadius: '9px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-blue-50 hover:shadow-md"
          >
            {t('landing:buttons.history')}
          </Button>
        </div>

      </main>
    </div>
  );
};
