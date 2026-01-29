/**
 * Documentation Page Layout
 * Shared layout for all documentation pages with sidebar navigation
 */

'use client';

import { MarketingLayout } from '@/components/layout';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@snowforge/ui';
import { ChevronRight } from 'lucide-react';

interface DocSection {
  title: string;
  items: { title: string; href: string }[];
}

const docSections: DocSection[] = [
  {
    title: 'Getting Started',
    items: [
      { title: 'Introduction', href: '/docs/getting-started' },
      { title: 'Creating Jobs', href: '/docs/creating-jobs' },
      { title: 'Exporting Data', href: '/docs/exporting-data' },
    ],
  },
  {
    title: 'Core Concepts',
    items: [
      { title: 'Understanding Jobs', href: '/docs/jobs' },
      { title: 'Query Types', href: '/docs/queries' },
      { title: 'Scheduling', href: '/docs/scheduling' },
      { title: 'Templates', href: '/docs/templates' },
    ],
  },
  {
    title: 'API Reference',
    items: [
      { title: 'Authentication', href: '/docs/api/authentication' },
      { title: 'Jobs API', href: '/docs/api/jobs' },
      { title: 'Webhooks', href: '/docs/api/webhooks' },
      { title: 'Rate Limits', href: '/docs/api/rate-limits' },
    ],
  },
  {
    title: 'Advanced Features',
    items: [
      { title: 'JavaScript Rendering', href: '/docs/javascript-rendering' },
      { title: 'Proxy Rotation', href: '/docs/proxy-rotation' },
      { title: 'Custom Headers', href: '/docs/custom-headers' },
      { title: 'Error Handling', href: '/docs/error-handling' },
    ],
  },
];

interface DocLayoutProps {
  children: React.ReactNode;
  title: string;
  description?: string;
}

export function DocLayout({ children, title, description }: DocLayoutProps) {
  const pathname = usePathname();

  return (
    <MarketingLayout>
      <div className="mx-auto max-w-7xl px-6 lg:px-8 py-12">
        <div className="flex flex-col lg:flex-row gap-12">
          {/* Sidebar Navigation */}
          <aside className="lg:w-64 flex-shrink-0">
            <nav className="sticky top-24 space-y-6">
              {docSections.map((section) => (
                <div key={section.title}>
                  <h4 className="font-semibold text-sm text-foreground mb-2">
                    {section.title}
                  </h4>
                  <ul className="space-y-1">
                    {section.items.map((item) => (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          className={cn(
                            'block text-sm py-1.5 px-3 rounded-md transition-colors',
                            pathname === item.href
                              ? 'bg-accent/10 text-accent-foreground font-medium'
                              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                          )}
                        >
                          {item.title}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </aside>

          {/* Main Content */}
          <main className="flex-1 min-w-0">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
              <Link href="/docs" className="hover:text-foreground">
                Docs
              </Link>
              <ChevronRight className="h-4 w-4" />
              <span className="text-foreground">{title}</span>
            </div>

            {/* Page Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-foreground mb-2">{title}</h1>
              {description && (
                <p className="text-lg text-muted-foreground">{description}</p>
              )}
            </div>

            {/* Content */}
            <div className="prose prose-slate dark:prose-invert max-w-none">
              {children}
            </div>
          </main>
        </div>
      </div>
    </MarketingLayout>
  );
}
