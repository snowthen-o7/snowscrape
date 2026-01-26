/**
 * CTA Section
 * Call-to-action section for marketing pages
 */

'use client';

import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface CTASectionProps {
  title: string;
  description: string;
  primaryCTA?: {
    text: string;
    href: string;
  };
  secondaryCTA?: {
    text: string;
    href: string;
  };
}

export function CTASection({
  title,
  description,
  primaryCTA = { text: 'Get Started Free', href: '/sign-up' },
  secondaryCTA,
}: CTASectionProps) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-brand-primary to-brand-primary/90">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-grid-white/[0.05] bg-[size:20px_20px]" />

      <div className="relative mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
            {title}
          </h2>
          <p className="mt-6 text-lg leading-8 text-gray-300">
            {description}
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Button size="lg" asChild className="bg-brand-accent text-brand-primary hover:bg-brand-accent/90">
              <Link href={primaryCTA.href}>
                {primaryCTA.text}
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>

            {secondaryCTA && (
              <Button
                size="lg"
                variant="outline"
                asChild
                className="border-white/20 text-white hover:bg-white/10"
              >
                <Link href={secondaryCTA.href}>{secondaryCTA.text}</Link>
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
