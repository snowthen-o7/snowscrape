/**
 * Hero Section
 * Landing page hero with gradient background
 */

'use client';

import { Button } from '@snowforge/ui';
import { ArrowRight, PlayCircle } from 'lucide-react';
import Link from 'next/link';

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-brand-primary via-brand-primary/95 to-brand-accent/20">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-grid-white/[0.05] bg-[size:20px_20px]" />

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-brand-primary/50 via-transparent to-transparent" />

      <div className="relative mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          {/* Badge */}
          <div className="mb-8 inline-flex items-center gap-2 rounded-full bg-brand-accent/10 px-4 py-2 text-sm font-medium text-brand-accent ring-1 ring-inset ring-brand-accent/20">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-accent opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-accent"></span>
            </span>
            Now in Beta - Limited Time Free Access
          </div>

          {/* Main heading */}
          <h1 className="text-5xl font-bold tracking-tight text-white sm:text-7xl">
            Web Scraping
            <span className="block bg-gradient-to-r from-brand-accent to-cyan-300 bg-clip-text text-transparent">
              Made Simple
            </span>
          </h1>

          {/* Subheading */}
          <p className="mt-6 text-lg leading-8 text-gray-300 sm:text-xl">
            Extract data from any website with powerful CSS, XPath, and regex queries.
            Schedule jobs, handle JavaScript rendering, and export to multiple formats.
            No coding required.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex items-center justify-center gap-4">
            <Button size="lg" asChild className="bg-brand-accent text-brand-primary hover:bg-brand-accent/90">
              <Link href="/sign-up">
                Get Started Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>

            <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10">
              <PlayCircle className="mr-2 h-5 w-5" />
              Watch Demo
            </Button>
          </div>

          {/* Trust indicators */}
          <div className="mt-12 flex items-center justify-center gap-8 text-sm text-gray-400">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-brand-accent" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              No credit card required
            </div>
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-brand-accent" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Free forever plan
            </div>
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-brand-accent" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Cancel anytime
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="mx-auto mt-20 max-w-5xl">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <div className="text-center">
              <div className="text-4xl font-bold text-brand-accent">1M+</div>
              <div className="mt-2 text-sm text-gray-400">Pages Scraped Daily</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-brand-accent">99.9%</div>
              <div className="mt-2 text-sm text-gray-400">Uptime SLA</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-brand-accent">10K+</div>
              <div className="mt-2 text-sm text-gray-400">Active Users</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-brand-accent">500+</div>
              <div className="mt-2 text-sm text-gray-400">Templates</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
