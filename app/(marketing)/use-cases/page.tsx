/**
 * Use Cases Page
 * Industry-specific scraping examples and solutions
 */

import { MarketingLayout } from '@/components/layout/MarketingLayout';
import { CTASection } from '@/components/marketing/CTASection';
import {
  ShoppingCart,
  TrendingUp,
  Building2,
  Briefcase,
  Search,
  Users,
} from 'lucide-react';

export default function UseCases() {
  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Solutions for every industry
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              See how businesses across industries use SnowScrape to extract valuable
              data and gain competitive advantages.
            </p>
          </div>
        </div>
      </section>

      {/* Use Cases Grid */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          {/* E-commerce */}
          <div className="mb-24">
            <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
              <div>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                  <ShoppingCart className="h-6 w-6 text-brand-accent" />
                </div>
                <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
                  E-commerce Price Monitoring
                </h2>
                <p className="mt-6 text-lg text-muted-foreground">
                  Track competitor prices, product availability, and reviews across multiple
                  online retailers. Stay competitive with real-time pricing intelligence.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <h4 className="font-semibold text-foreground">Common Use Cases</h4>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Monitor competitor pricing strategies</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Track product availability and stock levels</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Aggregate customer reviews and ratings</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Identify pricing trends and opportunities</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-card p-8">
                <h3 className="text-lg font-semibold text-foreground">Example: Amazon Competitor Tracking</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  A consumer electronics retailer uses SnowScrape to monitor prices of 500+
                  products across 10 competitors every hour.
                </p>

                <div className="mt-6 space-y-4">
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-xs font-medium text-foreground">Data Points Collected:</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      <li>• Product name and SKU</li>
                      <li>• Current price and discount percentage</li>
                      <li>• Stock availability status</li>
                      <li>• Average rating and review count</li>
                      <li>• Seller information</li>
                    </ul>
                  </div>

                  <div className="rounded-lg bg-brand-accent/10 p-4">
                    <p className="text-xs font-medium text-foreground">Results:</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      <li>• 15% increase in competitive pricing accuracy</li>
                      <li>• Reduced manual monitoring time by 30 hours/week</li>
                      <li>• Identified $200K in revenue opportunities</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Market Research */}
          <div className="mb-24">
            <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
              <div className="order-2 lg:order-1">
                <div className="rounded-2xl border border-border bg-card p-8">
                  <h3 className="text-lg font-semibold text-foreground">Example: Social Media Sentiment Analysis</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A marketing agency tracks brand mentions and sentiment across social
                    platforms for 20+ clients.
                  </p>

                  <div className="mt-6 space-y-4">
                    <div className="rounded-lg bg-muted p-4">
                      <p className="text-xs font-medium text-foreground">Data Sources:</p>
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>• Twitter/X posts and engagement metrics</li>
                        <li>• Reddit discussions and upvotes</li>
                        <li>• Product review sites</li>
                        <li>• News articles and blogs</li>
                      </ul>
                    </div>

                    <div className="rounded-lg bg-brand-accent/10 p-4">
                      <p className="text-xs font-medium text-foreground">Impact:</p>
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>• Real-time brand reputation monitoring</li>
                        <li>• Early detection of PR issues</li>
                        <li>• Competitive intelligence gathering</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="order-1 lg:order-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                  <TrendingUp className="h-6 w-6 text-brand-accent" />
                </div>
                <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
                  Market Research & Analysis
                </h2>
                <p className="mt-6 text-lg text-muted-foreground">
                  Gather market intelligence, track trends, and analyze consumer sentiment
                  from social media, forums, and review sites.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <h4 className="font-semibold text-foreground">Popular Applications</h4>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Brand reputation monitoring</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Consumer sentiment analysis</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Trend identification and forecasting</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Competitor product launches</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Real Estate */}
          <div className="mb-24">
            <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
              <div>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                  <Building2 className="h-6 w-6 text-brand-accent" />
                </div>
                <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
                  Real Estate Data Aggregation
                </h2>
                <p className="mt-6 text-lg text-muted-foreground">
                  Collect property listings, pricing trends, and market data from multiple
                  real estate platforms to power your analytics and investment decisions.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <h4 className="font-semibold text-foreground">Key Use Cases</h4>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Property listing aggregation</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Market trend analysis by location</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Investment opportunity identification</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Rental yield calculations</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-card p-8">
                <h3 className="text-lg font-semibold text-foreground">Example: Multi-Platform Listing Aggregator</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  A real estate investment firm scrapes 50,000+ property listings daily from
                  Zillow, Realtor.com, and Redfin.
                </p>

                <div className="mt-6 space-y-4">
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-xs font-medium text-foreground">Extracted Data:</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      <li>• Property details (beds, baths, sqft)</li>
                      <li>• Listing and sale prices</li>
                      <li>• Days on market and price history</li>
                      <li>• Neighborhood statistics</li>
                      <li>• School ratings and proximity</li>
                    </ul>
                  </div>

                  <div className="rounded-lg bg-brand-accent/10 p-4">
                    <p className="text-xs font-medium text-foreground">Outcome:</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      <li>• 40% faster deal identification</li>
                      <li>• $2M in undervalued properties found</li>
                      <li>• Comprehensive market coverage</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Job Market */}
          <div className="mb-24">
            <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
              <div className="order-2 lg:order-1">
                <div className="rounded-2xl border border-border bg-card p-8">
                  <h3 className="text-lg font-semibold text-foreground">Example: Tech Job Market Analysis</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A recruiting agency monitors 10,000+ tech job postings across LinkedIn,
                    Indeed, and company career pages.
                  </p>

                  <div className="mt-6 space-y-4">
                    <div className="rounded-lg bg-muted p-4">
                      <p className="text-xs font-medium text-foreground">Tracked Metrics:</p>
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>• Job titles and required skills</li>
                        <li>• Salary ranges and benefits</li>
                        <li>• Remote vs. on-site ratios</li>
                        <li>• Hiring company information</li>
                        <li>• Application deadlines</li>
                      </ul>
                    </div>

                    <div className="rounded-lg bg-brand-accent/10 p-4">
                      <p className="text-xs font-medium text-foreground">Benefits:</p>
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>• Salary benchmarking for candidates</li>
                        <li>• Skills gap identification</li>
                        <li>• Hiring trend forecasting</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="order-1 lg:order-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                  <Briefcase className="h-6 w-6 text-brand-accent" />
                </div>
                <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
                  Job Market Intelligence
                </h2>
                <p className="mt-6 text-lg text-muted-foreground">
                  Monitor job postings, salary trends, and hiring patterns to make informed
                  career decisions or optimize your recruitment strategy.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <h4 className="font-semibold text-foreground">Applications</h4>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Salary benchmarking and trends</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Skills demand analysis</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Company hiring patterns</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Remote work trends</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* SEO & Content */}
          <div className="mb-24">
            <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
              <div>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                  <Search className="h-6 w-6 text-brand-accent" />
                </div>
                <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
                  SEO & Content Research
                </h2>
                <p className="mt-6 text-lg text-muted-foreground">
                  Extract SERP data, backlink profiles, and content performance metrics to
                  inform your SEO strategy and content creation.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <h4 className="font-semibold text-foreground">Use Cases</h4>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>SERP position tracking</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Competitor content analysis</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Backlink monitoring</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Keyword research at scale</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-card p-8">
                <h3 className="text-lg font-semibold text-foreground">Example: Content Gap Analysis</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  An SEO agency tracks 5,000+ keywords across Google SERPs for 30 clients,
                  identifying content opportunities.
                </p>

                <div className="mt-6 space-y-4">
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-xs font-medium text-foreground">Analyzed Elements:</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      <li>• Title tags and meta descriptions</li>
                      <li>• Featured snippets and SERP features</li>
                      <li>• Top 10 ranking pages</li>
                      <li>• Content length and structure</li>
                      <li>• Domain authority scores</li>
                    </ul>
                  </div>

                  <div className="rounded-lg bg-brand-accent/10 p-4">
                    <p className="text-xs font-medium text-foreground">Results:</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      <li>• 200+ content opportunities identified</li>
                      <li>• 35% increase in organic traffic</li>
                      <li>• Automated competitor monitoring</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Lead Generation */}
          <div>
            <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
              <div className="order-2 lg:order-1">
                <div className="rounded-2xl border border-border bg-card p-8">
                  <h3 className="text-lg font-semibold text-foreground">Example: B2B Lead Database Building</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A sales automation company builds targeted lead lists by scraping business
                    directories, LinkedIn, and company websites.
                  </p>

                  <div className="mt-6 space-y-4">
                    <div className="rounded-lg bg-muted p-4">
                      <p className="text-xs font-medium text-foreground">Data Collected:</p>
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>• Company name and industry</li>
                        <li>• Contact information (email, phone)</li>
                        <li>• Decision maker titles</li>
                        <li>• Company size and revenue</li>
                        <li>• Technology stack used</li>
                      </ul>
                    </div>

                    <div className="rounded-lg bg-brand-accent/10 p-4">
                      <p className="text-xs font-medium text-foreground">Impact:</p>
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>• 50,000+ qualified leads generated</li>
                        <li>• 70% reduction in lead research time</li>
                        <li>• 25% increase in conversion rates</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="order-1 lg:order-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                  <Users className="h-6 w-6 text-brand-accent" />
                </div>
                <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
                  Lead Generation & Enrichment
                </h2>
                <p className="mt-6 text-lg text-muted-foreground">
                  Build targeted lead lists and enrich contact data from business directories,
                  social networks, and company websites.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <h4 className="font-semibold text-foreground">Common Applications</h4>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>B2B prospect identification</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Contact information verification</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Company firmographic data</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-brand-accent">•</span>
                        <span>Technology stack detection</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Industries Served */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Trusted across industries
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              From startups to enterprises, businesses of all sizes rely on SnowScrape
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-2 gap-8 md:grid-cols-4">
            {[
              'E-commerce',
              'Finance',
              'Real Estate',
              'Marketing',
              'Recruiting',
              'Research',
              'Travel',
              'Media',
            ].map((industry) => (
              <div
                key={industry}
                className="rounded-lg border border-border bg-card p-6 text-center transition-all hover:border-brand-accent/50"
              >
                <p className="font-semibold text-foreground">{industry}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <CTASection
        title="Ready to solve your use case?"
        description="Join thousands of companies extracting valuable data with SnowScrape."
        primaryCTA={{ text: 'Start Free Trial', href: '/sign-up' }}
        secondaryCTA={{ text: 'Contact Sales', href: '/contact' }}
      />
    </MarketingLayout>
  );
}
