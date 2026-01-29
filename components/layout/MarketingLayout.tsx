import React from 'react';
import { MarketingHeader, MarketingFooter, cn } from '@snowforge/ui';

interface MarketingLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function MarketingLayout({ children, className }: MarketingLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingHeader
        brandName="SnowScrape"
        logoSrc="/logo.png"
        navigation={[
          { name: 'Features', href: '/features' },
          { name: 'Pricing', href: '/pricing' },
          { name: 'Docs', href: '/docs' },
          { name: 'Blog', href: '/blog' },
        ]}
        primaryCtaText="Start Free Trial"
        primaryCtaHref="/sign-up"
      />
      <main className={cn('flex-1', className)}>
        {children}
      </main>
      <MarketingFooter
        brandName="SnowScrape"
        logoSrc="/logo.png"
        tagline="Web Scraping Made Simple"
        productLinks={[
          { name: 'Features', href: '/features' },
          { name: 'Pricing', href: '/pricing' },
          { name: 'Use Cases', href: '/use-cases' },
          { name: 'Templates', href: '/#templates' },
        ]}
        resourceLinks={[
          { name: 'Documentation', href: '/docs' },
          { name: 'API Reference', href: '/docs/api' },
          { name: 'Blog', href: '/blog' },
          { name: 'Support', href: '/contact' },
        ]}
        companyLinks={[
          { name: 'About', href: '/about' },
          { name: 'Contact', href: '/contact' },
          { name: 'Privacy Policy', href: '/privacy-policy' },
          { name: 'Terms of Service', href: '/terms-conditions' },
        ]}
      />
    </div>
  );
}
