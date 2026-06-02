'use client';

import React, { useState, useEffect } from 'react';
import { UserButton, useUser } from '@clerk/nextjs';
import {
  AppLayout as BaseAppLayout,
  type AppLayoutProps as BaseAppLayoutProps,
  ThemeToggle
} from '@snowforge/ui';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  BarChart2,
  Plus,
  Webhook,
  Settings,
  Trash2,
  Plug,
  Send,
} from 'lucide-react';
import { NotificationCenter } from '@/components/NotificationCenter';
import { DeleteAccountModal } from '@/components/billing/DeleteAccountModal';

/**
 * SnowScrape-specific layout wrapper
 *
 * Pre-configures the shared AppLayout with SnowScrape navigation and branding.
 * Use this instead of AppLayout directly in SnowScrape pages.
 */
export function SnowScrapeLayout({ children }: { children: React.ReactNode }) {
  // @snowforge/ui v4 removed sidebar collapse state — sidebar is always
  // expanded on desktop now. No useSidebar() call needed here.
  const { user } = useUser();
  const [isMounted, setIsMounted] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const sidebarConfig: BaseAppLayoutProps['sidebar'] = {
    appName: 'SnowScrape',
    logoSrc: '/logo.png',
    homeHref: '/dashboard',
    navItems: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Templates', href: '/dashboard/templates', icon: FileText },
      { label: 'Jobs', href: '/dashboard/jobs', icon: Briefcase },
      { label: 'Analytics', href: '/dashboard/analytics', icon: BarChart2 },
      { label: 'Webhooks', href: '/webhooks', icon: Webhook },
      { label: 'Integrations', href: '/dashboard/integrations', icon: Plug },
      { label: 'Destinations', href: '/dashboard/destinations', icon: Send },
    ],
    quickAction: {
      label: 'New Job',
      href: '/dashboard/jobs/new',
      icon: Plus,
    },
  };

  // Right side content for top nav (notifications + user)
  const rightContent = isMounted ? (
    <>
      <NotificationCenter />
      <ThemeToggle />
      <div className="flex items-center gap-3">
        {user && (
          <div className="hidden md:block text-right">
            <p className="text-sm font-medium">{user.fullName || user.username}</p>
            <p className="text-xs text-muted-foreground">
              {user.primaryEmailAddress?.emailAddress}
            </p>
          </div>
        )}
        <UserButton afterSignOutUrl="/">
          <UserButton.MenuItems>
            <UserButton.Link
              label="Settings"
              labelIcon={<Settings className="h-4 w-4" />}
              href="/dashboard/settings"
            />
            <UserButton.Action
              label="Delete account"
              labelIcon={<Trash2 className="h-4 w-4 text-destructive" />}
              onClick={() => setDeleteModalOpen(true)}
            />
          </UserButton.MenuItems>
        </UserButton>
        <DeleteAccountModal
          open={deleteModalOpen}
          onOpenChange={setDeleteModalOpen}
        />
      </div>
    </>
  ) : null;

  const topNavConfig: BaseAppLayoutProps['topNav'] = {
    appName: 'SnowScrape',
    logoSrc: '/logo.png',
    homeHref: '/dashboard',
    searchPlaceholder: 'Search jobs, templates...',
    rightContent,
  };

  return (
    <BaseAppLayout
      sidebar={sidebarConfig}
      topNav={topNavConfig}
    >
      {children}
    </BaseAppLayout>
  );
}

// Re-export as AppLayout for backwards compatibility with existing imports
export { SnowScrapeLayout as AppLayout };
