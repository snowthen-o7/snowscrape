/**
 * Pricing Card
 * Card component for displaying pricing plans
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Check } from 'lucide-react';
import Link from 'next/link';

interface PricingCardProps {
  name: string;
  price: string | number;
  description: string;
  features: string[];
  cta: string;
  ctaHref: string;
  popular?: boolean;
  variant?: 'default' | 'accent';
}

export function PricingCard({
  name,
  price,
  description,
  features,
  cta,
  ctaHref,
  popular = false,
  variant = 'default',
}: PricingCardProps) {
  return (
    <Card
      className={`relative h-full ${
        popular
          ? 'border-2 border-accent ring-2 ring-brand-accent/20'
          : 'border-border'
      }`}
    >
      {popular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-accent px-4 py-1 text-sm font-semibold text-primary">
          Most Popular
        </div>
      )}

      <CardContent className="p-8">
        <h3 className="text-2xl font-bold text-foreground">{name}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>

        <div className="mt-6 flex items-baseline gap-x-2">
          {typeof price === 'number' ? (
            <>
              <span className="text-5xl font-bold tracking-tight text-foreground">
                ${price}
              </span>
              <span className="text-sm text-muted-foreground">/month</span>
            </>
          ) : (
            <span className="text-5xl font-bold tracking-tight text-foreground">
              {price}
            </span>
          )}
        </div>

        <ul className="mt-8 space-y-3">
          {features.map((feature, index) => (
            <li key={index} className="flex gap-x-3 text-sm text-muted-foreground">
              <Check className="h-5 w-5 flex-none text-accent-foreground" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>

        <Button
          className={`mt-8 w-full ${
            variant === 'accent'
              ? 'bg-accent text-primary hover:bg-accent/90'
              : ''
          }`}
          variant={variant === 'accent' ? 'default' : 'outline'}
          asChild
        >
          <Link href={ctaHref}>{cta}</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
