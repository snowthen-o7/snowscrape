'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { UserButton, useUser } from '@clerk/nextjs';
import { Button, cn } from '@snowforge/ui';

interface MarketingLayoutProps {
  children: React.ReactNode;
  className?: string;
}

const navItems = [
  { label: 'Features', href: '/features' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Docs', href: '/docs' },
  { label: 'Blog', href: '/blog' },
];

export function MarketingLayout({ children, className }: MarketingLayoutProps) {
  const pathname = usePathname();
  const { isSignedIn } = useUser();

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <Image
              src="/logo.png"
              alt="SnowForge"
              width={32}
              height={32}
              className="rounded-lg"
            />
            <span className="font-bold text-xl">SnowScrape</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-primary',
                  pathname === item.href
                    ? 'text-foreground'
                    : 'text-muted-foreground'
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Auth Actions */}
          <div className="flex items-center gap-4">
            {isSignedIn ? (
              <>
                <Button asChild variant="ghost">
                  <Link href="/dashboard">Dashboard</Link>
                </Button>
                <UserButton afterSignOutUrl="/" />
              </>
            ) : (
              <>
                <Button asChild variant="ghost">
                  <Link href="/sign-in">Sign In</Link>
                </Button>
                <Button asChild>
                  <Link href="/sign-up">Get Started</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className={cn('flex-1', className)}>
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t bg-muted/40">
        <div className="container py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="space-y-4">
              <Link href="/" className="flex items-center space-x-2">
                <Image
                  src="/logo.png"
                  alt="SnowForge"
                  width={32}
                  height={32}
                  className="rounded-lg"
                />
                <span className="font-bold text-lg">SnowScrape</span>
              </Link>
              <p className="text-sm text-muted-foreground">
                Powerful web scraping, simplified. Extract data from any website with ease.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link href="/features" className="hover:text-foreground">Features</Link></li>
                <li><Link href="/pricing" className="hover:text-foreground">Pricing</Link></li>
                <li><Link href="/docs" className="hover:text-foreground">Documentation</Link></li>
                <li><Link href="/templates" className="hover:text-foreground">Templates</Link></li>
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link href="/about" className="hover:text-foreground">About</Link></li>
                <li><Link href="/blog" className="hover:text-foreground">Blog</Link></li>
                <li><Link href="/contact" className="hover:text-foreground">Contact</Link></li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link href="/privacy-policy" className="hover:text-foreground">Privacy Policy</Link></li>
                <li><Link href="/terms-conditions" className="hover:text-foreground">Terms of Service</Link></li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t text-center text-sm text-muted-foreground">
            <p>&copy; {new Date().getFullYear()} SnowScrape. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
