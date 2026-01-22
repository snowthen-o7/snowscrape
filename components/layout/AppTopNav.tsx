'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { UserButton, useUser } from '@clerk/nextjs';
import { SearchIcon, MenuIcon, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { NotificationCenter } from '@/components/NotificationCenter';
import { cn } from '@/lib/utils';

interface AppTopNavProps {
  className?: string;
  onMenuClick?: () => void;
}

export function AppTopNav({ className, onMenuClick }: AppTopNavProps) {
  const { user } = useUser();

  return (
    <header
      className={cn(
        'sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background px-6',
        className
      )}
    >
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onMenuClick}
      >
        <MenuIcon className="h-5 w-5" />
      </Button>

      {/* Logo for mobile */}
      <Link href="/" className="flex items-center space-x-2 md:hidden">
        <Image
          src="/logo.png"
          alt="SnowForge"
          width={32}
          height={32}
          className="rounded-lg"
        />
      </Link>

      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search jobs, templates..."
            className="pl-10 pr-9 w-full"
          />
          <TooltipProvider delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <HelpCircle className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <p>Search by job name, template name, or source URL</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <NotificationCenter />

        {/* User menu */}
        <div className="flex items-center gap-3">
          {user && (
            <div className="hidden md:block text-right">
              <p className="text-sm font-medium">{user.fullName || user.username}</p>
              <p className="text-xs text-muted-foreground">
                {user.primaryEmailAddress?.emailAddress}
              </p>
            </div>
          )}
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  );
}
