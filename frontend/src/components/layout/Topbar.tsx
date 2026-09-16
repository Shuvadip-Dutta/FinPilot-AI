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
import { ThemeToggle } from '../common/ThemeToggle';

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
      className={`sticky top-0 z-30 h-16 bg-surface/85 backdrop-blur-md border-b border-border-theme transition-all duration-300 ease-in-out ${
        isSidebarCollapsed ? 'lg:pl-18' : 'lg:pl-64'
      }`}
    >
      <div className="h-full px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Left: Mobile hamburger & branding on mobile */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenMobile}
            className="lg:hidden p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Quick Breadcrumb / Branding context */}
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-text-muted">
            <span className="text-text-primary font-semibold">FINPILOT</span>
            <span>/</span>
            <span className="text-accent-primary font-medium">TERMINAL</span>
          </div>
        </div>

        {/* Center: Global Research / Search shortcut */}
        <div className="flex-1 max-w-md mx-auto hidden md:block">
          <button
            onClick={handleGlobalSearchClick}
            className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-lg bg-surface-secondary/70 border border-border-theme text-xs text-text-muted hover:border-accent-primary/40 hover:text-text-secondary transition-all cursor-pointer group shadow-xs"
          >
            <div className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5 text-text-muted group-hover:text-accent-primary transition-colors" />
              <span>Ask FinPilot AI (e.g. &quot;Analyze RELIANCE&quot;)...</span>
            </div>
            <div className="flex items-center gap-1 font-mono text-[10px] text-text-muted bg-surface px-1.5 py-0.5 rounded border border-border-theme">
              <Command className="w-3 h-3" />
              <span>K</span>
            </div>
          </button>
        </div>

        {/* Right: API Health Status, Theme Toggle & User Profile Menu */}
        <div className="flex items-center gap-2.5">
          <div className="hidden sm:block">
            <SystemHealthIndicator compact />
          </div>

          {/* Theme Toggle (Light / Dark) */}
          <ThemeToggle compact />

          {/* User Dropdown */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-surface-secondary border border-transparent hover:border-border-theme transition-colors cursor-pointer select-none"
              aria-expanded={isUserMenuOpen}
              aria-label="User account menu"
            >
              <div className="w-8 h-8 rounded-lg bg-accent-soft border border-accent-primary/30 flex items-center justify-center text-accent-primary font-semibold text-xs font-mono">
                {user?.username ? user.username.substring(0, 2).toUpperCase() : 'FP'}
              </div>
              <div className="hidden sm:flex flex-col text-left">
                <span className="text-xs font-semibold text-text-primary leading-tight">
                  {user?.username || 'Analyst'}
                </span>
                <span className="text-[10px] text-text-muted font-mono">
                  {user?.email || 'Authenticated'}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
            </button>

            {/* Dropdown Menu */}
            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-surface-elevated border border-border-theme shadow-card-hover py-1.5 z-50 animate-in fade-in-50 zoom-in-95 duration-100">
                <div className="px-3.5 py-2 border-b border-border-subtle">
                  <p className="text-xs font-semibold text-text-primary">{user?.username}</p>
                  <p className="text-[11px] font-mono text-text-muted truncate">{user?.email}</p>
                  <div className="mt-1 flex items-center gap-1.5 text-[10px] text-accent-primary font-mono">
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
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-text-secondary hover:bg-surface-secondary hover:text-text-primary transition-colors cursor-pointer"
                  >
                    <UserIcon className="w-4 h-4 text-text-muted" />
                    <span>Analyst Profile</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      navigate('/app/settings');
                    }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-text-secondary hover:bg-surface-secondary hover:text-text-primary transition-colors cursor-pointer"
                  >
                    <Settings className="w-4 h-4 text-text-muted" />
                    <span>System Settings</span>
                  </button>
                </div>

                <div className="border-t border-border-subtle pt-1">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-status-negative hover:bg-status-negative-soft transition-colors cursor-pointer"
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
