import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { jobsApi } from '../api/jobsApi';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

interface StartJobButtonProps {
  onJobStarted: (jobId: number) => void;
  disabled?: boolean;
}

export const StartJobButton = ({ onJobStarted, disabled }: StartJobButtonProps) => {
  const { t } = useTranslation(['dashboard', 'common']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await jobsApi.startJob();
      onJobStarted(response.job_id);
    } catch (err) {
      setError(t('dashboard:errors.startJobFailed'));
      console.error('Error starting job:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <Button
        onClick={handleStart}
        disabled={disabled || isLoading}
        style={{
          height: '48px',
          minHeight: '48px',
          width: '216px',
          backgroundColor: 'white',
          color: '#1976D2',
          fontWeight: '600',
          fontSize: '1.05rem',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
          border: '2px solid #1976D2',
          borderRadius: '9px',
          transition: 'all 0.2s ease'
        }}
        className="hover:bg-blue-50 hover:shadow-md"
      >
{isLoading ? t('common:status.starting') : t('dashboard:buttons.processOrders')}
      </Button>
      {error && (
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
};

