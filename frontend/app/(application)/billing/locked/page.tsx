/**
 * Billing Locked Page
 * Shown when subscription is past_due, canceled, incomplete, etc.
 * One CTA → POST /billing/portal → Stripe Customer Portal.
 */

'use client';

import { useOpenPortal } from '@/lib/hooks';
import { Button } from '@snowforge/ui';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

const REASON_COPY: Record<string, { title: string; body: string }> = {
  payment_failed: {
    title: 'Your payment failed',
    body: 'Update your payment method to keep using SnowScrape.',
  },
  canceled: {
    title: 'Your subscription was canceled',
    body: 'Resubscribe to keep using SnowScrape. Your existing data is safe.',
  },
  default: {
    title: 'Your account is on hold',
    body: 'Manage your subscription to continue.',
  },
};

export default function BillingLockedPage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get('reason') ?? 'default';
  const copy = REASON_COPY[reason] ?? REASON_COPY.default;

  const openPortal = useOpenPortal();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-xl w-full bg-card border border-border rounded-lg p-8 space-y-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-destructive" />
          <h1 className="text-2xl font-bold">{copy.title}</h1>
        </div>
        <p className="text-muted-foreground">{copy.body}</p>

        <Button
          size="lg"
          className="w-full"
          disabled={openPortal.isPending}
          onClick={() => openPortal.mutate()}
        >
          {openPortal.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Opening Stripe…
            </>
          ) : (
            'Manage subscription'
          )}
        </Button>

        {openPortal.isError && (
          <div className="text-sm text-destructive">
            Couldn&apos;t open the customer portal. Please try again.
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Need help? Email{' '}
          <a href="mailto:alex@snowforge.dev" className="underline">
            alex@snowforge.dev
          </a>.
        </p>
      </div>
    </div>
  );
}
