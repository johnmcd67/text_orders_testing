import { useTranslation } from 'react-i18next';
import type { Job } from '../types/job.types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

interface ProgressTrackerProps {
  job: Job;
}

const getStepInfo = (status: Job['status']) => {
  switch (status) {
    case 'pending':
      return { step: 1, total: 4, statusKey: 'initializing' };
    case 'running':
      return { step: 2, total: 4, statusKey: 'processing' };
    case 'awaiting_review_data':
      return { step: 3, total: 4, statusKey: 'awaitingReview' };
    case 'completed':
      return { step: 4, total: 4, statusKey: 'completed' };
    case 'failed':
      return { step: 0, total: 4, statusKey: 'failed' };
    default:
      return { step: 0, total: 4, statusKey: 'unknown' };
  }
};

const getStatusVariant = (status: Job['status']) => {
  switch (status) {
    case 'completed':
      return 'default' as const;
    case 'failed':
      return 'destructive' as const;
    case 'awaiting_review_data':
      return 'secondary' as const;
    default:
      return 'outline' as const;
  }
};

const getStatusStyle = (status: Job['status']) => {
  switch (status) {
    case 'running':
      return {
        backgroundColor: 'rgb(255, 193, 7)',
        color: 'white',
        border: 'transparent'
      };
    case 'completed':
      return {
        backgroundColor: 'rgb(146, 208, 80)',
        color: 'white',
        border: 'transparent'
      };
    case 'failed':
      return {
        backgroundColor: 'rgb(255, 0, 0)',
        color: 'white',
        border: 'transparent'
      };
    default:
      return {};
  }
};

export const ProgressTracker = ({ job }: ProgressTrackerProps) => {
  const { t } = useTranslation('common');
  const stepInfo = getStepInfo(job.status);
  const progress = job.progress ?? 0;
  const statusLabel = t(`status.${stepInfo.statusKey}`);

  return (
    <Card className="shadow-lg border border-border" style={{ maxWidth: '650px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <CardHeader style={{ paddingTop: '16px', paddingBottom: '4px', paddingLeft: '24px', paddingRight: '24px' }}>
        <CardTitle className="break-words">
          {t('labels.step', { step: stepInfo.step, total: stepInfo.total, label: statusLabel, progress })}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1" style={{ paddingTop: '4px', paddingBottom: '16px', paddingLeft: '24px', paddingRight: '24px' }}>
        <Progress value={progress} className="w-full" />

        {job.progress_message && (
          <p className="text-sm text-muted-foreground">{job.progress_message}</p>
        )}

        <div className="pt-6 space-y-3 text-sm border-t-2">
          <div>
            <span className="font-semibold text-muted-foreground">{t('labels.jobId')}</span>{' '}
            <span className="font-bold">{job.id}</span>
          </div>
          <div>
            <span className="font-semibold text-muted-foreground">{t('labels.status')}</span>{' '}
            <Badge
              variant={getStatusVariant(job.status)}
              style={getStatusStyle(job.status)}
              className="rounded-none"
            >
              {statusLabel}
            </Badge>
          </div>
          <div>
            <span className="font-semibold text-muted-foreground">{t('labels.started')}</span>{' '}
            <span className="font-bold">{new Date(job.created_at).toLocaleString()}</span>
          </div>
          {job.completed_at && (
            <div>
              <span className="font-semibold text-muted-foreground">{t('labels.completed')}</span>{' '}
              <span className="font-bold">{new Date(job.completed_at).toLocaleString()}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

