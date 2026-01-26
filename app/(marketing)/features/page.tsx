/**
 * Features Page
 * Detailed feature breakdown with examples and benefits
 */

import { MarketingLayout } from '@/components/layout';
import { FeatureCard } from '@/components/marketing/FeatureCard';
import { CTASection } from '@/components/marketing/CTASection';
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
  Settings,
  Lock,
  Cpu,
} from 'lucide-react';

export default function Features() {
  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Powerful features for modern web scraping
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Everything you need to extract, transform, and export web data at scale.
              Built for developers, designed for simplicity.
            </p>
          </div>
        </div>
      </section>

      {/* Data Extraction */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Flexible Data Extraction
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Multiple extraction methods to handle any website structure
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Code2 className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">XPath & CSS Selectors</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Extract data using powerful XPath expressions or familiar CSS selectors.
                Perfect for precise targeting of nested elements.
              </p>
              <div className="mt-4 rounded-lg bg-muted p-3">
                <code className="text-xs text-foreground">
                  //div[@class='product']//span[@class='price']
                </code>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <FileCode className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">Regular Expressions</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Use regex patterns for complex text extraction and validation. Great for
                extracting specific patterns like emails, phone numbers, or prices.
              </p>
              <div className="mt-4 rounded-lg bg-muted p-3">
                <code className="text-xs text-foreground">
                  /\$[0-9]+\.[0-9]{'{2}'}/g
                </code>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Settings className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">JSONPath</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Extract data from JSON responses and APIs using JSONPath expressions.
                Ideal for working with RESTful APIs and JSON endpoints.
              </p>
              <div className="mt-4 rounded-lg bg-muted p-3">
                <code className="text-xs text-foreground">
                  $.items[*].price
                </code>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* JavaScript & Rendering */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-16 lg:grid-cols-2">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                JavaScript Rendering
              </h2>
              <p className="mt-6 text-lg leading-8 text-muted-foreground">
                Scrape dynamic websites with full JavaScript execution. Handle modern SPAs,
                lazy loading, AJAX content, and infinite scroll with ease.
              </p>

              <div className="mt-8 space-y-4">
                <div className="flex gap-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
                    <Zap className="h-4 w-4 text-accent-foreground" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground">Full Browser Automation</h4>
                    <p className="text-sm text-muted-foreground">
                      Powered by headless Chrome for authentic rendering
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
                    <Zap className="h-4 w-4 text-accent-foreground" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground">Wait for Elements</h4>
                    <p className="text-sm text-muted-foreground">
                      Automatically wait for dynamic content to load
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
                    <Zap className="h-4 w-4 text-accent-foreground" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground">Screenshot Capture</h4>
                    <p className="text-sm text-muted-foreground">
                      Take full-page screenshots for visual verification
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
                    <Zap className="h-4 w-4 text-accent-foreground" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground">Custom JavaScript</h4>
                    <p className="text-sm text-muted-foreground">
                      Execute custom scripts before extraction
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8">
              <h3 className="text-lg font-semibold text-foreground">Supported Scenarios</h3>
              <ul className="mt-6 space-y-3 text-sm text-muted-foreground">
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>React, Vue, Angular, and other SPA frameworks</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Infinite scroll and lazy-loaded content</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>AJAX requests and dynamic data loading</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Modal dialogs and popup content</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Interactive charts and data visualizations</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Client-side rendered tables and grids</span>
                </li>
              </ul>

              <div className="mt-8 rounded-lg bg-muted p-4">
                <p className="text-xs font-medium text-foreground">Example Configuration:</p>
                <pre className="mt-2 text-xs text-muted-foreground">
{`{
  "js_render": true,
  "wait_for": "div.products",
  "wait_time": 5000,
  "screenshot": true
}`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Proxy & Reliability */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Reliability & Scale
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Built-in features to ensure your scraping jobs run smoothly at any scale
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-2">
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Globe className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">Proxy Rotation</h3>
              <p className="mt-2 text-muted-foreground">
                Automatic proxy rotation with geo-targeting and fallback strategies. Avoid
                rate limits and IP bans with our global proxy network.
              </p>
              <ul className="mt-6 space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Residential and datacenter proxies</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Country and city-level targeting</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Automatic rotation and retry logic</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Custom proxy support (BYO)</span>
                </li>
              </ul>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Cpu className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">Smart Retry Logic</h3>
              <p className="mt-2 text-muted-foreground">
                Automatic retries with exponential backoff for failed requests. Handle
                temporary failures and network issues gracefully.
              </p>
              <ul className="mt-6 space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Configurable retry attempts and delays</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Exponential backoff strategy</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Proxy rotation on failures</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-foreground">•</span>
                  <span>Custom error handling</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Scheduling & Automation */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
            <div className="order-2 lg:order-1">
              <div className="rounded-2xl border border-border bg-card p-8">
                <h3 className="text-lg font-semibold text-foreground">Schedule Options</h3>
                <div className="mt-6 space-y-4">
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-sm font-medium text-foreground">Interval-based</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Every 5 minutes, hourly, daily, weekly, monthly
                    </p>
                  </div>
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-sm font-medium text-foreground">Cron Expression</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Full cron support: 0 9 * * 1-5 (9am weekdays)
                    </p>
                  </div>
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-sm font-medium text-foreground">Conditional</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Run when specific conditions are met
                    </p>
                  </div>
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-sm font-medium text-foreground">Manual</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Run on-demand via UI or API
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="order-1 lg:order-2">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Calendar className="h-6 w-6 text-accent-foreground" />
              </div>
              <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                Powerful Scheduling
              </h2>
              <p className="mt-6 text-lg leading-8 text-muted-foreground">
                Set it and forget it. Schedule your scraping jobs to run automatically at
                any interval, with full control over timing and frequency.
              </p>
              <ul className="mt-8 space-y-3 text-muted-foreground">
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Flexible scheduling with cron support</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Timezone-aware scheduling</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>Pause and resume jobs anytime</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-accent-foreground">✓</span>
                  <span>History and audit logs</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Export & Integration */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Export & Integrate
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Get your data in any format and integrate with your existing tools
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Download}
              title="Multiple Formats"
              description="Export to JSON, CSV, Excel, Parquet, or SQL. Choose the format that works best for your workflow."
            />
            <FeatureCard
              icon={Webhook}
              title="Webhook Notifications"
              description="Real-time notifications when jobs complete, fail, or require attention. Integrate with any service."
            />
            <FeatureCard
              icon={BarChart3}
              title="API Access"
              description="Full REST API for programmatic access. Build custom integrations and workflows."
            />
          </div>
        </div>
      </section>

      {/* Security & Compliance */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Enterprise Security
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Your data is protected with industry-leading security standards
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-3">
            <div className="rounded-2xl border border-border bg-card p-8 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Shield className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">SOC 2 Compliant</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Independently verified security controls and data protection
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Lock className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Encryption</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                AES-256 encryption at rest and TLS 1.3 in transit for all data
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Settings className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-lg font-semibold text-foreground">Access Control</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Role-based access, SSO, SAML, and audit logs for compliance
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <CTASection
        title="Ready to see these features in action?"
        description="Start your free trial today and experience the power of modern web scraping."
        primaryCTA={{ text: 'Start Free Trial', href: '/sign-up' }}
        secondaryCTA={{ text: 'View Pricing', href: '/pricing' }}
      />
    </MarketingLayout>
  );
}
