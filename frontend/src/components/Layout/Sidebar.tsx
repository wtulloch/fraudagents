import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Bell, FolderOpen, FileText,
  Users, BarChart3, Database, Shield
} from 'lucide-react';
import clsx from 'clsx';

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/alerts', label: 'Alert Queue', icon: Bell },
  { to: '/hitl', label: 'HITL Review', icon: Users },
  { to: '/sar', label: 'SAR Filing', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/synthetic', label: 'Synthetic Data', icon: Database },
];

export default function Sidebar() {
  return (
    <aside className="w-60 bg-gray-900 flex flex-col flex-shrink-0">
      {/* Logo */}
      <div className="h-16 flex items-center gap-2 px-5 border-b border-gray-700">
        <Shield className="text-blue-400" size={22} />
        <span className="text-white font-semibold text-sm leading-tight">
          Fraud Detection<br />
          <span className="text-gray-400 text-xs font-normal">AI Agent Platform</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white',
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        Azure AI Foundry · MAF v1
      </div>
    </aside>
  );
}
