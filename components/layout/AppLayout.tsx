'use client';

import React, { useState } from 'react';
import { AppSidebar } from './AppSidebar';
import { AppTopNav } from './AppTopNav';
import { cn } from '@/lib/utils';

interface AppLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function AppLayout({ children, className }: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar - Desktop */}
      <div className="hidden md:flex">
        <AppSidebar />
      </div>

      {/* Sidebar - Mobile (Overlay) */}
      {sidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Sidebar */}
          <div className="fixed inset-y-0 left-0 z-50 md:hidden">
            <AppSidebar />
          </div>
        </>
      )}

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <AppTopNav onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

        <main className={cn('flex-1 overflow-y-auto bg-muted/10', className)}>
          <div className="container mx-auto p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
