import { Bell, RefreshCw } from 'lucide-react';
import { useHITLQueue } from '../../hooks/useCases';

export default function Header() {
  const { data: queue } = useHITLQueue(false);
  const pending = queue?.length ?? 0;

  return (
    <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6 flex-shrink-0">
      <h1 className="text-gray-300 text-sm font-medium">
        Fraud &amp; AML Detection — Multi-Agent Platform
      </h1>
      <div className="flex items-center gap-4">
        <button
          onClick={() => window.location.reload()}
          className="text-gray-400 hover:text-gray-200 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={16} />
        </button>
        <button className="relative text-gray-400 hover:text-gray-200 transition-colors">
          <Bell size={18} />
          {pending > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center leading-none">
              {pending > 9 ? '9+' : pending}
            </span>
          )}
        </button>
        <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-semibold">
          A
        </div>
      </div>
    </header>
  );
}
