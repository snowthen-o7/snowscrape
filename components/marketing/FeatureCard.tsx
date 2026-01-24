/**
 * Feature Card
 * Card component for displaying features
 */

import { Card, CardContent } from '@snowforge/ui';
import { LucideIcon } from 'lucide-react';

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function FeatureCard({ icon: Icon, title, description }: FeatureCardProps) {
  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur transition-all hover:border-brand-accent/50 hover:shadow-lg hover:shadow-brand-accent/10">
      <CardContent className="p-6">
        <div className="mb-4 inline-flex rounded-lg bg-brand-accent/10 p-3">
          <Icon className="h-6 w-6 text-brand-accent" />
        </div>
        <h3 className="mb-2 text-xl font-semibold text-foreground">{title}</h3>
        <p className="text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
