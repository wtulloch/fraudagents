import clsx from 'clsx';
import type { AgentOutput } from '../../types';
import { CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react';
import { feedbackApi } from '../../services/api';
import { useState } from 'react';

interface Props { outputs: AgentOutput[] }

const AGENT_LABELS: Record<string, string> = {
  adverse_media: 'Adverse Media',
  transaction_pattern: 'Transaction Pattern',
  kyc_kyb: 'KYC / KYB Lookup',
  sanctions: 'Sanctions Matching',
  fraud: 'Fraud Detection',
  aml: 'AML Analysis',
};

const riskColors: Record<string, string> = {
  CRITICAL:   'text-red-400 bg-red-900/30',
  HIGH:       'text-orange-400 bg-orange-900/30',
  MEDIUM:     'text-yellow-400 bg-yellow-900/30',
  LOW:        'text-green-400 bg-green-900/30',
  NEGLIGIBLE: 'text-gray-400 bg-slate-700',
};

export default function AgentOutputPanel({ outputs }: Props) {
  const [submitted, setSubmitted] = useState<Record<string, boolean>>({});

  const submitFeedback = async (output: AgentOutput, correct: boolean) => {
    await feedbackApi.submit({
      alert_id: output.alert_id,
      agent_name: output.agent_name,
      run_id: output.run_id,
      analyst_username: 'analyst',
      is_correct: correct,
    });
    setSubmitted(p => ({ ...p, [output.run_id]: true }));
  };

  if (!outputs.length) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200">Agent Investigation Results</h3>
      {outputs.map(output => (
        <div key={output.run_id} className="border border-slate-700 rounded-xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-slate-700/50 border-b border-slate-700">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-gray-100">
                {AGENT_LABELS[output.agent_name] || output.agent_name}
              </span>
              {output.error ? (
                <XCircle size={14} className="text-red-500" />
              ) : (
                <CheckCircle size={14} className="text-green-500" />
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className={clsx('text-xs font-semibold px-2 py-0.5 rounded-full', riskColors[output.risk_level] || '')}>
                {output.risk_level} · {(output.risk_score * 100).toFixed(0)}%
              </span>
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock size={11} /> {output.latency_ms}ms
              </span>
              <span className="text-xs text-gray-400">{output.model_used}</span>
              {output.groundedness_score != null && (
                <span title="Groundedness score (1-5)" className="text-xs text-indigo-600">
                  G:{output.groundedness_score.toFixed(1)}
                </span>
              )}
            </div>
          </div>

          {/* Body */}
          <div className="px-4 py-3 space-y-3">
            {output.error ? (
              <p className="text-sm text-red-600">{output.error}</p>
            ) : (
              <>
                <p className="text-sm text-gray-300">{output.finding}</p>

                {(output.flags?.length ?? 0) > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {output.flags!.map(f => (
                      <span key={f} className="text-xs bg-red-900/30 text-red-300 border border-red-700/50 px-2 py-0.5 rounded-full">
                        {f}
                      </span>
                    ))}
                  </div>
                )}

                {(output.citations?.length ?? 0) > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-1">Sources</p>
                    <div className="space-y-0.5">
                      {output.citations!.slice(0, 3).map((c, i) => (
                        <p key={i} className="text-xs text-gray-400">
                          [{i + 1}] {c.source} — score {(c.relevance_score * 100).toFixed(0)}%
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* RL Feedback */}
                {!submitted[output.run_id] ? (
                  <div className="flex items-center gap-2 pt-1 border-t border-slate-700">
                    <span className="text-xs text-gray-400">Accurate?</span>
                    <button
                      onClick={() => submitFeedback(output, true)}
                      className="text-xs text-green-400 hover:bg-green-900/30 px-2 py-1 rounded transition-colors flex items-center gap-1"
                    >
                      <CheckCircle size={12} /> Yes
                    </button>
                    <button
                      onClick={() => submitFeedback(output, false)}
                      className="text-xs text-red-400 hover:bg-red-900/30 px-2 py-1 rounded transition-colors flex items-center gap-1"
                    >
                      <XCircle size={12} /> No
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 pt-1 border-t border-slate-700">✓ Feedback recorded</p>
                )}
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
