import { useParams } from 'react-router-dom';
import { useAlerts, useAgentRuns, useInvestigateAlert } from '../hooks/useAlerts';
import AgentOutputPanel from '../components/CaseView/AgentOutputPanel';
import SARDraftPanel from '../components/SAR/SARDraftPanel';
import type { AgentOutput, OrchestratorResult } from '../types';
import {
  AlertTriangle, ArrowLeft, Play, FileText, User,
  DollarSign, Tag, Clock, CheckCircle, XCircle, AlertOctagon,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { useState } from 'react';

const OUTCOME_CONFIG = {
  SAR_FILE:       { color: 'bg-red-900/30 border-red-700/50 text-red-300',    icon: FileText,     label: 'SAR Filing Required' },
  ESCALATE:       { color: 'bg-orange-900/30 border-orange-700/50 text-orange-300', icon: AlertOctagon, label: 'Escalated' },
  CLOSE_NO_ACTION:{ color: 'bg-green-900/30 border-green-700/50 text-green-300',  icon: CheckCircle,  label: 'Closed – No Action' },
  PENDING_HITL:   { color: 'bg-amber-900/30 border-amber-700/50 text-amber-300',   icon: Clock,        label: 'Pending HITL Review' },
};

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { data: allAlerts } = useAlerts();
  const { data: agentRuns, isLoading: loadingRuns } = useAgentRuns(caseId ?? '');
  const investigate = useInvestigateAlert();
  const [result, setResult] = useState<OrchestratorResult | null>(null);

  const alert = allAlerts?.find(a => a.id === caseId);
  const outputs: AgentOutput[] = (agentRuns as AgentOutput[] | undefined) ?? result?.agent_outputs ?? [];
  const decision = result?.decision;

  const handleReInvestigate = async () => {
    if (!alert) return;
    const r = await investigate.mutateAsync({
      alertId: alert.id,
      accountId: alert.account_id,
    });
    setResult(r);
  };

  if (!alert && !caseId) {
    return <p className="text-sm text-gray-400 p-8">Case not found.</p>;
  }

  const outcomeConfig = decision?.outcome ? OUTCOME_CONFIG[decision.outcome] : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <button onClick={() => navigate('/alerts')} className="btn-secondary p-2 mt-0.5">
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-white">Case Investigation</h1>
          <p className="text-sm font-mono text-gray-400">Alert ID: {caseId}</p>
        </div>
        {alert && (
          <button
            onClick={handleReInvestigate}
            disabled={investigate.isPending}
            className="btn-primary flex items-center gap-2"
          >
            <Play size={14} />
            {investigate.isPending ? 'Running Agents…' : 'Re-Investigate'}
          </button>
        )}
      </div>

      {/* Alert info */}
      {alert && (
        <div className="card">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-start gap-2">
              <User size={14} className="text-gray-400 mt-0.5" />
              <div>
                <p className="text-xs text-gray-400">Customer</p>
                <p className="text-sm font-medium">{alert.customer_name || alert.account_id}</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Tag size={14} className="text-gray-400 mt-0.5" />
              <div>
                <p className="text-xs text-gray-400">Typology</p>
                <p className="text-sm font-medium">{alert.typology.replace(/_/g, ' ')}</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <DollarSign size={14} className="text-gray-400 mt-0.5" />
              <div>
                <p className="text-xs text-gray-400">Amount</p>
                <p className="text-sm font-medium">
                  {alert.amount != null ? `$${alert.amount.toLocaleString()} ${alert.currency}` : '—'}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Clock size={14} className="text-gray-400 mt-0.5" />
              <div>
                <p className="text-xs text-gray-400">Age</p>
                <p className="text-sm font-medium">
                  {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                </p>
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            {alert.is_pep && <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full font-medium">● PEP</span>}
            {alert.is_swift && <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full font-medium">● SWIFT</span>}
            {alert.is_high_value && <span className="text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full font-medium">● High Value</span>}
            <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium',
              alert.priority === 'CRITICAL' ? 'bg-red-500/20 text-red-300' :
              alert.priority === 'HIGH' ? 'bg-orange-500/20 text-orange-300' :
              alert.priority === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300' :
              'bg-green-500/20 text-green-300'
            )}>
              {alert.priority}
            </span>
          </div>
        </div>
      )}

      {/* Decision outcome banner */}
      {outcomeConfig && (
        <div className={clsx('border rounded-xl px-5 py-4 flex items-start gap-3', outcomeConfig.color)}>
          <outcomeConfig.icon size={20} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold text-sm">{outcomeConfig.label}</p>
            <p className="text-sm mt-0.5 opacity-80">{decision?.rationale}</p>
            <p className="text-xs mt-1 opacity-60">Rule: {decision?.rule_triggered} • Score: {((decision?.risk_score ?? 0) * 100).toFixed(0)}%</p>
          </div>
        </div>
      )}

      {/* Agent investigation in progress */}
      {investigate.isPending && (
        <div className="card flex items-center gap-4 border-blue-700/50 bg-blue-900/20">
          <div className="animate-spin w-6 h-6 border-4 border-blue-700 border-t-blue-400 rounded-full shrink-0" />
          <div>
            <p className="text-sm font-semibold text-blue-300">Agent Investigation Running</p>
            <p className="text-xs text-blue-400">Fan-out to 6 specialist agents via Azure AI Foundry…</p>
          </div>
        </div>
      )}

      {/* Agent outputs */}
      {loadingRuns ? (
        <div className="card animate-pulse h-48" />
      ) : outputs.length > 0 ? (
        <AgentOutputPanel outputs={outputs} />
      ) : !investigate.isPending ? (
        <div className="card text-center py-12">
          <AlertTriangle size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">No agent investigation results yet.</p>
          {alert && (
            <button onClick={handleReInvestigate} className="btn-primary mt-4">
              Run Investigation
            </button>
          )}
        </div>
      ) : null}

      {/* SAR Panel (show when decision requires SAR or there are agent outputs) */}
      {caseId && outputs.length > 0 && (
        <SARDraftPanel caseId={caseId} alertIds={[caseId]} />
      )}
    </div>
  );
}
