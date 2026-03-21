import { useQuery } from '@tanstack/react-query';
import { dashboardApi, feedbackApi } from '../services/api';

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: dashboardApi.metrics,
    refetchInterval: 30_000,
  });
}

export function useAuditTrail(limit = 50) {
  return useQuery({
    queryKey: ['auditTrail', limit],
    queryFn: () => dashboardApi.auditTrail(limit),
    refetchInterval: 60_000,
  });
}

export function useFeedbackMetrics() {
  return useQuery({
    queryKey: ['feedbackMetrics'],
    queryFn: feedbackApi.allMetrics,
    staleTime: 5 * 60_000,
  });
}
