/**
 * About Page
 * Company mission, team, and values
 */

import { MarketingLayout } from '@/components/layout';
import { CTASection } from '@/components/marketing/CTASection';
import {
  Target,
  Heart,
  Zap,
  Users,
  Globe,
  TrendingUp,
} from 'lucide-react';

export default function About() {
  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Making web data accessible to everyone
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              We're building the most powerful, yet easiest-to-use web scraping platform
              on the planet. No coding required, just results.
            </p>
          </div>
        </div>
      </section>

      {/* Mission */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                Our Mission
              </h2>
              <p className="mt-6 text-lg text-muted-foreground">
                At SnowScrape, we believe that web data should be accessible to everyone—not
                just developers with advanced programming skills.
              </p>
              <p className="mt-4 text-lg text-muted-foreground">
                We're on a mission to democratize web data extraction by providing powerful,
                reliable, and easy-to-use tools that help businesses of all sizes make
                data-driven decisions.
              </p>
              <p className="mt-4 text-lg text-muted-foreground">
                Whether you're a solo entrepreneur tracking competitor prices, a data scientist
                gathering research data, or an enterprise team building custom integrations,
                SnowScrape scales with your needs.
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8">
              <h3 className="text-xl font-semibold text-foreground">By the Numbers</h3>
              <div className="mt-8 grid grid-cols-2 gap-8">
                <div>
                  <p className="text-4xl font-bold text-accent-foreground">1M+</p>
                  <p className="mt-2 text-sm text-muted-foreground">Pages scraped daily</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-accent-foreground">10K+</p>
                  <p className="mt-2 text-sm text-muted-foreground">Active users</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-accent-foreground">99.9%</p>
                  <p className="mt-2 text-sm text-muted-foreground">Uptime guarantee</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-accent-foreground">500+</p>
                  <p className="mt-2 text-sm text-muted-foreground">Ready-made templates</p>
                </div>
              </div>

              <div className="mt-8 rounded-lg bg-muted p-4">
                <p className="text-sm text-muted-foreground">
                  Founded in 2023, we've helped thousands of businesses extract millions of
                  data points and save countless hours of manual work.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Our Values
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              The principles that guide everything we do
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            {/* Value 1 */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Target className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">
                Customer-First
              </h3>
              <p className="mt-2 text-muted-foreground">
                Every decision we make starts with our customers. We build features based on
                your feedback and needs, not what's trendy.
              </p>
            </div>

            {/* Value 2 */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Zap className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">
                Simplicity
              </h3>
              <p className="mt-2 text-muted-foreground">
                Web scraping shouldn't require a PhD in computer science. We make complex
                technology simple and accessible to everyone.
              </p>
            </div>

            {/* Value 3 */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Heart className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">
                Reliability
              </h3>
              <p className="mt-2 text-muted-foreground">
                Your data collection can't wait. We maintain 99.9% uptime and ensure your
                jobs run exactly when and how you expect them to.
              </p>
            </div>

            {/* Value 4 */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Users className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">
                Transparency
              </h3>
              <p className="mt-2 text-muted-foreground">
                No hidden fees, no surprise charges. We're upfront about our pricing,
                features, and limitations so you can make informed decisions.
              </p>
            </div>

            {/* Value 5 */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <TrendingUp className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">
                Innovation
              </h3>
              <p className="mt-2 text-muted-foreground">
                The web is constantly evolving, and so are we. We continuously improve our
                platform to handle modern websites and new challenges.
              </p>
            </div>

            {/* Value 6 */}
            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10">
                <Globe className="h-6 w-6 text-accent-foreground" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-foreground">
                Ethical Practices
              </h3>
              <p className="mt-2 text-muted-foreground">
                We promote responsible web scraping. Our tools respect robots.txt, rate
                limits, and website terms of service.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Meet the Team
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              A diverse team of engineers, designers, and data enthusiasts
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                name: 'Alex Rivera',
                role: 'CEO & Co-Founder',
                initials: 'AR',
              },
              {
                name: 'Sarah Chen',
                role: 'CTO & Co-Founder',
                initials: 'SC',
              },
              {
                name: 'Marcus Johnson',
                role: 'Head of Engineering',
                initials: 'MJ',
              },
              {
                name: 'Emily Taylor',
                role: 'Head of Product',
                initials: 'ET',
              },
            ].map((member) => (
              <div
                key={member.name}
                className="rounded-2xl border border-border bg-card p-8 text-center"
              >
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-accent/10 text-2xl font-bold text-accent-foreground">
                  {member.initials}
                </div>
                <h3 className="mt-6 text-lg font-semibold text-foreground">{member.name}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{member.role}</p>
              </div>
            ))}
          </div>

          <div className="mx-auto mt-16 max-w-3xl text-center">
            <p className="text-lg text-muted-foreground">
              We're a remote-first team distributed across 8 countries, united by our passion
              for making web data more accessible.
            </p>
          </div>
        </div>
      </section>

      {/* Story */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Our Story
            </h2>
            <div className="mt-8 space-y-6 text-lg text-muted-foreground">
              <p>
                SnowScrape was born out of frustration. Our founders, Alex and Sarah, spent
                years building custom web scrapers for various projects—from e-commerce price
                monitoring to market research data collection.
              </p>
              <p>
                Each new project meant writing hundreds of lines of code, dealing with proxy
                management, handling JavaScript rendering, and debugging endless edge cases.
                There had to be a better way.
              </p>
              <p>
                In 2023, they decided to build the scraping platform they wished existed:
                powerful enough for complex use cases, yet simple enough for anyone to use
                without writing a single line of code.
              </p>
              <p>
                Today, SnowScrape serves thousands of users—from solo entrepreneurs to Fortune
                500 companies—helping them extract millions of data points daily. We're just
                getting started.
              </p>
            </div>

            <div className="mt-12 rounded-2xl border border-border bg-card p-8">
              <h3 className="text-xl font-semibold text-foreground">Join Us</h3>
              <p className="mt-4 text-muted-foreground">
                We're always looking for talented people who share our mission. Check out our
                open positions and join us in making web data accessible to everyone.
              </p>
              <div className="mt-6 flex gap-4">
                <a
                  href="/careers"
                  className="inline-flex items-center rounded-lg bg-accent px-6 py-3 font-semibold text-primary hover:bg-accent/90"
                >
                  View Open Positions
                </a>
                <a
                  href="/contact"
                  className="inline-flex items-center rounded-lg border border-border bg-card px-6 py-3 font-semibold text-foreground hover:border-accent/50"
                >
                  Get in Touch
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <CTASection
        title="Ready to join thousands of happy customers?"
        description="Start extracting web data today with our free plan. No credit card required."
        primaryCTA={{ text: 'Start Free Trial', href: '/sign-up' }}
        secondaryCTA={{ text: 'Contact Sales', href: '/contact' }}
      />
    </MarketingLayout>
  );
}
