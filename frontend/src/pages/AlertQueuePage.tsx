import { useState } from 'react';
import { AlertTriangle, RefreshCw, Plus } from 'lucide-react';
import { useAlerts } from '../hooks/useAlerts';
import AlertTable from '../components/AlertQueue/AlertTable';
import type { AlertStatus } from '../types';

const STATUS_TABS: { label: string; value?: AlertStatus }[] = [
  { label: 'All' },
  { label: 'New', value: 'NEW' },
  { label: 'Investigating', value: 'IN_INVESTIGATION' },
  { label: 'HITL Pending', value: 'PENDING_HITL' },
  { label: 'SAR Draft', value: 'SAR_DRAFT' },
  { label: 'Escalated', value: 'ESCALATED' },
  { label: 'Closed', value: 'CLOSED_NO_ACTION' },
];

export default function AlertQueuePage() {
  const [activeTab, setActiveTab] = useState<AlertStatus | undefined>(undefined);
  const { data: alerts, isLoading, isFetching, refetch } = useAlerts(activeTab);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <AlertTriangle size={22} className="text-orange-500" /> Alert Queue
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {alerts?.length ?? 0} alerts {activeTab ? `(${activeTab})` : '(all statuses)'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="btn-secondary flex items-center gap-1.5"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 border-b border-slate-700">
        {STATUS_TABS.map(tab => (
          <button
            key={tab.label}
            onClick={() => setActiveTab(tab.value)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.value
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="card text-center py-12">
          <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-3" />
          <p className="text-sm text-gray-400">Loading alerts…</p>
        </div>
      ) : (
        <AlertTable alerts={alerts ?? []} />
      )}
    </div>
  );
}
