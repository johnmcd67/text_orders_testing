import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { jobsApi } from '../api/jobsApi';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, AlertTriangle } from 'lucide-react';
import { FailureSummaryPanel } from './FailureSummaryPanel';

interface ResultsDownloadProps {
  jobId: number;
}

export const ResultsDownload = ({ jobId }: ResultsDownloadProps) => {
  const { t } = useTranslation(['dashboard', 'common']);
  const [isDownloading, setIsDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const getFileTypeName = (fileType: 'order_details' | 'failed_orders') => {
    return fileType === 'order_details'
      ? t('dashboard:resultsDownload.claveiInput')
      : t('dashboard:resultsDownload.failedOrders');
  };

  const handleDownload = async (fileType: 'order_details' | 'failed_orders') => {
    try {
      setIsDownloading(fileType);
      setError(null);
      await jobsApi.downloadResults(jobId, fileType);
    } catch (err: unknown) {
      const fileTypeName = getFileTypeName(fileType);
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { status?: number } };
        if (axiosError.response?.status === 404) {
          setError(t('dashboard:errors.fileNotFound', { fileType: fileTypeName }));
        } else {
          setError(t('dashboard:errors.downloadFailed', { fileType: fileTypeName }));
        }
      } else {
        setError(t('dashboard:errors.downloadFailed', { fileType: fileTypeName }));
      }
      console.error('Error downloading results:', err);
    } finally {
      setIsDownloading(null);
    }
  };

  return (
    <>
    <Card className="shadow-lg border border-border" style={{ maxWidth: '650px', margin: '0 auto 8px auto', width: '100%', boxSizing: 'border-box' }}>
      <CardHeader style={{ padding: '12px 24px 8px 24px' }}>
        <CardTitle>{t('dashboard:resultsDownload.title')}</CardTitle>
        <CardDescription>
          {t('dashboard:resultsDownload.description')}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2" style={{ padding: '8px 24px 12px 24px' }}>
        <div className="flex gap-6 justify-center flex-wrap">
          <Button
            onClick={() => handleDownload('order_details')}
            disabled={isDownloading !== null}
            variant="outline"
            style={{
              height: '48px',
              minHeight: '48px',
              width: '216px',
              backgroundColor: 'white',
              color: '#4CAF50',
              fontWeight: 'bold',
              fontSize: '1.05rem',
              marginRight: '16px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              border: '2px solid #4CAF50',
              borderRadius: '9px',
              transition: 'all 0.2s ease'
            }}
            className="hover:bg-green-50 hover:shadow-md"
          >
            <Download className="mr-2 h-4 w-4" />
            {isDownloading === 'order_details' ? t('common:status.downloading') : t('dashboard:resultsDownload.claveiInput')}
          </Button>

          <Button
            onClick={() => handleDownload('failed_orders')}
            disabled={isDownloading !== null}
            variant="outline"
            style={{
              height: '48px',
              minHeight: '48px',
              width: '216px',
              backgroundColor: 'white',
              color: '#D32F2F',
              fontWeight: 'bold',
              fontSize: '1.05rem',
              marginLeft: '16px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              border: '2px solid #D32F2F',
              borderRadius: '9px',
              transition: 'all 0.2s ease'
            }}
            className="hover:bg-red-50 hover:shadow-md"
          >
            <AlertTriangle className="mr-2 h-4 w-4" />
            {isDownloading === 'failed_orders' ? t('common:status.downloading') : t('dashboard:resultsDownload.failedOrders')}
          </Button>
        </div>

        {error && (
          <Alert variant="destructive" className="border-0">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="pt-3 border-t text-sm text-muted-foreground">
          <p className="font-medium mb-1.5">{t('dashboard:resultsDownload.expectedFiles')}</p>
          <ul className="space-y-0.5">
            <li className="flex items-start gap-2">
              <Download className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span><code className="text-xs">{t('dashboard:resultsDownload.claveiFileName', { jobId })}</code> - {t('dashboard:resultsDownload.claveiDescription')}</span>
            </li>
            <li className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span><code className="text-xs">{t('dashboard:resultsDownload.failedFileName', { jobId })}</code> - {t('dashboard:resultsDownload.failedDescription')}</span>
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>

    {/* Failure Summary Panel - AI-powered analysis of failed orders */}
    <FailureSummaryPanel jobId={jobId} compact={false} />
    </>
  );
};

