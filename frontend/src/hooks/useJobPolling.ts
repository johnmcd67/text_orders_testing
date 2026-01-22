import { useQuery } from '@tanstack/react-query';
import { jobsApi } from '../api/jobsApi';
import type { Job } from '../types/job.types';

export const useJobPolling = (jobId: number | null, enabled: boolean = true) => {
  return useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getJobStatus(jobId!),
    enabled: enabled && jobId !== null,
    refetchInterval: (query) => {
      const data = query.state.data;
      console.log('[useJobPolling] Current status:', data?.status);

      if (data?.status === 'running' || data?.status === 'pending') {
        console.log('[useJobPolling] Continuing to poll...');
        return 2000;
      }
      console.log('[useJobPolling] Stopping poll, status:', data?.status);
      return false;
    },
    refetchIntervalInBackground: true,
  });
};

