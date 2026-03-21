// Shared TypeScript types mirroring backend Pydantic models

export type AlertStatus =
  | 'NEW' | 'ROUTING' | 'IN_INVESTIGATION' | 'PENDING_HITL'
  | 'SAR_DRAFT' | 'SAR_FILED' | 'ESCALATED'
  | 'CLOSED_NO_ACTION' | 'CLOSED_SUSPICIOUS';

export type AlertPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type AlertTypology =
  | 'STRUCTURING' | 'LAYERING' | 'PLACEMENT' | 'INTEGRATION'
  | 'WIRE_FRAUD' | 'SANCTIONS_EVASION' | 'PEP_ACTIVITY'
  | 'HIGH_RISK_JURISDICTION' | 'ADVERSE_MEDIA' | 'TRADE_BASED_ML'
  | 'ACCOUNT_TAKEOVER' | 'IDENTITY_THEFT' | 'CARD_FRAUD'
  | 'SYNTHETIC_IDENTITY' | 'FIRST_PARTY_FRAUD' | 'PAYMENT_FRAUD' | 'UNKNOWN';

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NEGLIGIBLE';
export type DecisionOutcome = 'SAR_FILE' | 'ESCALATE' | 'CLOSE_NO_ACTION' | 'PENDING_HITL';

export interface Alert {
  id: string;
  case_id?: string;
  account_id: string;
  customer_name?: string;
  typology: AlertTypology;
  status: AlertStatus;
  priority: AlertPriority;
  source: string;
  amount?: number;
  currency: string;
  description?: string;
  created_at: string;
  updated_at: string;
  is_pep: boolean;
  is_high_value: boolean;
  is_swift: boolean;
  transaction_ids: string[];
  risk_score?: number;
}

export interface Citation {
  source: string;
  document_id: string;
  relevance_score: number;
  excerpt?: string;
}

export interface AgentOutput {
  agent_name: string;
  alert_id: string;
  run_id: string;
  thread_id?: string;
  model_used: string;
  finding: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  citations: Citation[];
  evidence_summary: string;
  flags: string[];
  groundedness_score?: number;
  is_grounded: boolean;
  latency_ms?: number;
  created_at: string;
  error?: string;
}

export interface RiskSignal {
  alert_id: string;
  composite_score: number;
  risk_level: RiskLevel;
  agent_scores: Record<string, number>;
  all_flags: string[];
  requires_hitl: boolean;
  hitl_reason?: string;
}

export interface DecisionResult {
  alert_id: string;
  outcome: DecisionOutcome;
  rationale: string;
  rule_triggered: string;
  risk_score: number;
  risk_level: RiskLevel;
  requires_sar: boolean;
  auto_sar_eligible: boolean;
}

export interface OrchestratorResult {
  alert_id: string;
  agent_outputs: AgentOutput[];
  risk_signal: RiskSignal;
  decision: DecisionResult;
  total_latency_ms: number;
}

export interface Case {
  id: string;
  alert_ids: string[];
  account_id: string;
  customer_name?: string;
  status: string;
  tier: string;
  risk_score: number;
  composite_flags: string[];
  created_at: string;
  updated_at: string;
}

export interface SAR {
  id: string;
  case_id: string;
  alert_ids: string[];
  status: string;
  narrative: { narrative_text: string; drafted_by_agent: boolean };
  drafted_at: string;
}

export interface HITLQueueItem {
  id: string;
  alert_id: string;
  case_id?: string;
  reason: string;
  priority: string;
  risk_signal: RiskSignal;
  resolved: boolean;
  queued_at: string;
}

export interface DashboardMetrics {
  alerts_by_status: Array<{ status: string; count: number }>;
  total_sars: number;
  hitl_pending: number;
  model_router: Record<string, string>;
}

export interface FeedbackMetrics {
  agent_name: string;
  total: number;
  correct: number;
  accuracy: number | null;
  true_positives: number;
  false_positives: number;
  precision: number | null;
  fine_tune_ready: boolean;
}
