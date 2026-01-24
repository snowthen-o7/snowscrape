/**
 * Landing Page
 * Main marketing homepage for SnowScrape
 */

import { Hero } from '@/components/marketing/Hero';
import { FeatureCard } from '@/components/marketing/FeatureCard';
import { TestimonialCard } from '@/components/marketing/TestimonialCard';
import { CTASection } from '@/components/marketing/CTASection';
import { Button } from '@snowforge/ui';
import { MarketingLayout } from '@/components/layout';
import {
  Code2,
  Zap,
  Globe,
  Calendar,
  Download,
  Shield,
  BarChart3,
  Webhook,
  FileCode,
  Clock,
  Database,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';

export default function Home() {
  return (
    <MarketingLayout>
      {/* Hero Section */}
      <Hero />

      {/* Features Section */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Everything you need to scrape the web
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Powerful features designed for developers, data scientists, and businesses
              who need reliable web data extraction.
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Code2}
              title="Multiple Query Types"
              description="Extract data using XPath, CSS selectors, regex, or JSONPath. Mix and match for complex scraping scenarios."
            />
            <FeatureCard
              icon={Zap}
              title="JavaScript Rendering"
              description="Scrape dynamic websites with full JavaScript execution. Handle SPAs, lazy loading, and AJAX content."
            />
            <FeatureCard
              icon={Globe}
              title="Proxy Rotation"
              description="Built-in proxy support with geo-targeting, automatic rotation, and fallback strategies."
            />
            <FeatureCard
              icon={Calendar}
              title="Smart Scheduling"
              description="Schedule jobs by day, hour, and minute. Run scrapes exactly when you need them."
            />
            <FeatureCard
              icon={Download}
              title="Multiple Export Formats"
              description="Download results as JSON, CSV, Excel, Parquet, or SQL. Perfect for any data pipeline."
            />
            <FeatureCard
              icon={Webhook}
              title="Webhook Notifications"
              description="Get real-time notifications when jobs complete, fail, or require attention."
            />
            <FeatureCard
              icon={Shield}
              title="Enterprise Security"
              description="SOC 2 compliant with encryption at rest and in transit. Your data is always protected."
            />
            <FeatureCard
              icon={BarChart3}
              title="Usage Analytics"
              description="Track API calls, data volume, costs, and performance metrics with detailed analytics."
            />
            <FeatureCard
              icon={FileCode}
              title="Template Marketplace"
              description="500+ pre-built templates for popular websites. Get started in seconds, not hours."
            />
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              How it works
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              From zero to extracting data in three simple steps
            </p>
          </div>

          <div className="mx-auto mt-16 max-w-5xl">
            <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
              {/* Step 1 */}
              <div className="relative">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent text-xl font-bold text-brand-primary">
                  1
                </div>
                <h3 className="mt-6 text-xl font-semibold text-foreground">
                  Choose a Template or Start Fresh
                </h3>
                <p className="mt-2 text-muted-foreground">
                  Browse 500+ pre-built templates for popular websites, or create your own
                  custom scraper from scratch.
                </p>
              </div>

              {/* Step 2 */}
              <div className="relative">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent text-xl font-bold text-brand-primary">
                  2
                </div>
                <h3 className="mt-6 text-xl font-semibold text-foreground">
                  Configure Your Queries
                </h3>
                <p className="mt-2 text-muted-foreground">
                  Define what data to extract using XPath, CSS selectors, or regex. Set up
                  scheduling, proxies, and export options.
                </p>
              </div>

              {/* Step 3 */}
              <div className="relative">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent text-xl font-bold text-brand-primary">
                  3
                </div>
                <h3 className="mt-6 text-xl font-semibold text-foreground">
                  Run and Export
                </h3>
                <p className="mt-2 text-muted-foreground">
                  Hit run and watch your data flow in real-time. Export to your favorite
                  format or send to webhooks.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Teaser */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Simple, transparent pricing
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Start free, scale as you grow. No hidden fees or surprises.
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-3">
            {/* Free Plan */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <h3 className="text-2xl font-bold text-foreground">Free</h3>
              <p className="mt-2 text-sm text-muted-foreground">Perfect for testing and small projects</p>
              <p className="mt-6 flex items-baseline gap-x-2">
                <span className="text-5xl font-bold tracking-tight text-foreground">$0</span>
                <span className="text-sm text-muted-foreground">/month</span>
              </p>
              <ul className="mt-8 space-y-3 text-sm leading-6 text-muted-foreground">
                <li className="flex gap-x-3">
                  <Clock className="h-5 w-5 flex-none text-brand-accent" />
                  1,000 API calls/month
                </li>
                <li className="flex gap-x-3">
                  <Database className="h-5 w-5 flex-none text-brand-accent" />
                  100 MB storage
                </li>
                <li className="flex gap-x-3">
                  <Sparkles className="h-5 w-5 flex-none text-brand-accent" />
                  Access to all templates
                </li>
              </ul>
              <Button className="mt-8 w-full" variant="outline" asChild>
                <Link href="/sign-up">Get Started</Link>
              </Button>
            </div>

            {/* Pro Plan */}
            <div className="relative rounded-2xl border-2 border-brand-accent bg-card p-8 ring-2 ring-brand-accent/20">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-brand-accent px-4 py-1 text-sm font-semibold text-brand-primary">
                Most Popular
              </div>
              <h3 className="text-2xl font-bold text-foreground">Pro</h3>
              <p className="mt-2 text-sm text-muted-foreground">For professionals and growing teams</p>
              <p className="mt-6 flex items-baseline gap-x-2">
                <span className="text-5xl font-bold tracking-tight text-foreground">$49</span>
                <span className="text-sm text-muted-foreground">/month</span>
              </p>
              <ul className="mt-8 space-y-3 text-sm leading-6 text-muted-foreground">
                <li className="flex gap-x-3">
                  <Clock className="h-5 w-5 flex-none text-brand-accent" />
                  100,000 API calls/month
                </li>
                <li className="flex gap-x-3">
                  <Database className="h-5 w-5 flex-none text-brand-accent" />
                  10 GB storage
                </li>
                <li className="flex gap-x-3">
                  <Sparkles className="h-5 w-5 flex-none text-brand-accent" />
                  JavaScript rendering
                </li>
                <li className="flex gap-x-3">
                  <Sparkles className="h-5 w-5 flex-none text-brand-accent" />
                  Proxy rotation
                </li>
              </ul>
              <Button className="mt-8 w-full bg-brand-accent text-brand-primary hover:bg-brand-accent/90" asChild>
                <Link href="/sign-up">Start Free Trial</Link>
              </Button>
            </div>

            {/* Enterprise Plan */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <h3 className="text-2xl font-bold text-foreground">Enterprise</h3>
              <p className="mt-2 text-sm text-muted-foreground">For large-scale operations</p>
              <p className="mt-6 flex items-baseline gap-x-2">
                <span className="text-5xl font-bold tracking-tight text-foreground">Custom</span>
              </p>
              <ul className="mt-8 space-y-3 text-sm leading-6 text-muted-foreground">
                <li className="flex gap-x-3">
                  <Clock className="h-5 w-5 flex-none text-brand-accent" />
                  Unlimited API calls
                </li>
                <li className="flex gap-x-3">
                  <Database className="h-5 w-5 flex-none text-brand-accent" />
                  Unlimited storage
                </li>
                <li className="flex gap-x-3">
                  <Sparkles className="h-5 w-5 flex-none text-brand-accent" />
                  Dedicated support
                </li>
                <li className="flex gap-x-3">
                  <Sparkles className="h-5 w-5 flex-none text-brand-accent" />
                  Custom SLAs
                </li>
              </ul>
              <Button className="mt-8 w-full" variant="outline" asChild>
                <Link href="/contact">Contact Sales</Link>
              </Button>
            </div>
          </div>

          <div className="mt-8 text-center">
            <Link
              href="/pricing"
              className="text-sm font-semibold text-brand-accent hover:text-brand-accent/80"
            >
              View full pricing details →
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Trusted by thousands of developers
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              See what our customers are saying about SnowScrape
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-3">
            <TestimonialCard
              quote="SnowScrape cut our data collection time from days to hours. The template marketplace alone is worth the price of admission."
              author="Sarah Johnson"
              role="Data Engineer"
              company="TechCorp"
            />
            <TestimonialCard
              quote="Finally, a scraping tool that just works. No complicated setup, no maintenance nightmares. Just reliable data extraction."
              author="Michael Chen"
              role="CTO"
              company="DataFlow Inc"
            />
            <TestimonialCard
              quote="The JavaScript rendering feature is a game-changer. We can now scrape modern SPAs without any issues."
              author="Emily Rodriguez"
              role="Lead Developer"
              company="WebData Solutions"
            />
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <CTASection
        title="Ready to start scraping?"
        description="Join thousands of developers and businesses who trust SnowScrape for their web data needs. Start your free trial today."
        secondaryCTA={{ text: 'View Pricing', href: '/pricing' }}
      />
    </MarketingLayout>
  );
}
