import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  BrainCircuit,
  History,
  FileText,
  TrendingUp,
  PieChart,
  ShieldAlert,
  Sliders,
  GitFork,
  Bell,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { NavItem } from '../../types/common';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const NAV_ITEMS: NavItem[] = [
  { name: 'Dashboard', href: '/app/dashboard', icon: LayoutDashboard, exact: true },
  { name: 'Research', href: '/app/research', icon: BrainCircuit, badge: 'Agentic', exact: true },
  { name: 'Research History', href: '/app/research/history', icon: History, exact: true },
  { name: 'Documents', href: '/app/documents', icon: FileText, badge: 'RAG', exact: true },
  { name: 'Markets', href: '/app/markets', icon: TrendingUp, exact: true },
  { name: 'Portfolio', href: '/app/portfolio', icon: PieChart },
  { name: 'Alerts', href: '/app/alerts', icon: Bell },
  { name: 'Risk', href: '/app/risk', icon: ShieldAlert },
  { name: 'Optimization', href: '/app/optimization', icon: Sliders },
  { name: 'Backtest', href: '/app/backtest', icon: GitFork },
  { name: 'Profile', href: '/app/profile', icon: User, exact: true },
  { name: 'Settings', href: '/app/settings', icon: Settings, exact: true },
];


export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs lg:hidden transition-opacity"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-surface border-r border-border-theme transition-all duration-300 ease-in-out ${
          isCollapsed ? 'w-18' : 'w-64'
        } ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Sidebar Header / Brand Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-border-theme shrink-0">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-accent-primary flex items-center justify-center shrink-0 shadow-sm">
              <Sparkles className="w-5 h-5 text-accent-text stroke-[2.5]" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col truncate">
                <span className="text-base font-extrabold tracking-tight text-text-primary flex items-center gap-1.5">
                  FINPILOT <span className="text-accent-primary font-mono text-xs font-semibold px-1.5 py-0.5 rounded-sm bg-accent-soft border border-accent-primary/30">AI</span>
                </span>
                <span className="text-[10px] uppercase font-mono tracking-wider text-text-muted truncate">
                  Research & Quant Engine
                </span>
              </div>
            )}
          </div>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-secondary transition-colors cursor-pointer"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          <div className="px-3 pb-2">
            {!isCollapsed ? (
              <p className="text-[11px] font-semibold text-text-muted uppercase tracking-wider font-mono">
                Platform Navigation
              </p>
            ) : (
              <div className="h-2" />
            )}
          </div>

          <nav className="space-y-1" aria-label="Main Navigation">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  end={item.exact}
                  onClick={() => {
                    if (isMobileOpen) {
                      onCloseMobile();
                    }
                  }}
                  className={({ isActive }) =>
                    `group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                      isActive
                        ? 'bg-accent-soft text-accent-primary border border-accent-primary shadow-xs font-semibold ring-1 ring-accent-primary/20'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-secondary border border-transparent'
                    }`
                  }
                  title={isCollapsed ? item.name : undefined}
                >
                  <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
                  {!isCollapsed && (
                    <span className="flex-1 truncate">{item.name}</span>
                  )}
                  {!isCollapsed && item.badge && (
                    <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded-full bg-accent-soft text-accent-primary border border-accent-primary/40">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer — Architecture Pill & Version */}
        <div className="p-3 border-t border-border-theme bg-surface-secondary/40 shrink-0">
          {!isCollapsed ? (
            <div className="p-3 rounded-lg bg-surface border border-border-theme text-xs shadow-xs">
              <div className="flex items-center justify-between text-text-primary font-mono text-[11px] mb-1">
                <span>DJANGO REST</span>
                <span className="text-status-positive">v1 API</span>
              </div>
              <p className="text-[11px] text-text-muted leading-tight">
                Deterministic Quant & LangGraph Agent Engine
              </p>
            </div>
          ) : (
            <div className="flex justify-center" title="Django REST Framework API">
              <div className="w-8 h-8 rounded-lg bg-surface border border-border-theme flex items-center justify-center text-text-muted text-xs font-mono">
                v1
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
