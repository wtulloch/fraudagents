import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';

interface Props {
  alertsByStatus: Array<{ status: string; count: number }>;
}

const STATUS_COLORS: Record<string, string> = {
  NEW: '#3b82f6',
  IN_INVESTIGATION: '#8b5cf6',
  PENDING_HITL: '#f59e0b',
  SAR_DRAFT: '#f97316',
  SAR_FILED: '#10b981',
  ESCALATED: '#ef4444',
  CLOSED_NO_ACTION: '#6b7280',
  CLOSED_SUSPICIOUS: '#14b8a6',
};

export default function RiskDistribution({ alertsByStatus }: Props) {
  const data = alertsByStatus.map(d => ({
    ...d,
    fill: STATUS_COLORS[d.status] || '#94a3b8',
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Pie */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Alerts by Status</h3>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={80} label={{ fill: '#9ca3af', fontSize: 11 }}>
              {data.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }} />
            <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Bar */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Alert Volume by Status</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="status" tick={{ fontSize: 10, fill: '#9ca3af' }} interval={0} angle={-25} textAnchor="end" height={50} />
            <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
