import React from 'react';

export interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  exact?: boolean;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export type StatusVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
