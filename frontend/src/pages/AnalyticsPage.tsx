import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend,
} from 'recharts';
import { BarChart2, TrendingUp, RefreshCw, Brain } from 'lucide-react';
import { useFeedbackMetrics } from '../hooks/useCases';
import { useQuery } from '@tanstack/react-query';
import { agentsApi } from '../services/api';

const AGENT_LABELS: Record<string, string> = {
  adverse_media: 'Adverse Media',
  transaction_pattern: 'Txn Pattern',
  kyc_kyb: 'KYC/KYB',
  sanctions: 'Sanctions',
  fraud: 'Fraud',
  aml: 'AML',
};

export default function AnalyticsPage() {
  const { data: feedbackMetrics, isLoading: loadingFeedback } = useFeedbackMetrics();
  const { data: agentsData } = useQuery({ queryKey: ['agents'], queryFn: agentsApi.list });
  // Backend returns { registered_agents: string[], agent_ids: Record<string,string> }
  const agentList: { id: string; name: string }[] | undefined = agentsData
    ? (agentsData.registered_agents as string[]).map((name: string) => ({
        id: agentsData.agent_ids[name] ?? name,
        name,
      }))
    : undefined;

  const barData = (feedbackMetrics ?? []).map((m: any) => ({
    name: AGENT_LABELS[m.agent_name] || m.agent_name,
    Accuracy: m.accuracy != null ? +(m.accuracy * 100).toFixed(1) : null,
    Precision: m.precision != null ? +(m.precision * 100).toFixed(1) : null,
    Samples: m.total,
  }));

  const radarData = (feedbackMetrics ?? []).map((m: any) => ({
    agent: AGENT_LABELS[m.agent_name] || m.agent_name,
    Accuracy: m.accuracy != null ? +(m.accuracy * 100).toFixed(1) : 0,
    Precision: m.precision != null ? +(m.precision * 100).toFixed(1) : 0,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BarChart2 size={22} className="text-purple-500" /> Analytics &amp; RL Feedback
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Agent performance metrics — feeds reinforcement learning fine-tuning pipeline
        </p>
      </div>

      {/* Foundry agents registry */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          <Brain size={14} className="text-blue-500" /> Foundry Agent Registry
        </h3>
        {agentList ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {agentList.map((agent) => (
              <div key={agent.id} className="bg-slate-700 rounded-lg p-3">
                <p className="text-xs font-semibold text-gray-200 capitalize">
                  {agent.name.replace(/-/g, ' ')}
                </p>
                <p className="text-xs text-gray-400 font-mono mt-0.5">{agent.id}</p>
                <div className="flex items-center gap-1 mt-1.5">
                  <span className="w-2 h-2 bg-green-400 rounded-full" />
                  <span className="text-xs text-green-400">active</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">Loading agents…</p>
        )}
      </div>

      {/* Accuracy / Precision bar chart */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
            <TrendingUp size={14} className="text-green-500" /> Agent Accuracy &amp; Precision
          </h3>
          <span className="text-xs text-gray-500">Based on analyst feedback</span>
        </div>
        {loadingFeedback ? (
          <div className="animate-pulse h-48 bg-slate-700 rounded-lg" />
        ) : barData.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-sm text-gray-400">No feedback data yet.</p>
            <p className="text-xs text-gray-400 mt-1">
              Use the ✓ / ✗ feedback buttons in Case Detail view to train agents.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData} margin={{ top: 5, right: 20, left: -15, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} domain={[0, 100]} unit="%" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }} formatter={(v: any) => `${v}%`} />
              <Legend wrapperStyle={{ color: '#9ca3af' }} />
              <Bar dataKey="Accuracy" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Precision" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Radar chart */}
      {radarData.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Performance Radar</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="agent" tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <Radar name="Accuracy" dataKey="Accuracy" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
              <Radar name="Precision" dataKey="Precision" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.2} />
              <Legend wrapperStyle={{ color: '#9ca3af' }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Fine-tune readiness table */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <RefreshCw size={14} className="text-orange-500" /> Fine-Tune Readiness
        </h3>
        {loadingFeedback ? (
          <div className="animate-pulse h-24 bg-gray-50 rounded-lg" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  {['Agent', 'Samples', 'TP', 'FP', 'Accuracy', 'Precision', 'Ready'].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-gray-400 pb-2 pr-4 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(feedbackMetrics ?? []).map((m: any) => (
                  <tr key={m.agent_name} className="border-b border-slate-700">
                    <td className="py-2 pr-4 font-medium text-gray-200 capitalize">
                      {AGENT_LABELS[m.agent_name] || m.agent_name}
                    </td>
                    <td className="py-2 pr-4 text-gray-400">{m.total}</td>
                    <td className="py-2 pr-4 text-green-600">{m.true_positives}</td>
                    <td className="py-2 pr-4 text-red-600">{m.false_positives}</td>
                    <td className="py-2 pr-4">
                      {m.accuracy != null ? `${(m.accuracy * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      {m.precision != null ? `${(m.precision * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        m.fine_tune_ready
                          ? 'bg-green-500/20 text-green-300'
                          : 'bg-slate-700 text-gray-500'
                      }`}>
                        {m.fine_tune_ready ? '✓ Ready' : 'Not yet'}
                      </span>
                    </td>
                  </tr>
                ))}
                {!(feedbackMetrics as any[])?.length && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-sm text-gray-400">
                      No feedback submitted yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
