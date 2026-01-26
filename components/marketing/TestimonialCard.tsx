/**
 * Testimonial Card
 * Card component for displaying customer testimonials
 */

import { Card, CardContent } from '@/components/ui/card';
import { Star } from 'lucide-react';

interface TestimonialCardProps {
  quote: string;
  author: string;
  role: string;
  company: string;
  rating?: number;
}

export function TestimonialCard({
  quote,
  author,
  role,
  company,
  rating = 5,
}: TestimonialCardProps) {
  return (
    <Card className="h-full border-border/50 bg-card/50 backdrop-blur">
      <CardContent className="p-6">
        {/* Stars */}
        <div className="mb-4 flex gap-1">
          {Array.from({ length: rating }).map((_, i) => (
            <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
          ))}
        </div>

        {/* Quote */}
        <blockquote className="mb-6 text-foreground">
          &ldquo;{quote}&rdquo;
        </blockquote>

        {/* Author */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-sm font-semibold text-accent-foreground">
            {author.split(' ').map((n) => n[0]).join('')}
          </div>
          <div>
            <div className="font-semibold text-foreground">{author}</div>
            <div className="text-sm text-muted-foreground">
              {role} at {company}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
