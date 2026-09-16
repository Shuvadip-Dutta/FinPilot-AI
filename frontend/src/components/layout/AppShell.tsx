import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { ShieldCheck } from 'lucide-react';

export const AppShell: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-app text-text-primary flex flex-col selection:bg-accent-soft selection:text-accent-primary">
      {/* Sidebar Navigation */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Topbar */}
      <Topbar
        onOpenMobile={() => setIsMobileMenuOpen(true)}
        isSidebarCollapsed={isSidebarCollapsed}
      />

      {/* Main Content Area */}
      <main
        className={`flex-1 flex flex-col transition-all duration-300 ease-in-out ${
          isSidebarCollapsed ? 'lg:pl-18' : 'lg:pl-64'
        }`}
      >
        <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </div>

        {/* Subtle Regulatory Compliance Disclaimer Footer */}
        <footer className="border-t border-border-theme bg-surface/60 py-3 px-6 text-center">
          <div className="flex items-center justify-center gap-2 text-[11px] text-text-muted max-w-3xl mx-auto">
            <ShieldCheck className="w-3.5 h-3.5 text-text-muted shrink-0" />
            <span>
              FinPilot AI provides research and decision-support information. It does not execute trades or guarantee investment outcomes.
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
};
