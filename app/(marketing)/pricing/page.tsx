/**
 * Pricing Page
 * Detailed pricing plans with comparison table and FAQ
 */

import { MarketingLayout } from '@/components/layout';
import { PricingCard } from '@/components/marketing/PricingCard';
import { CTASection } from '@/components/marketing/CTASection';
import { Check, X } from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@snowforge/ui';

export default function Pricing() {
  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Simple, transparent pricing
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Choose the plan that fits your needs. Start free, upgrade as you grow.
              All plans include our core features.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
            {/* Starter Plan */}
            <PricingCard
              name="Starter"
              price={0}
              description="Perfect for testing and small projects"
              features={[
                '1,000 API calls/month',
                '100 MB storage',
                'All query types (XPath, CSS, Regex)',
                'Basic scheduling',
                'CSV & JSON export',
                'Email support',
                'Access to all templates',
              ]}
              cta="Get Started Free"
              ctaHref="/sign-up"
            />

            {/* Pro Plan */}
            <PricingCard
              name="Pro"
              price={49}
              description="For professionals and growing teams"
              features={[
                '100,000 API calls/month',
                '10 GB storage',
                'JavaScript rendering',
                'Advanced scheduling',
                'All export formats',
                'Proxy rotation',
                'Webhook notifications',
                'Priority email support',
                'Custom templates',
              ]}
              cta="Start Free Trial"
              ctaHref="/sign-up"
              popular
              variant="accent"
            />

            {/* Business Plan */}
            <PricingCard
              name="Business"
              price={149}
              description="For teams and businesses"
              features={[
                '500,000 API calls/month',
                '50 GB storage',
                'Everything in Pro',
                'Dedicated proxies',
                'Custom rate limits',
                'Team collaboration (5 users)',
                'SSO & SAML',
                'Phone & chat support',
                'SLA guarantee',
              ]}
              cta="Start Free Trial"
              ctaHref="/sign-up"
            />

            {/* Enterprise Plan */}
            <PricingCard
              name="Enterprise"
              price="Custom"
              description="For large-scale operations"
              features={[
                'Unlimited API calls',
                'Unlimited storage',
                'Everything in Business',
                'Dedicated infrastructure',
                'Custom integrations',
                'Unlimited team members',
                'Dedicated account manager',
                '24/7 phone support',
                'Custom SLAs',
              ]}
              cta="Contact Sales"
              ctaHref="/contact"
            />
          </div>

          {/* Annual discount notice */}
          <div className="mt-12 text-center">
            <p className="text-sm text-muted-foreground">
              💰 Save 20% with annual billing
            </p>
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Compare plans
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Detailed feature comparison across all plans
            </p>
          </div>

          <div className="mx-auto mt-16 max-w-6xl overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-4 pr-8 text-sm font-semibold text-foreground">
                    Features
                  </th>
                  <th className="pb-4 px-6 text-sm font-semibold text-center text-foreground">
                    Starter
                  </th>
                  <th className="pb-4 px-6 text-sm font-semibold text-center text-foreground">
                    Pro
                  </th>
                  <th className="pb-4 px-6 text-sm font-semibold text-center text-foreground">
                    Business
                  </th>
                  <th className="pb-4 pl-6 text-sm font-semibold text-center text-foreground">
                    Enterprise
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {/* API Calls */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    API calls per month
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    1,000
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    100,000
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    500,000
                  </td>
                  <td className="py-4 pl-6 text-sm text-center text-foreground">
                    Unlimited
                  </td>
                </tr>

                {/* Storage */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    Storage
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    100 MB
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    10 GB
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    50 GB
                  </td>
                  <td className="py-4 pl-6 text-sm text-center text-foreground">
                    Unlimited
                  </td>
                </tr>

                {/* JavaScript Rendering */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    JavaScript rendering
                  </td>
                  <td className="py-4 px-6 text-center">
                    <X className="inline h-5 w-5 text-muted-foreground" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 pl-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                </tr>

                {/* Proxy Rotation */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    Proxy rotation
                  </td>
                  <td className="py-4 px-6 text-center">
                    <X className="inline h-5 w-5 text-muted-foreground" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 pl-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                </tr>

                {/* Webhooks */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    Webhook notifications
                  </td>
                  <td className="py-4 px-6 text-center">
                    <X className="inline h-5 w-5 text-muted-foreground" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 pl-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                </tr>

                {/* Team members */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    Team members
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    1
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    1
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    5
                  </td>
                  <td className="py-4 pl-6 text-sm text-center text-foreground">
                    Unlimited
                  </td>
                </tr>

                {/* Support */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    Support
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    Email
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    Priority email
                  </td>
                  <td className="py-4 px-6 text-sm text-center text-foreground">
                    Phone & chat
                  </td>
                  <td className="py-4 pl-6 text-sm text-center text-foreground">
                    24/7 dedicated
                  </td>
                </tr>

                {/* SLA */}
                <tr>
                  <td className="py-4 pr-8 text-sm text-muted-foreground">
                    SLA guarantee
                  </td>
                  <td className="py-4 px-6 text-center">
                    <X className="inline h-5 w-5 text-muted-foreground" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <X className="inline h-5 w-5 text-muted-foreground" />
                  </td>
                  <td className="py-4 px-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                  <td className="py-4 pl-6 text-center">
                    <Check className="inline h-5 w-5 text-brand-accent" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-3xl px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Frequently asked questions
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Have a different question? Contact our support team.
            </p>
          </div>

          <Accordion type="single" collapsible className="mt-16">
            <AccordionItem value="item-1">
              <AccordionTrigger>What payment methods do you accept?</AccordionTrigger>
              <AccordionContent>
                We accept all major credit cards (Visa, MasterCard, American Express), PayPal,
                and bank transfers for Enterprise plans. All payments are processed securely through
                Stripe.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-2">
              <AccordionTrigger>Can I change plans at any time?</AccordionTrigger>
              <AccordionContent>
                Yes! You can upgrade or downgrade your plan at any time. When upgrading, you'll be
                charged a prorated amount for the remainder of your billing cycle. When downgrading,
                the change will take effect at the start of your next billing cycle.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-3">
              <AccordionTrigger>What happens if I exceed my plan limits?</AccordionTrigger>
              <AccordionContent>
                If you exceed your API call limit, your jobs will be paused until the next billing
                cycle or until you upgrade your plan. We'll send you email notifications at 80% and
                100% usage to help you stay informed.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-4">
              <AccordionTrigger>Do you offer annual billing?</AccordionTrigger>
              <AccordionContent>
                Yes! Annual billing is available for all paid plans and comes with a 20% discount.
                You can switch to annual billing from your account settings.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-5">
              <AccordionTrigger>Is there a free trial for paid plans?</AccordionTrigger>
              <AccordionContent>
                Yes! All paid plans come with a 14-day free trial. No credit card required to start.
                You can cancel at any time during the trial period without being charged.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-6">
              <AccordionTrigger>What's your refund policy?</AccordionTrigger>
              <AccordionContent>
                We offer a 30-day money-back guarantee for all plans. If you're not satisfied,
                contact our support team for a full refund.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-7">
              <AccordionTrigger>Can I use my own proxies?</AccordionTrigger>
              <AccordionContent>
                Yes! Business and Enterprise plans allow you to configure custom proxy servers.
                You can use your own residential or datacenter proxies alongside our built-in
                proxy rotation.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-8">
              <AccordionTrigger>Do you offer discounts for nonprofits?</AccordionTrigger>
              <AccordionContent>
                Yes! We offer a 50% discount on all plans for registered nonprofit organizations
                and educational institutions. Contact our sales team with your documentation.
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </section>

      {/* CTA */}
      <CTASection
        title="Ready to get started?"
        description="Start your free trial today. No credit card required."
        primaryCTA={{ text: 'Start Free Trial', href: '/sign-up' }}
        secondaryCTA={{ text: 'Contact Sales', href: '/contact' }}
      />
    </MarketingLayout>
  );
}
