'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboardIcon,
  FileTextIcon,
  BriefcaseIcon,
  BarChart3Icon,
  WebhookIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  PlusIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string | number;
}

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboardIcon,
  },
  {
    label: 'Templates',
    href: '/dashboard/templates',
    icon: FileTextIcon,
  },
  {
    label: 'Jobs',
    href: '/dashboard/jobs',
    icon: BriefcaseIcon,
  },
  {
    label: 'Analytics',
    href: '/dashboard/analytics',
    icon: BarChart3Icon,
  },
  {
    label: 'Webhooks',
    href: '/webhooks',
    icon: WebhookIcon,
  },
];

interface AppSidebarProps {
  className?: string;
}

export function AppSidebar({ className }: AppSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Logo Section */}
      <div className="flex h-16 items-center justify-between px-4 border-b">
        {!collapsed && (
          <Link href="/" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-brand-primary flex items-center justify-center">
              <span className="text-white font-bold text-sm">SS</span>
            </div>
            <span className="font-bold text-lg">SnowScrape</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className={cn('h-8 w-8', collapsed && 'mx-auto')}
        >
          {collapsed ? (
            <ChevronRightIcon className="h-4 w-4" />
          ) : (
            <ChevronLeftIcon className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Quick Action */}
      <div className="p-4">
        {collapsed ? (
          <Button size="icon" className="w-full" asChild>
            <Link href="/dashboard/jobs/new">
              <PlusIcon className="h-4 w-4" />
            </Link>
          </Button>
        ) : (
          <Button className="w-full" asChild>
            <Link href="/dashboard/jobs/new">
              <PlusIcon className="h-4 w-4 mr-2" />
              New Job
            </Link>
          </Button>
        )}
      </div>

      <Separator />

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground',
                collapsed && 'justify-center'
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!collapsed && (
                <span className="flex-1">{item.label}</span>
              )}
              {!collapsed && item.badge && (
                <span className="ml-auto text-xs font-medium">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <Separator />

      {/* Footer - Recent Jobs */}
      {!collapsed && (
        <div className="p-4">
          <p className="text-xs font-medium text-muted-foreground mb-2">
            Recent Jobs
          </p>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground truncate hover:text-foreground cursor-pointer">
              Amazon Product Scraper
            </div>
            <div className="text-xs text-muted-foreground truncate hover:text-foreground cursor-pointer">
              LinkedIn Profiles
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
