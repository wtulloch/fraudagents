import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'blue' | 'red' | 'yellow' | 'green' | 'purple';
}

const colorMap = {
  blue:   'bg-blue-500/20 text-blue-400',
  red:    'bg-red-500/20 text-red-400',
  yellow: 'bg-amber-500/20 text-amber-400',
  green:  'bg-green-500/20 text-green-400',
  purple: 'bg-purple-500/20 text-purple-400',
};

export default function MetricCard({ title, value, subtitle, icon: Icon, color = 'blue' }: Props) {
  return (
    <div className="card flex items-center gap-4">
      <div className={clsx('rounded-xl p-3', colorMap[color])}>
        <Icon size={22} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400 truncate">{title}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
        {subtitle && <p className="text-xs text-gray-500 truncate">{subtitle}</p>}
      </div>
    </div>
  );
}
