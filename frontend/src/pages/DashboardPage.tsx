import { AlertTriangle, FileText, Users, Activity, Clock, Shield } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import MetricCard from '../components/Dashboard/MetricCard';
import RiskDistribution from '../components/Dashboard/RiskDistribution';
import { useDashboardMetrics, useAuditTrail } from '../hooks/useDashboardMetrics';

export default function DashboardPage() {
  const { data: metrics, isLoading: loadingMetrics } = useDashboardMetrics();
  const { data: audit, isLoading: loadingAudit } = useAuditTrail(20);

  const totalAlerts = metrics?.alerts_by_status?.reduce((s: number, d) => s + d.count, 0) ?? 0;
  const newAlerts = metrics?.alerts_by_status?.find(d => d.status === 'NEW')?.count ?? 0;
  const inProgress = (metrics?.alerts_by_status?.find(d => d.status === 'IN_INVESTIGATION')?.count ?? 0)
    + (metrics?.alerts_by_status?.find(d => d.status === 'PENDING_HITL')?.count ?? 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Fraud Detection Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">Real-time AML &amp; Fraud Monitoring</p>
        </div>
          <span className="flex items-center gap-1.5 text-xs text-green-400 bg-green-900/30 px-3 py-1.5 rounded-full font-medium">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          Agents Active
        </span>
      </div>

      {/* Metric cards */}
      {loadingMetrics ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card animate-pulse h-24 bg-slate-700" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Alerts"
            value={totalAlerts}
            subtitle={`${newAlerts} new`}
            icon={AlertTriangle}
            color="blue"
          />
          <MetricCard
            title="HITL Pending"
            value={metrics?.hitl_pending ?? 0}
            subtitle="Awaiting analyst review"
            icon={Users}
            color="yellow"
          />
          <MetricCard
            title="SARs Filed"
            value={metrics?.total_sars ?? 0}
            subtitle="Suspicious activity reports"
            icon={FileText}
            color="red"
          />
          <MetricCard
            title="In Investigation"
            value={inProgress}
            subtitle="Agents working"
            icon={Activity}
            color="purple"
          />
        </div>
      )}

      {/* Risk distribution */}
      {metrics?.alerts_by_status && (
        <RiskDistribution alertsByStatus={metrics.alerts_by_status} />
      )}

      {/* Model router + audit trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Router */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          </h3>
          {metrics?.model_router ? (
            <dl className="space-y-2">
              {Object.entries(metrics.model_router).map(([task, model]) => (
                <div key={task} className="flex items-center justify-between text-sm">
                  <dt className="text-gray-400 capitalize">{task.replace(/_/g, ' ')}</dt>
                  <dd className="font-medium text-gray-200 bg-slate-700 px-2 py-0.5 rounded text-xs">{model}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-gray-500">Loading router…</p>
          )}
        </div>

        {/* Audit Trail */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <Clock size={14} className="text-gray-500" /> Recent Audit Trail
          </h3>
          {loadingAudit ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="animate-pulse h-8 bg-slate-700 rounded" />
              ))}
            </div>
          ) : (
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {((audit as any[]) ?? []).map((entry: any, i: number) => (
                <div key={i} className="flex items-start gap-2 text-xs py-1.5 border-b border-slate-700">
                  <span className="text-gray-400 shrink-0 font-mono">
                    {entry.timestamp ? formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true }) : '—'}
                  </span>
                  <span className="font-medium text-gray-400 capitalize shrink-0">
                    {(entry.event_type || '').replace(/_/g, ' ')}
                  </span>
                  <span className="text-gray-400 truncate">{entry.alert_id?.slice(0, 8) ?? ''}</span>
                </div>
              ))}
              {!audit?.length && <p className="text-sm text-gray-400">No audit entries yet.</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
