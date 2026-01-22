import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { jobsApi } from '../api/jobsApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, FileWarning, RefreshCw, CheckCircle, ChevronDown, ChevronUp, X, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface FailureSummaryPanelProps {
  jobId: number;
  compact?: boolean; // For DataReviewTable (compact) vs ResultsDownload (full)
}

export const FailureSummaryPanel = ({ jobId, compact = false }: FailureSummaryPanelProps) => {
  const { t } = useTranslation(['failureSummary', 'common']);
  const [summary, setSummary] = useState<string | null>(null);
  const [failureCount, setFailureCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [hasGenerated, setHasGenerated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noFailures, setNoFailures] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExportPdf = async () => {
    if (!summary) return;

    try {
      setIsExporting(true);
      setError(null);
      await jobsApi.downloadFailureSummaryPdf(jobId);
    } catch (err) {
      console.error('Error exporting PDF:', err);
      setError(t('failureSummary:errors.exportFailed'));
    } finally {
      setIsExporting(false);
    }
  };

  const handleGenerateSummary = async (regenerate: boolean = false) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await jobsApi.getFailureSummary(jobId, regenerate);

      if (!response.has_failures) {
        setSummary(null);
        setFailureCount(0);
        setHasGenerated(true);
        setNoFailures(true);
        return;
      }

      setSummary(response.summary);
      setFailureCount(response.failure_count);
      setHasGenerated(true);
      setNoFailures(false);

    } catch (err) {
      setError(t('failureSummary:errors.generateFailed'));
      console.error('Error generating summary:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // If not generated yet, show button to generate
  if (!hasGenerated) {
    return (
      <div
        className={compact ? 'mb-2' : 'flex flex-col items-center'}
        style={{ maxWidth: compact ? '100%' : '650px', margin: compact ? '0 0 8px 0' : '0 auto 8px auto', width: '100%' }}
      >
          <Button
            onClick={() => handleGenerateSummary(false)}
            disabled={isLoading}
            variant="outline"
            style={{
              height: '48px',
              minHeight: '48px',
              backgroundColor: 'white',
              color: '#F57C00',
              fontWeight: 'bold',
              fontSize: '1.05rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              border: '2px solid #F57C00',
              borderRadius: '9px',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-orange-50 hover:shadow-md"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('failureSummary:status.analyzing')}
              </>
            ) : (
              <>
                <FileWarning className="mr-2 h-4 w-4" />
                {t('failureSummary:buttons.generate')}
              </>
            )}
          </Button>

        {error && (
          <Alert variant="destructive" className="mt-3 border-0">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>
    );
  }

  // If no failures
  if (noFailures) {
    return (
      <Card
        className={`shadow-lg border border-green-200 bg-green-50 ${compact ? 'mb-2' : ''}`}
        style={{ maxWidth: compact ? '100%' : '650px', margin: compact ? '0 0 8px 0' : '0 auto 8px auto', width: '100%' }}
      >
        <CardContent style={{ padding: '16px 24px' }}>
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle className="h-5 w-5" />
            <span className="font-medium">{t('failureSummary:status.allSuccess')}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show summary
  return (
    <Card
      className={`shadow-lg border border-border ${compact ? 'mb-2' : ''}`}
      style={{ maxWidth: compact ? '100%' : '650px', margin: compact ? '0 0 8px 0' : '0 auto 8px auto', width: '100%' }}
    >
      <CardHeader style={{ padding: compact ? '8px 16px' : '12px 24px 8px 24px' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileWarning className="h-5 w-5 text-amber-500" />
            <CardTitle className={compact ? 'text-base' : ''}>
              {t('failureSummary:card.title', { count: failureCount })}
            </CardTitle>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleGenerateSummary(true)}
              disabled={isLoading}
              title={t('failureSummary:tooltips.regenerate')}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportPdf}
              disabled={isExporting || isCollapsed}
              title={t('failureSummary:tooltips.exportPdf')}
            >
              <Download className={`h-4 w-4 ${isExporting ? 'animate-pulse' : ''}`} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCollapsed(!isCollapsed)}
              title={isCollapsed ? t('failureSummary:tooltips.expand') : t('failureSummary:tooltips.collapse')}
            >
              {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setHasGenerated(false)}
              title={t('failureSummary:tooltips.close')}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      {!isCollapsed && (
        <CardContent style={{ padding: compact ? '8px 16px 16px' : '8px 24px 16px 24px' }}>
          <div>
            {/* Title for display */}
            <div className="text-lg font-bold mb-3 pb-2 border-b flex items-center gap-2">
              <FileWarning className="h-5 w-5 text-amber-500" />
              {t('failureSummary:card.title', { count: failureCount })}
            </div>
            {error ? (
              <Alert variant="destructive" className="border-0">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : (
              <div
                className="prose prose-sm max-w-none dark:prose-invert overflow-auto"
                style={{
                  maxHeight: compact ? '300px' : '400px',
                  fontSize: '0.875rem',
                  lineHeight: '1.5',
                }}
              >
              <ReactMarkdown
                components={{
                  h2: ({ children }) => (
                    <h2 className="text-lg font-bold mt-4 mb-2 text-foreground border-b pb-1">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-semibold mt-3 mb-1 text-foreground">{children}</h3>
                  ),
                  p: ({ children }) => (
                    <p className="my-1 text-muted-foreground">{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>
                  ),
                  li: ({ children }) => (
                    <li className="text-muted-foreground">{children}</li>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-foreground">{children}</strong>
                  ),
                  code: ({ children }) => (
                    <code className="bg-muted px-1 py-0.5 rounded text-xs">{children}</code>
                  ),
                }}
              >
                {summary || ''}
              </ReactMarkdown>
            </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
};
