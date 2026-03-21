import { useState } from 'react';
import { FileText, Send, CheckCircle, XCircle, Clock, Filter } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { sarApi } from '../services/api';
import type { SAR } from '../types';

const STATUS_COLORS: Record<string, string> = {
  DRAFT:          'bg-blue-500/20 text-blue-300',
  APPROVED:       'bg-green-500/20 text-green-300',
  REJECTED:       'bg-red-500/20 text-red-300',
  FILED:          'bg-teal-500/20 text-teal-300',
  PENDING_REVIEW: 'bg-amber-500/20 text-amber-300',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  DRAFT: <Clock size={12} />,
  APPROVED: <CheckCircle size={12} />,
  REJECTED: <XCircle size={12} />,
  FILED: <Send size={12} />,
};

export default function SARPage() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const { data: sars, isLoading } = useQuery({
    queryKey: ['sars', statusFilter],
    queryFn: () => sarApi.list(statusFilter || undefined),
    refetchInterval: 30_000,
  });

  const counts = (sars ?? []).reduce((acc: Record<string, number>, s: SAR) => {
    acc[s.status] = (acc[s.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText size={22} className="text-red-500" /> SAR Management
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Suspicious Activity Reports lifecycle
          </p>
        </div>
      </div>

      {/* Summary counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {['DRAFT', 'PENDING_REVIEW', 'APPROVED', 'FILED'].map(status => (
          <button
            key={status}
            onClick={() => setStatusFilter(s => s === status ? '' : status)}
            className={`card text-left transition-all hover:shadow-md ${
              statusFilter === status ? 'ring-2 ring-blue-500' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-400 capitalize">{status.replace(/_/g, ' ')}</span>
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${STATUS_COLORS[status] || 'bg-slate-700 text-gray-400'}`}>
                {STATUS_ICONS[status]}
              </span>
            </div>
            <p className="text-2xl font-bold text-white">{counts[status] ?? 0}</p>
          </button>
        ))}
      </div>

      {/* Filter indicator */}
      {statusFilter && (
        <div className="flex items-center gap-2 text-sm">
          <Filter size={14} className="text-gray-400" />
          <span className="text-gray-500">Filtered by:</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1 ${STATUS_COLORS[statusFilter]}`}>
            {statusFilter}
            <button onClick={() => setStatusFilter('')} className="ml-1 hover:opacity-70">×</button>
          </span>
        </div>
      )}

      {/* SAR list */}
      {isLoading ? (
        <div className="card animate-pulse h-48" />
      ) : (sars ?? []).length === 0 ? (
        <div className="card text-center py-16">
          <FileText size={36} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">No SARs found{statusFilter ? ` with status "${statusFilter}"` : ''}.</p>
          <p className="text-xs text-gray-400 mt-1">SARs are auto-drafted when agents trigger SAR_FILE decisions.</p>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-slate-700/50 border-b border-slate-700">
              <tr>
                {['SAR ID', 'Case ID', 'Status', 'AI-Drafted', 'Narrative Preview', 'Created', 'Actions'].map(h => (
                  <th key={h} className="text-left text-xs font-semibold text-gray-400 uppercase tracking-wide px-4 py-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {(sars as SAR[]).map(sar => (
                <tr key={sar.id} className="hover:bg-slate-700/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{sar.id.slice(0, 10)}…</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{sar.case_id.slice(0, 10)}…</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full flex items-center gap-1 w-fit ${STATUS_COLORS[sar.status] || 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_ICONS[sar.status]} {sar.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {sar.narrative.drafted_by_agent ? (
                      <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full">AI ✓</span>
                    ) : (
                      <span className="text-xs text-gray-500">Manual</span>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <p className="text-xs text-gray-400 truncate">
                      {sar.narrative.narrative_text?.slice(0, 120) || 'No narrative yet…'}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {formatDistanceToNow(new Date(sar.drafted_at), { addSuffix: true })}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={`/cases/${sar.case_id}`}
                      className="btn-secondary py-1 px-3 text-xs"
                    >
                      View Case
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
