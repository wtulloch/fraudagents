import axios from 'axios';
import type {
  Alert, AlertStatus, OrchestratorResult, Case,
  SAR, HITLQueueItem, DashboardMetrics, FeedbackMetrics
} from '../types';

const http = axios.create({ baseURL: '/api', timeout: 120_000 });

// ── Alerts ────────────────────────────────────────────────────────────────────
export const alertsApi = {
  list: (status?: AlertStatus, limit = 50) =>
    http.get<Alert[]>('/alerts/', { params: { status, limit } }).then(r => r.data),

  get: (alertId: string, accountId: string) =>
    http.get<Alert>(`/alerts/${alertId}`, { params: { account_id: accountId } }).then(r => r.data),

  create: (body: Partial<Alert>) =>
    http.post<Alert>('/alerts/', body).then(r => r.data),

  update: (alertId: string, accountId: string, body: Partial<Alert>) =>
    http.patch<Alert>(`/alerts/${alertId}`, body, { params: { account_id: accountId } }).then(r => r.data),

  investigate: (alertId: string, accountId: string, sessionId?: string) =>
    http.post<OrchestratorResult>(`/alerts/${alertId}/investigate`, {
      account_id: accountId, session_id: sessionId
    }).then(r => r.data),

  agentRuns: (alertId: string) =>
    http.get<object[]>(`/alerts/${alertId}/agent-runs`).then(r => r.data),
};

// ── Cases ─────────────────────────────────────────────────────────────────────
export const casesApi = {
  list: (status?: string) =>
    http.get<Case[]>('/cases/', { params: { status } }).then(r => r.data),

  get: (caseId: string, accountId: string) =>
    http.get<Case>(`/cases/${caseId}`, { params: { account_id: accountId } }).then(r => r.data),

  create: (body: Partial<Case>) =>
    http.post<Case>('/cases/', body).then(r => r.data),

  addNote: (caseId: string, accountId: string, note: { author: string; content: string }) =>
    http.post(`/cases/${caseId}/notes`, note, { params: { account_id: accountId } }).then(r => r.data),

  updateStatus: (caseId: string, accountId: string, status: string) =>
    http.patch(`/cases/${caseId}/status`, null, { params: { account_id: accountId, status } }).then(r => r.data),
};

// ── SAR ───────────────────────────────────────────────────────────────────────
export const sarApi = {
  list: (status?: string) =>
    http.get<SAR[]>('/sar/', { params: { status } }).then(r => r.data),

  draft: (body: { case_id: string; alert_ids: string[]; filing_type?: string; additional_context?: string }) =>
    http.post<SAR>('/sar/draft', body).then(r => r.data),

  get: (sarId: string, caseId: string) =>
    http.get<SAR>(`/sar/${sarId}`, { params: { case_id: caseId } }).then(r => r.data),

  approve: (sarId: string, caseId: string, body: { reviewer_username: string; approved: boolean; comments?: string }) =>
    http.post(`/sar/${sarId}/approve`, body, { params: { case_id: caseId } }).then(r => r.data),

  file: (sarId: string, caseId: string, filedBy: string) =>
    http.post(`/sar/${sarId}/file`, null, { params: { case_id: caseId, filed_by: filedBy } }).then(r => r.data),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboardApi = {
  metrics: () => http.get<DashboardMetrics>('/dashboard/metrics').then(r => r.data),
  auditTrail: (limit = 50) => http.get<object[]>('/dashboard/audit-trail', { params: { limit } }).then(r => r.data),
};

// ── HITL ──────────────────────────────────────────────────────────────────────
export const hitlApi = {
  queue: (resolved = false) =>
    http.get<HITLQueueItem[]>('/hitl/queue', { params: { resolved } }).then(r => r.data),

  resolve: (itemId: string, alertId: string, body: { analyst_username: string; decision: string; notes?: string }) =>
    http.post(`/hitl/queue/${itemId}/resolve`, body, { params: { alert_id: alertId } }).then(r => r.data),
};

// ── Synthetic Data ────────────────────────────────────────────────────────────
export const syntheticApi = {
  generate: (body: { n_records: number; fraud_rate: number; index_to_search: boolean }) =>
    http.post('/synthetic/generate', body).then(r => r.data),

  batches: () => http.get('/synthetic/batches').then(r => r.data),

  scenario: (typology: string, nTxn = 10) =>
    http.get('/synthetic/scenario/' + typology, { params: { n_transactions: nTxn } }).then(r => r.data),
};

// ── Feedback ──────────────────────────────────────────────────────────────────
export const feedbackApi = {
  submit: (body: {
    alert_id: string; agent_name: string; run_id: string;
    analyst_username: string; is_correct: boolean;
    actual_risk_score?: number; actual_typology?: string; notes?: string;
  }) => http.post('/feedback/submit', body).then(r => r.data),

  allMetrics: () => http.get<FeedbackMetrics[]>('/feedback/metrics').then(r => r.data),

  agentMetrics: (agentName: string) =>
    http.get<FeedbackMetrics>(`/feedback/metrics/${agentName}`).then(r => r.data),
};

// ── Agents ────────────────────────────────────────────────────────────────────
export const agentsApi = {
  list: () => http.get('/agents/').then(r => r.data),
  modelRouter: () => http.get('/agents/model-router').then(r => r.data),
  reload: () => http.post('/agents/reload').then(r => r.data),
};
