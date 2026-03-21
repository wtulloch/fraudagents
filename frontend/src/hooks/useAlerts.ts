import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi } from '../services/api';
import type { AlertStatus } from '../types';

export function useAlerts(status?: AlertStatus) {
  return useQuery({
    queryKey: ['alerts', status],
    queryFn: () => alertsApi.list(status),
    refetchInterval: 15_000,
  });
}

export function useAlert(alertId: string, accountId: string) {
  return useQuery({
    queryKey: ['alert', alertId],
    queryFn: () => alertsApi.get(alertId, accountId),
    enabled: !!alertId && !!accountId,
  });
}

export function useInvestigateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, accountId, sessionId }: { alertId: string; accountId: string; sessionId?: string }) =>
      alertsApi.investigate(alertId, accountId, sessionId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['alert', variables.alertId] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['agentRuns', variables.alertId] });
    },
  });
}

export function useAgentRuns(alertId: string) {
  return useQuery({
    queryKey: ['agentRuns', alertId],
    queryFn: () => alertsApi.agentRuns(alertId),
    enabled: !!alertId,
  });
}
