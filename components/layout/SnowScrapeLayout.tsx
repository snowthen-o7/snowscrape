'use client';

import React from 'react';
import {
  AppLayout as BaseAppLayout,
  type AppLayoutProps as BaseAppLayoutProps,
  useSidebar,
} from '@snowforge/ui';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  BarChart2,
  Settings,
  Bell,
  Plus,
  Webhook,
} from 'lucide-react';

/**
 * SnowScrape-specific layout wrapper
 *
 * Pre-configures the shared AppLayout with SnowScrape navigation and branding.
 * Use this instead of AppLayout directly in SnowScrape pages.
 */
export function SnowScrapeLayout({ children }: { children: React.ReactNode }) {
  const { collapsed, setCollapsed } = useSidebar();

  const sidebarConfig: BaseAppLayoutProps['sidebar'] = {
    appName: 'SnowScrape',
    logoSrc: '/logo.png',
    homeHref: '/dashboard',
    navItems: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Jobs', href: '/dashboard/jobs', icon: Briefcase },
      { label: 'Templates', href: '/dashboard/templates', icon: FileText },
      { label: 'Analytics', href: '/dashboard/analytics', icon: BarChart2 },
      { label: 'Webhooks', href: '/webhooks', icon: Webhook },
      { label: 'Notifications', href: '/dashboard/notifications', icon: Bell },
      { label: 'Settings', href: '/dashboard/settings', icon: Settings },
    ],
    quickAction: {
      label: 'New Job',
      href: '/dashboard/jobs/new',
      icon: Plus,
    },
  };

  const topNavConfig: BaseAppLayoutProps['topNav'] = {
    appName: 'SnowScrape',
    logoSrc: '/logo.png',
    homeHref: '/dashboard',
    searchPlaceholder: 'Search jobs...',
  };

  return (
    <BaseAppLayout
      sidebar={sidebarConfig}
      topNav={topNavConfig}
      sidebarCollapsed={collapsed}
      onSidebarCollapsedChange={setCollapsed}
    >
      {children}
    </BaseAppLayout>
  );
}

// Re-export as AppLayout for backwards compatibility with existing imports
export { SnowScrapeLayout as AppLayout };
