/**
 * Documentation Hub
 * Central documentation landing page with quick links
 */

import { MarketingLayout } from '@/components/layout';
import { CTASection } from '@/components/marketing/CTASection';
import {
  BookOpen,
  Code2,
  Zap,
  FileCode,
  Terminal,
  Lightbulb,
  Video,
  MessageCircle,
} from 'lucide-react';
import Link from 'next/link';

export default function Docs() {
  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Documentation
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Everything you need to get started with SnowScrape and become a web scraping expert.
            </p>

            {/* Search Bar Placeholder */}
            <div className="mt-10">
              <div className="mx-auto max-w-xl">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Search documentation..."
                    className="flex-1 rounded-lg border border-white/20 bg-white/10 px-4 py-3 text-white placeholder:text-gray-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                  />
                  <button className="rounded-lg bg-accent px-6 py-3 font-semibold text-primary hover:bg-accent/90">
                    Search
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Start */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Get started in minutes
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Follow our step-by-step guides to create your first scraping job
            </p>
          </div>

          <div className="mx-auto mt-16 max-w-5xl">
            <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
              {/* Step 1 */}
              <Link
                href="/docs/getting-started"
                className="group rounded-2xl border border-border bg-card p-8 transition-all hover:border-accent/50 hover:shadow-lg"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 transition-colors group-hover:bg-accent/20">
                  <BookOpen className="h-6 w-6 text-accent-foreground" />
                </div>
                <h3 className="mt-6 text-xl font-semibold text-foreground">
                  1. Getting Started
                </h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Create your account and set up your first project in less than 5 minutes.
                </p>
                <p className="mt-4 text-sm font-medium text-accent-foreground group-hover:underline">
                  Read the guide →
                </p>
              </Link>

              {/* Step 2 */}
              <Link
                href="/docs/creating-jobs"
                className="group rounded-2xl border border-border bg-card p-8 transition-all hover:border-accent/50 hover:shadow-lg"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 transition-colors group-hover:bg-accent/20">
                  <Zap className="h-6 w-6 text-accent-foreground" />
                </div>
                <h3 className="mt-6 text-xl font-semibold text-foreground">
                  2. Create Your First Job
                </h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Learn how to configure extraction queries and run your first scraping job.
                </p>
                <p className="mt-4 text-sm font-medium text-accent-foreground group-hover:underline">
                  View tutorial →
                </p>
              </Link>

              {/* Step 3 */}
              <Link
                href="/docs/exporting-data"
                className="group rounded-2xl border border-border bg-card p-8 transition-all hover:border-accent/50 hover:shadow-lg"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 transition-colors group-hover:bg-accent/20">
                  <FileCode className="h-6 w-6 text-accent-foreground" />
                </div>
                <h3 className="mt-6 text-xl font-semibold text-foreground">
                  3. Export Your Data
                </h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Export results in JSON, CSV, or other formats and integrate with your tools.
                </p>
                <p className="mt-4 text-sm font-medium text-accent-foreground group-hover:underline">
                  Learn more →
                </p>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Documentation Categories */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Explore by topic
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Deep dive into specific features and capabilities
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-6xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {/* Core Concepts */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <BookOpen className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Core Concepts</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/docs/jobs" className="hover:text-accent-foreground">
                    → Understanding Jobs
                  </Link>
                </li>
                <li>
                  <Link href="/docs/queries" className="hover:text-accent-foreground">
                    → Query Types (XPath, CSS, Regex)
                  </Link>
                </li>
                <li>
                  <Link href="/docs/scheduling" className="hover:text-accent-foreground">
                    → Scheduling & Automation
                  </Link>
                </li>
                <li>
                  <Link href="/docs/templates" className="hover:text-accent-foreground">
                    → Using Templates
                  </Link>
                </li>
              </ul>
            </div>

            {/* API Reference */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Code2 className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">API Reference</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/docs/api/authentication" className="hover:text-accent-foreground">
                    → Authentication
                  </Link>
                </li>
                <li>
                  <Link href="/docs/api/jobs" className="hover:text-accent-foreground">
                    → Jobs API
                  </Link>
                </li>
                <li>
                  <Link href="/docs/api/webhooks" className="hover:text-accent-foreground">
                    → Webhooks
                  </Link>
                </li>
                <li>
                  <Link href="/docs/api/rate-limits" className="hover:text-accent-foreground">
                    → Rate Limits & Quotas
                  </Link>
                </li>
              </ul>
            </div>

            {/* Advanced Features */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Terminal className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Advanced Features</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/docs/javascript-rendering" className="hover:text-accent-foreground">
                    → JavaScript Rendering
                  </Link>
                </li>
                <li>
                  <Link href="/docs/proxy-rotation" className="hover:text-accent-foreground">
                    → Proxy Rotation
                  </Link>
                </li>
                <li>
                  <Link href="/docs/custom-headers" className="hover:text-accent-foreground">
                    → Custom Headers & Cookies
                  </Link>
                </li>
                <li>
                  <Link href="/docs/error-handling" className="hover:text-accent-foreground">
                    → Error Handling & Retries
                  </Link>
                </li>
              </ul>
            </div>

            {/* Integrations */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Zap className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Integrations</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/docs/integrations/zapier" className="hover:text-accent-foreground">
                    → Zapier Integration
                  </Link>
                </li>
                <li>
                  <Link href="/docs/integrations/python" className="hover:text-accent-foreground">
                    → Python SDK
                  </Link>
                </li>
                <li>
                  <Link href="/docs/integrations/nodejs" className="hover:text-accent-foreground">
                    → Node.js SDK
                  </Link>
                </li>
                <li>
                  <Link href="/docs/integrations/webhooks" className="hover:text-accent-foreground">
                    → Webhook Integrations
                  </Link>
                </li>
              </ul>
            </div>

            {/* Best Practices */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Lightbulb className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Best Practices</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/docs/best-practices/performance" className="hover:text-accent-foreground">
                    → Performance Optimization
                  </Link>
                </li>
                <li>
                  <Link href="/docs/best-practices/reliability" className="hover:text-accent-foreground">
                    → Reliability & Monitoring
                  </Link>
                </li>
                <li>
                  <Link href="/docs/best-practices/legal" className="hover:text-accent-foreground">
                    → Legal & Ethical Scraping
                  </Link>
                </li>
                <li>
                  <Link href="/docs/best-practices/security" className="hover:text-accent-foreground">
                    → Security Best Practices
                  </Link>
                </li>
              </ul>
            </div>

            {/* Troubleshooting */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <MessageCircle className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Troubleshooting</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/docs/troubleshooting/common-errors" className="hover:text-accent-foreground">
                    → Common Errors
                  </Link>
                </li>
                <li>
                  <Link href="/docs/troubleshooting/debugging" className="hover:text-accent-foreground">
                    → Debugging Failed Jobs
                  </Link>
                </li>
                <li>
                  <Link href="/docs/troubleshooting/performance" className="hover:text-accent-foreground">
                    → Performance Issues
                  </Link>
                </li>
                <li>
                  <Link href="/docs/troubleshooting/contact" className="hover:text-accent-foreground">
                    → Contact Support
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Video Tutorials */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 mx-auto">
              <Video className="h-6 w-6 text-accent-foreground" />
            </div>
            <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Video Tutorials
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Watch step-by-step video guides to master SnowScrape features
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-3">
            {[
              {
                title: 'Getting Started with SnowScrape',
                duration: '8:32',
                description: 'Learn the basics in under 10 minutes',
              },
              {
                title: 'Advanced Query Techniques',
                duration: '12:15',
                description: 'Master XPath and CSS selectors',
              },
              {
                title: 'Setting Up Webhooks',
                duration: '6:45',
                description: 'Integrate SnowScrape with your tools',
              },
            ].map((video, index) => (
              <div
                key={index}
                className="group cursor-pointer rounded-2xl border border-border bg-card p-6 transition-all hover:border-accent/50 hover:shadow-lg"
              >
                <div className="aspect-video w-full rounded-lg bg-muted flex items-center justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10 transition-colors group-hover:bg-accent/20">
                    <Video className="h-8 w-8 text-accent-foreground" />
                  </div>
                </div>
                <h3 className="mt-4 font-semibold text-foreground">{video.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{video.description}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{video.duration}</span>
                  <span className="text-sm font-medium text-accent-foreground group-hover:underline">
                    Watch now →
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <CTASection
        title="Still have questions?"
        description="Our support team is here to help. Reach out anytime through chat, email, or phone."
        primaryCTA={{ text: 'Contact Support', href: '/contact' }}
        secondaryCTA={{ text: 'View All Docs', href: '/docs/getting-started' }}
      />
    </MarketingLayout>
  );
}
