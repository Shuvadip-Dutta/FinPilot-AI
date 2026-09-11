import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Menu,
  Search,
  LogOut,
  User as UserIcon,
  Settings,
  ChevronDown,
  Sparkles,
  Command,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { SystemHealthIndicator } from '../common/SystemHealthIndicator';

interface TopbarProps {
  onOpenMobile: () => void;
  isSidebarCollapsed: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({ onOpenMobile, isSidebarCollapsed }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleGlobalSearchClick = () => {
    navigate('/app/research');
  };

  return (
    <header
      className={`sticky top-0 z-30 h-16 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 transition-all duration-300 ease-in-out ${
        isSidebarCollapsed ? 'lg:pl-18' : 'lg:pl-64'
      }`}
    >
      <div className="h-full px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Left: Mobile hamburger & branding on mobile */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenMobile}
            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Quick Breadcrumb / Branding context */}
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="text-slate-200 font-semibold">FINPILOT</span>
            <span>/</span>
            <span className="text-cyan-400 font-medium">TERMINAL</span>
          </div>
        </div>

        {/* Center: Global Research / Search shortcut */}
        <div className="flex-1 max-w-md mx-auto hidden md:block">
          <button
            onClick={handleGlobalSearchClick}
            className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-400 hover:border-slate-700 hover:text-slate-300 transition-all cursor-pointer group shadow-xs"
          >
            <div className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-400 transition-colors" />
              <span>Ask FinPilot AI (e.g. &quot;Analyze RELIANCE&quot;)...</span>
            </div>
            <div className="flex items-center gap-1 font-mono text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700/60">
              <Command className="w-3 h-3" />
              <span>K</span>
            </div>
          </button>
        </div>

        {/* Right: API Health Status & User Profile Menu */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <SystemHealthIndicator compact />
          </div>

          {/* User Dropdown */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-colors cursor-pointer select-none"
              aria-expanded={isUserMenuOpen}
              aria-label="User account menu"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500/20 to-indigo-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-300 font-semibold text-xs font-mono">
                {user?.username ? user.username.substring(0, 2).toUpperCase() : 'FP'}
              </div>
              <div className="hidden sm:flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-200 leading-tight">
                  {user?.username || 'Analyst'}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {user?.email || 'Authenticated'}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {/* Dropdown Menu */}
            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-slate-900 border border-slate-800 shadow-xl shadow-slate-950/50 py-1.5 z-50 animate-in fade-in-50 zoom-in-95 duration-100">
                <div className="px-3.5 py-2 border-b border-slate-800">
                  <p className="text-xs font-semibold text-slate-100">{user?.username}</p>
                  <p className="text-[11px] font-mono text-slate-400 truncate">{user?.email}</p>
                  <div className="mt-1 flex items-center gap-1.5 text-[10px] text-cyan-400 font-mono">
                    <Sparkles className="w-3 h-3" />
                    <span>JWT Session Active</span>
                  </div>
                </div>

                <div className="py-1">
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      navigate('/app/profile');
                    }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-300 hover:bg-slate-800/70 hover:text-white transition-colors cursor-pointer"
                  >
                    <UserIcon className="w-4 h-4 text-slate-400" />
                    <span>Analyst Profile</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      navigate('/app/settings');
                    }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-300 hover:bg-slate-800/70 hover:text-white transition-colors cursor-pointer"
                  >
                    <Settings className="w-4 h-4 text-slate-400" />
                    <span>System Settings</span>
                  </button>
                </div>

                <div className="border-t border-slate-800 pt-1">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-rose-400 hover:bg-rose-950/30 hover:text-rose-300 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
