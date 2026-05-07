/**
 * Onboarding Checkout Page
 * One CTA → POST /billing/checkout (plan=pro, is_trial=true) → Stripe.
 */

'use client';

import { useStartCheckout } from '@/lib/hooks';
import { Button } from '@snowforge/ui';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

export default function OnboardingCheckoutPage() {
  const searchParams = useSearchParams();
  const cancelled = searchParams.get('cancelled') === '1';

  const startCheckout = useStartCheckout();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-xl w-full bg-card border border-border rounded-lg p-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Start your 14-day Pro trial</h1>
          <p className="text-muted-foreground">
            Card required. We won&apos;t charge you until day 15. Cancel anytime.
          </p>
        </div>

        <ul className="space-y-2">
          {[
            '25,000 pages/month',
            'JS rendering + proxy rotation',
            'Webhook delivery',
            '5 concurrent jobs',
          ].map((feature) => (
            <li key={feature} className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              {feature}
            </li>
          ))}
        </ul>

        {cancelled && (
          <div className="bg-muted p-3 rounded text-sm text-muted-foreground">
            You cancelled the checkout. Try again whenever you&apos;re ready.
          </div>
        )}

        <Button
          size="lg"
          className="w-full"
          disabled={startCheckout.isPending}
          onClick={() =>
            startCheckout.mutate({ plan: 'pro', interval: 'month', is_trial: true })
          }
        >
          {startCheckout.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Redirecting to Stripe…
            </>
          ) : (
            'Start trial — continue to Stripe'
          )}
        </Button>

        {startCheckout.isError && (
          <div className="text-sm text-destructive">
            Couldn&apos;t start checkout. Please try again or contact support.
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          By continuing you agree to our{' '}
          <a href="/terms-conditions" className="underline">terms</a> and{' '}
          <a href="/privacy-policy" className="underline">privacy policy</a>.
        </p>
      </div>
    </div>
  );
}
