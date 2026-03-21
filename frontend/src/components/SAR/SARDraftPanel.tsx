import { useState } from 'react';
import { sarApi } from '../../services/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { SAR } from '../../types';
import { FileText, Send, CheckCircle } from 'lucide-react';

interface Props {
  caseId: string;
  alertIds: string[];
}

export default function SARDraftPanel({ caseId, alertIds }: Props) {
  const qc = useQueryClient();
  const [reviewerName, setReviewerName] = useState('');
  const [comments, setComments] = useState('');

  const { data: sars, isLoading } = useQuery({
    queryKey: ['sars', caseId],
    queryFn: () => sarApi.list(),
    select: (data: SAR[]) => data.filter(s => s.case_id === caseId),
  });

  const draftMutation = useMutation({
    mutationFn: () => sarApi.draft({ case_id: caseId, alert_ids: alertIds }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sars', caseId] }),
  });

  const approveMutation = useMutation({
    mutationFn: ({ sarId, approved }: { sarId: string; approved: boolean }) =>
      sarApi.approve(sarId, caseId, { reviewer_username: reviewerName, approved, comments }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sars', caseId] }),
  });

  const fileMutation = useMutation({
    mutationFn: (sarId: string) => sarApi.file(sarId, caseId, reviewerName || 'compliance_officer'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sars', caseId] }),
  });

  const sar = sars?.[0];

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <FileText size={16} /> SAR Filing
        </h3>
        {!sar && (
          <button
            onClick={() => draftMutation.mutate()}
            disabled={draftMutation.isPending}
            className="btn-primary flex items-center gap-1 text-xs py-1.5"
          >
            <FileText size={12} />
            {draftMutation.isPending ? 'Drafting with AI…' : 'Auto-Draft SAR'}
          </button>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading…</p>}

      {sar && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500">Status:</span>
            <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-medium">
              {sar.status}
            </span>
            {sar.narrative.drafted_by_agent && (
              <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full">AI-drafted</span>
            )}
          </div>

          <div className="bg-slate-700 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-400 mb-2">Narrative (Agent Draft)</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
              {sar.narrative.narrative_text || 'Narrative pending…'}
            </p>
          </div>

          {sar.status === 'DRAFT' && (
            <div className="space-y-2 border-t border-gray-100 pt-3">
              <input
                type="text"
                placeholder="Reviewer name"
                value={reviewerName}
                onChange={e => setReviewerName(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <textarea
                placeholder="Compliance comments (optional)"
                value={comments}
                onChange={e => setComments(e.target.value)}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => approveMutation.mutate({ sarId: sar.id, approved: true })}
                  disabled={!reviewerName || approveMutation.isPending}
                  className="btn-primary flex items-center gap-1 text-xs py-1.5"
                >
                  <CheckCircle size={12} /> Approve
                </button>
                <button
                  onClick={() => approveMutation.mutate({ sarId: sar.id, approved: false })}
                  disabled={!reviewerName || approveMutation.isPending}
                  className="btn-danger flex items-center gap-1 text-xs py-1.5"
                >
                  Reject
                </button>
              </div>
            </div>
          )}

          {sar.status === 'APPROVED' && (
            <button
              onClick={() => fileMutation.mutate(sar.id)}
              disabled={fileMutation.isPending}
              className="btn-primary flex items-center gap-1 text-xs py-1.5"
            >
              <Send size={12} />
              {fileMutation.isPending ? 'Filing…' : 'File with FinCEN'}
            </button>
          )}

          {sar.status === 'FILED' && (
            <p className="text-xs text-green-600 font-medium">✓ SAR filed with FinCEN</p>
          )}
        </div>
      )}
    </div>
  );
}
