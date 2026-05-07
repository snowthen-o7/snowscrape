/**
 * PricingCTA
 * Routes signed-out users to Clerk sign-up, signed-in users to portal/onboarding.
 */

'use client';

import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Button } from '@snowforge/ui';
import { useSubscription, useOpenPortal } from '@/lib/hooks';

interface Props {
  plan: 'pro' | 'business' | 'enterprise';
  variant?: 'default' | 'outline';
}

export function PricingCTA({ plan, variant = 'default' }: Props) {
  const { isSignedIn, isLoaded } = useUser();
  const router = useRouter();
  const { data: sub } = useSubscription();
  const openPortal = useOpenPortal();

  if (plan === 'enterprise') {
    return (
      <Button
        variant={variant}
        className="w-full"
        onClick={() => {
          window.location.href = 'mailto:alex@snowforge.dev?subject=SnowScrape Enterprise';
        }}
      >
        Contact us
      </Button>
    );
  }

  const label = plan === 'pro' ? 'Start 14-day trial' : 'Choose Business';

  if (!isLoaded) {
    return <Button variant={variant} className="w-full" disabled>Loading…</Button>;
  }

  if (!isSignedIn) {
    return (
      <Button
        variant={variant}
        className="w-full"
        onClick={() => router.push('/sign-up')}
      >
        {label}
      </Button>
    );
  }

  const status = sub?.status;
  const hasActiveSub = status === 'trialing' || status === 'active';

  if (hasActiveSub) {
    return (
      <Button
        variant={variant}
        className="w-full"
        disabled={openPortal.isPending}
        onClick={() => openPortal.mutate()}
      >
        Manage subscription
      </Button>
    );
  }

  return (
    <Button
      variant={variant}
      className="w-full"
      onClick={() => router.push('/onboarding/checkout')}
    >
      {label}
    </Button>
  );
}
