import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardApi, hitlApi, feedbackApi } from '../services/api';

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: dashboardApi.metrics,
    refetchInterval: 30_000,
  });
}

export function useHITLQueue(resolved = false) {
  return useQuery({
    queryKey: ['hitlQueue', resolved],
    queryFn: () => hitlApi.queue(resolved),
    refetchInterval: 10_000,
  });
}

export function useResolveHITL() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, alertId, body }: {
      itemId: string;
      alertId: string;
      body: { analyst_username: string; decision: string; notes?: string };
    }) => hitlApi.resolve(itemId, alertId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hitlQueue'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}

export function useFeedbackMetrics() {
  return useQuery({
    queryKey: ['feedbackMetrics'],
    queryFn: feedbackApi.allMetrics,
    staleTime: 60_000,
  });
}
