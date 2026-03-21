import { useState } from 'react';
import { Users, Clock, CheckCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useHITLQueue } from '../hooks/useCases';
import ReviewPanel from '../components/HITL/ReviewPanel';
import type { HITLQueueItem } from '../types';

export default function HITLPage() {
  const [showResolved, setShowResolved] = useState(false);
  const { data: queue, isLoading } = useHITLQueue(showResolved);
  const [selected, setSelected] = useState<HITLQueueItem | null>(null);

  const pending = (queue ?? []).filter(i => !i.resolved);
  const resolved = (queue ?? []).filter(i => i.resolved);
  const items = showResolved ? resolved : pending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Users size={22} className="text-yellow-500" /> Human-in-the-Loop Review
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {pending.length} pending review{pending.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => setShowResolved(v => !v)}
          className="btn-secondary flex items-center gap-2"
        >
          {showResolved ? <Clock size={14} /> : <CheckCircle size={14} />}
          {showResolved ? 'Show Pending' : 'Show Resolved'}
        </button>
      </div>

      {isLoading ? (
        <div className="card animate-pulse h-48" />
      ) : items.length === 0 ? (
        <div className="card text-center py-16">
          <CheckCircle size={36} className="mx-auto text-green-400 mb-3" />
          <p className="text-sm font-medium text-gray-500">
            {showResolved ? 'No resolved items.' : 'No items pending review — queue is clear!'}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-slate-700/50 border-b border-slate-700">
              <tr>
                {['Alert ID', 'Reason', 'Risk Score', 'Priority', 'Queued', 'Status', 'Action'].map(h => (
                  <th key={h} className="text-left text-xs font-semibold text-gray-400 uppercase tracking-wide px-4 py-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map(item => (
                <tr key={item.id} className="hover:bg-slate-700/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {item.alert_id.slice(0, 10)}…
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-amber-500/20 text-amber-300 text-xs px-2 py-0.5 rounded-full font-medium capitalize">
                      {item.reason.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-slate-600 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-gradient-to-r from-yellow-400 to-red-500"
                          style={{ width: `${((item.risk_signal?.composite_score ?? 0) * 100).toFixed(0)}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold text-gray-200">
                        {((item.risk_signal?.composite_score ?? 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium capitalize ${
                      item.priority === 'CRITICAL' ? 'text-red-600' :
                      item.priority === 'HIGH' ? 'text-orange-600' : 'text-yellow-600'
                    }`}>
                      {item.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {formatDistanceToNow(new Date(item.queued_at), { addSuffix: true })}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      item.resolved
                        ? 'bg-green-500/20 text-green-300'
                        : 'bg-amber-500/20 text-amber-300'
                    }`}>
                      {item.resolved ? 'Resolved' : 'Pending'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {!item.resolved && (
                      <button
                        onClick={() => setSelected(item)}
                        className="btn-primary py-1.5 text-xs"
                      >
                        Review
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <ReviewPanel item={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
