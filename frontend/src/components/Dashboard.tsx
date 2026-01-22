import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { StartJobButton } from './StartJobButton';
import { ProgressTracker } from './ProgressTracker';
import { DataReviewTable } from './DataReviewTable';
import { ResultsDownload } from './ResultsDownload';
import { ErrorDisplay } from './ErrorDisplay';
import { LanguageToggle } from './LanguageToggle';
import { useJobPolling } from '../hooks/useJobPolling';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

const STORAGE_KEY = 'activeJobId';

export const Dashboard = () => {
  const navigate = useNavigate();
  const { t } = useTranslation(['dashboard', 'common']);

  const [currentJobId, setCurrentJobId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? parseInt(stored, 10) : null;
  });

  const { data: job, isLoading, refetch } = useJobPolling(currentJobId, currentJobId !== null);

  useEffect(() => {
    if (currentJobId !== null) {
      localStorage.setItem(STORAGE_KEY, currentJobId.toString());
      console.log('[Dashboard] Saved job ID to localStorage:', currentJobId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
      console.log('[Dashboard] Removed job ID from localStorage');
    }
  }, [currentJobId]);

  useEffect(() => {
    if (job?.status === 'completed' || job?.status === 'failed') {
      console.log('[Dashboard] Job finished, will clear on next reset');
    }
  }, [job?.status]);

  const handleJobStarted = (jobId: number) => {
    setCurrentJobId(jobId);
  };

  const handleDataApproval = async () => {
    await refetch();
  };

  const handleRejection = () => {
    setCurrentJobId(null);
  };

  const handleRetry = () => {
    setCurrentJobId(null);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#f5f5f5' }}>
      {/* Blue Header Bar */}
      <header
        style={{
          backgroundColor: '#2196F3',
          padding: '16px 32px',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
          position: 'relative',
          zIndex: 60,
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
            {t('dashboard:title')}
          </h1>
        </div>
      </header>

      <div className="container mx-auto max-w-7xl flex-1" style={{ padding: '12px 24px' }}>
        <div style={{ marginBottom: '8px' }}>
          <Button
            onClick={() => navigate('/')}
            variant="outline"
            style={{
              height: '40px',
              minHeight: '40px',
              backgroundColor: 'white',
              color: '#1976D2',
              fontWeight: '600',
              border: '2px solid #1976D2',
              borderRadius: '9px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-blue-50 hover:shadow-md"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common:buttons.backToHome')}
          </Button>
        </div>

        <div className="space-y-2" style={{ marginTop: '8px' }}>
          {!currentJobId && (
            <Card className="mx-auto shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd', maxWidth: '336px' }}>
              <CardContent style={{ paddingTop: '32px', paddingBottom: '32px', paddingLeft: '24px', paddingRight: '24px' }}>
                <StartJobButton
                  onJobStarted={handleJobStarted}
                  disabled={isLoading}
                />
              </CardContent>
            </Card>
          )}

          {job && job.status !== 'awaiting_review_data' && (
            <div style={{ marginBottom: job?.status === 'completed' ? '8px' : '0' }}>
              <ProgressTracker job={job} />
            </div>
          )}

          {job?.status === 'failed' && (
            <ErrorDisplay
              error="The job encountered an error during processing. Please check the logs."
              onRetry={handleRetry}
            />
          )}

          {job?.status === 'completed' && (
            <ResultsDownload jobId={job.id} />
          )}

          {job?.status === 'completed' && (
            <div className="flex justify-center pb-2" style={{ marginTop: '0' }}>
              <Button
                onClick={() => setCurrentJobId(null)}
                variant="outline"
                style={{
                  height: '48px',
                  minHeight: '48px',
                  width: '260px',
                  backgroundColor: 'white',
                  color: '#4CAF50',
                  fontWeight: 'bold',
                  fontSize: '1.05rem',
                  border: '2px solid #4CAF50',
                  borderRadius: '9px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
                  transition: 'all 0.2s ease',
                }}
                className="hover:bg-green-50 hover:shadow-md"
              >
                {t('common:buttons.startNewJob')}
              </Button>
            </div>
          )}
        </div>

        {job?.status === 'awaiting_review_data' && (
          <DataReviewTable
            jobId={job.id}
            onApprove={handleDataApproval}
            onReject={handleRejection}
          />
        )}
      </div>
    </div>
  );
};

