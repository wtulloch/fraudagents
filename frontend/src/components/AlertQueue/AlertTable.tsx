import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Eye } from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import type { Alert } from '../../types';
import { useInvestigateAlert } from '../../hooks/useAlerts';

interface Props { alerts: Alert[] }

const priorityColors = {
  CRITICAL: 'risk-badge-critical',
  HIGH: 'risk-badge-high',
  MEDIUM: 'risk-badge-medium',
  LOW: 'risk-badge-low',
};

const statusColors: Record<string, string> = {
  NEW:              'bg-blue-500/20 text-blue-300',
  IN_INVESTIGATION: 'bg-purple-500/20 text-purple-300',
  PENDING_HITL:     'bg-amber-500/20 text-amber-300',
  SAR_DRAFT:        'bg-orange-500/20 text-orange-300',
  ESCALATED:        'bg-red-500/20 text-red-300',
  CLOSED_NO_ACTION: 'bg-slate-700 text-gray-400',
  CLOSED_SUSPICIOUS:'bg-teal-500/20 text-teal-300',
};

export default function AlertTable({ alerts }: Props) {
  const navigate = useNavigate();
  const investigate = useInvestigateAlert();
  const [investigating, setInvestigating] = useState<string | null>(null);

  const handleInvestigate = async (alert: Alert) => {
    setInvestigating(alert.id);
    try {
      const result = await investigate.mutateAsync({
        alertId: alert.id,
        accountId: alert.account_id,
      });
      navigate(`/cases/${result.alert_id}`);
    } finally {
      setInvestigating(null);
    }
  };

  if (!alerts.length) {
    return (
      <div className="card text-center py-12 text-gray-400 text-sm">
        No alerts found.
      </div>
    );
  }

  return (
    <div className="card overflow-hidden p-0">
      <table className="w-full text-sm">
        <thead className="bg-slate-700/50 border-b border-slate-700">
          <tr>
            {['Alert ID', 'Customer', 'Typology', 'Amount', 'Priority', 'Status', 'Age', 'Actions'].map(h => (
              <th key={h} className="text-left text-xs font-semibold text-gray-400 uppercase tracking-wide px-4 py-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {alerts.map(alert => (
            <tr key={alert.id} className="hover:bg-slate-700/50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{alert.id.slice(0, 8)}…</td>
              <td className="px-4 py-3 font-medium text-gray-100">{alert.customer_name || alert.account_id.slice(0, 10)}</td>
              <td className="px-4 py-3">
                <span className="bg-blue-500/20 text-blue-300 text-xs font-medium px-2 py-0.5 rounded">
                  {alert.typology.replace(/_/g, ' ')}
                </span>
              </td>
              <td className="px-4 py-3 font-medium">
                {alert.amount != null ? `$${alert.amount.toLocaleString()}` : '—'}
                {(alert.is_pep || alert.is_swift || alert.is_high_value) && (
                  <div className="flex gap-1 mt-0.5">
                    {alert.is_pep && <span className="text-xs bg-purple-500/20 text-purple-300 px-1 rounded">PEP</span>}
                    {alert.is_swift && <span className="text-xs bg-indigo-500/20 text-indigo-300 px-1 rounded">SWIFT</span>}
                    {alert.is_high_value && <span className="text-xs bg-red-500/20 text-red-300 px-1 rounded">HV</span>}
                  </div>
                )}
              </td>
              <td className="px-4 py-3">
                <span className={priorityColors[alert.priority] || 'risk-badge-low'}>
                  {alert.priority}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', statusColors[alert.status] || 'bg-gray-100 text-gray-600')}>
                  {alert.status.replace(/_/g, ' ')}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-gray-400">
                {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleInvestigate(alert)}
                    disabled={investigating === alert.id}
                    className="btn-primary flex items-center gap-1 py-1.5 text-xs"
                    title="Run agent investigation"
                  >
                    <Play size={12} />
                    {investigating === alert.id ? 'Running…' : 'Investigate'}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
