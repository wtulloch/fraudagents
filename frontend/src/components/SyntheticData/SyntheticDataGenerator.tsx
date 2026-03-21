import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { syntheticApi } from '../../services/api';
import { Database, Play, CheckCircle, ChevronRight } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const TYPOLOGY_OPTIONS = [
  'STRUCTURING', 'CARD_FRAUD', 'WIRE_FRAUD', 'LAYERING',
  'SANCTIONS_EVASION', 'ACCOUNT_TAKEOVER', 'PAYMENT_FRAUD',
];

export default function SyntheticDataGenerator() {
  const qc = useQueryClient();
  const [nRecords, setNRecords] = useState(100);
  const [fraudRate, setFraudRate] = useState(0.15);
  const [indexToSearch, setIndexToSearch] = useState(true);
  const [scenarioTypology, setScenarioTypology] = useState('');
  const [lastResult, setLastResult] = useState<any>(null);

  const { data: batches } = useQuery({
    queryKey: ['syntheticBatches'],
    queryFn: syntheticApi.batches,
    refetchInterval: 30_000,
  });

  const generateMutation = useMutation({
    mutationFn: () => syntheticApi.generate({
      n_records: nRecords,
      fraud_rate: fraudRate,
      index_to_search: indexToSearch,
    }),
    onSuccess: (data) => {
      setLastResult(data);
      qc.invalidateQueries({ queryKey: ['syntheticBatches'] });
    },
  });

  const scenarioMutation = useMutation({
    mutationFn: () => syntheticApi.scenario(scenarioTypology, 15),
    onSuccess: (data) => {
      setLastResult(data);
      qc.invalidateQueries({ queryKey: ['syntheticBatches'] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Bulk generation */}
      <div className="card space-y-5">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <Database size={14} className="text-blue-500" /> Bulk Synthetic Data Generation
        </h3>

        <div className="space-y-4">
          {/* Records slider */}
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-2">
              <label className="font-medium">Number of Records</label>
              <span className="font-bold text-white">{nRecords}</span>
            </div>
            <input
              type="range" min={10} max={1000} step={10}
              value={nRecords}
              onChange={e => setNRecords(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>10</span><span>1,000</span>
            </div>
          </div>

          {/* Fraud rate slider */}
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-2">
              <label className="font-medium">Fraud Rate</label>
              <span className="font-bold text-white">{(fraudRate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range" min={0} max={1} step={0.01}
              value={fraudRate}
              onChange={e => setFraudRate(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>0%</span><span>100%</span>
            </div>
          </div>

          {/* Index to AI Search toggle */}
          <div className="flex items-center justify-between py-2 border-t border-slate-700">
            <div>
              <p className="text-sm font-medium text-gray-200">Index to Azure AI Search</p>
              <p className="text-xs text-gray-400">Enables RAG-based agent retrieval</p>
            </div>
            <button
              onClick={() => setIndexToSearch(v => !v)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                indexToSearch ? 'bg-blue-600' : 'bg-slate-600'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                indexToSearch ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>

          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {generateMutation.isPending ? (
              <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Generating…</>
            ) : (
              <><Play size={14} /> Generate {nRecords} Records ({(fraudRate * 100).toFixed(0)}% fraud)</>
            )}
          </button>
        </div>
      </div>

      {/* Scenario generator */}
      <div className="card space-y-4">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <ChevronRight size={14} className="text-purple-500" /> Scenario-Based Generation
        </h3>
        <p className="text-xs text-gray-400">Generate a targeted fraud/AML scenario with realistic transaction chains.</p>
        <div className="flex gap-3">
          <select
            value={scenarioTypology}
            onChange={e => setScenarioTypology(e.target.value)}
            className="flex-1 border border-slate-600 rounded-lg px-3 py-2 text-sm bg-slate-700 text-gray-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">Select typology…</option>
            {TYPOLOGY_OPTIONS.map(t => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <button
            onClick={() => scenarioMutation.mutate()}
            disabled={!scenarioTypology || scenarioMutation.isPending}
            className="btn-primary flex items-center gap-1.5 shrink-0"
          >
            <Play size={13} />
            {scenarioMutation.isPending ? 'Loading…' : 'Generate'}
          </button>
        </div>
      </div>

      {/* Last result */}
      {lastResult && (
        <div className="card border-green-800/50 bg-green-900/20">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle size={16} className="text-green-400" />
            <p className="text-sm font-semibold text-green-300">Generation Complete</p>
          </div>
          <pre className="text-xs text-green-300 overflow-x-auto bg-slate-900 rounded-lg p-3 border border-green-800/50 max-h-48">
            {JSON.stringify(lastResult, null, 2)}
          </pre>
        </div>
      )}

      {/* Batch history */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Generation History</h3>
        {!(batches as any[])?.length ? (
          <p className="text-sm text-gray-500">No batches yet.</p>
        ) : (
          <div className="space-y-2">
            {(batches as any[]).map((batch: any) => (
              <div key={batch.id} className="flex items-center justify-between text-sm border-b border-slate-700 pb-2">
                <div>
                  <span className="font-medium text-gray-200">{batch.total_records ?? '?'} records</span>
                  <span className="text-gray-400 ml-2 text-xs">
                    {batch.fraud_rate != null ? `${(batch.fraud_rate * 100).toFixed(0)}% fraud` : ''}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {batch.indexed_to_search && (
                    <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full">Indexed</span>
                  )}
                  <span className="text-xs text-gray-400">
                    {batch.created_at
                      ? formatDistanceToNow(new Date(batch.created_at), { addSuffix: true })
                      : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
