import { useState } from 'react';
import type { HITLQueueItem } from '../../types';
import { X, Shield, CheckCircle, XCircle, AlertOctagon } from 'lucide-react';
import { useResolveHITL } from '../../hooks/useCases';

interface Props {
  item: HITLQueueItem;
  onClose: () => void;
}

const DECISION_OPTIONS = [
  { value: 'SAR_FILE',       label: 'File SAR',          icon: Shield,       color: 'border-red-700/50 bg-red-900/30 text-red-300' },
  { value: 'CLOSE_NO_ACTION',label: 'Close – No Action', icon: CheckCircle,  color: 'border-green-700/50 bg-green-900/30 text-green-300' },
  { value: 'ESCALATE',       label: 'Escalate',          icon: AlertOctagon, color: 'border-orange-700/50 bg-orange-900/30 text-orange-300' },
];

export default function ReviewPanel({ item, onClose }: Props) {
  const [decision, setDecision] = useState('');
  const [analyst, setAnalyst] = useState('');
  const [notes, setNotes] = useState('');
  const resolve = useResolveHITL();

  const handleResolve = async () => {
    if (!decision || !analyst) return;
    await resolve.mutateAsync({
      itemId: item.id,
      alertId: item.alert_id,
      body: { analyst_username: analyst, decision, notes },
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-base font-bold text-white">HITL Review</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Alert info */}
          <div className="bg-slate-700 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Alert ID</span>
              <span className="font-mono text-gray-300 text-xs">{item.alert_id.slice(0, 12)}…</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Reason</span>
              <span className="font-medium text-gray-200 capitalize">{item.reason.replace(/_/g, ' ')}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Risk Score</span>
              <span className="font-bold text-white">
                {((item.risk_signal?.composite_score ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Priority</span>
              <span className={`font-medium capitalize ${
                item.priority === 'CRITICAL' ? 'text-red-600' :
                item.priority === 'HIGH' ? 'text-orange-600' : 'text-yellow-600'
              }`}>
                {item.priority}
              </span>
            </div>
          </div>

          {/* Risk flags */}
          {item.risk_signal?.all_flags?.length > 0 && (
            <div>
            <p className="text-xs font-medium text-gray-400 mb-2">Risk Flags</p>
            <div className="flex flex-wrap gap-1.5">
              {item.risk_signal.all_flags.map(flag => (
                <span key={flag} className="text-xs bg-red-900/30 text-red-300 px-2 py-0.5 rounded-full">
                    {flag.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Decision selection */}
          <div>
            <p className="text-xs font-medium text-gray-400 mb-2">Analyst Decision</p>
            <div className="space-y-2">
              {DECISION_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setDecision(opt.value)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-sm font-medium transition-all ${
                    decision === opt.value ? opt.color + ' border-current' : 'border-slate-600 text-gray-300 hover:border-slate-500'
                  }`}
                >
                  <opt.icon size={16} />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Analyst name + notes */}
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Your name / badge number *"
              value={analyst}
              onChange={e => setAnalyst(e.target.value)}
              className="w-full border border-slate-600 rounded-lg px-3 py-2.5 text-sm bg-slate-700 text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <textarea
              placeholder="Investigation notes (optional)"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              className="w-full border border-slate-600 rounded-lg px-3 py-2.5 text-sm bg-slate-700 text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-slate-700">
          <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
          <button
            onClick={handleResolve}
            disabled={!decision || !analyst || resolve.isPending}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            {resolve.isPending ? (
              <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Resolving…</>
            ) : (
              <><CheckCircle size={14} /> Resolve</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
