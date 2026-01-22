import { useTranslation } from 'react-i18next';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface ErrorDisplayProps {
  error: string;
  onRetry?: () => void;
}

export const ErrorDisplay = ({ error, onRetry }: ErrorDisplayProps) => {
  const { t } = useTranslation(['errors', 'common']);
  return (
    <Alert variant="destructive" className="max-w-2xl mx-auto shadow-lg">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{t('errors:jobFailed')}</AlertTitle>
      <AlertDescription>
        <div className="space-y-4">
          <p>{error}</p>
          {onRetry && (
            <div className="flex justify-center">
              <Button
                onClick={onRetry}
                variant="outline"
                size="lg"
                className="px-8 py-3 font-semibold shadow-md hover:shadow-lg transition-shadow"
              >
                {t('common:buttons.retry')}
              </Button>
            </div>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
};

