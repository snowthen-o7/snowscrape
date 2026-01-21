/**
 * Template Detail Page
 * View template details and use it to create a new job
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft,
  Star,
  Download,
  ExternalLink,
  Code,
  FileJson,
  Info,
  CheckCircle2,
  Copy,
} from 'lucide-react';
import { toast } from '@/lib/toast';

// Template configurations (in production, these would come from a database or CMS)
const TEMPLATE_CONFIGS: any = {
  'amazon-product': {
    name: 'Amazon Product Scraper',
    description:
      'Extract comprehensive product details from Amazon including prices, reviews, ratings, availability, and specifications',
    category: 'E-commerce',
    difficulty: 'Easy',
    rating: 4.8,
    usageCount: 1250,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-15',
    queries: [
      { name: 'product_title', type: 'xpath', query: '//h1[@id="title"]/span/text()' },
      { name: 'price', type: 'xpath', query: '//span[@class="a-price-whole"]/text()' },
      { name: 'rating', type: 'xpath', query: '//span[@class="a-icon-alt"]/text()' },
      {
        name: 'review_count',
        type: 'xpath',
        query: '//span[@id="acrCustomerReviewText"]/text()',
      },
      { name: 'availability', type: 'xpath', query: '//div[@id="availability"]/span/text()' },
      {
        name: 'description',
        type: 'xpath',
        query: '//div[@id="feature-bullets"]//li/span/text()',
      },
    ],
    sampleData: [
      {
        product_title: 'Apple AirPods Pro (2nd Generation)',
        price: '249.00',
        rating: '4.7 out of 5 stars',
        review_count: '85,429',
        availability: 'In Stock',
        description: 'Active Noise Cancellation, Transparency mode, Adaptive Audio...',
      },
    ],
    usageNotes: [
      'Set rate_limit to 2-3 to avoid Amazon rate limiting',
      'Enable proxy rotation for high-volume scraping',
      'JavaScript rendering is not required for product pages',
      'Schedule during off-peak hours for better performance',
    ],
    compatibleSites: ['amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr'],
  },
  'linkedin-profile': {
    name: 'LinkedIn Profile Extractor',
    description:
      'Scrape professional profiles from LinkedIn including employment history, education, skills, and recommendations',
    category: 'Social Media',
    difficulty: 'Medium',
    rating: 4.6,
    usageCount: 890,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-12',
    queries: [
      { name: 'full_name', type: 'xpath', query: '//h1[@class="text-heading-xlarge"]/text()' },
      { name: 'headline', type: 'xpath', query: '//div[@class="text-body-medium"]/text()' },
      { name: 'location', type: 'xpath', query: '//span[@class="text-body-small"]/text()' },
      {
        name: 'current_company',
        type: 'xpath',
        query: '//div[@class="pv-entity__company-summary-info"]/h3/span[2]/text()',
      },
      {
        name: 'current_position',
        type: 'xpath',
        query: '//h3[@class="t-16 t-black t-bold"]/text()',
      },
    ],
    sampleData: [
      {
        full_name: 'John Doe',
        headline: 'Senior Software Engineer at Tech Corp',
        location: 'San Francisco, CA',
        current_company: 'Tech Corp',
        current_position: 'Senior Software Engineer',
      },
    ],
    usageNotes: [
      'LinkedIn requires authentication - use authenticated sessions',
      'Enable JavaScript rendering (dynamic content)',
      'Set rate_limit to 1 to avoid account restrictions',
      'Use residential proxies for better success rate',
      'Respect LinkedIn Terms of Service and robots.txt',
    ],
    compatibleSites: ['linkedin.com'],
  },
  'real-estate-zillow': {
    name: 'Zillow Real Estate Listings',
    description:
      'Extract property details from Zillow including prices, square footage, bedrooms, bathrooms, and location data',
    category: 'Real Estate',
    difficulty: 'Medium',
    rating: 4.7,
    usageCount: 720,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-10',
    queries: [
      { name: 'address', type: 'xpath', query: '//h1[@class="ds-address-container"]/text()' },
      { name: 'price', type: 'xpath', query: '//span[@class="ds-value"]/text()' },
      { name: 'bedrooms', type: 'xpath', query: '//span[@class="ds-bed"]/text()' },
      { name: 'bathrooms', type: 'xpath', query: '//span[@class="ds-bath"]/text()' },
      { name: 'sqft', type: 'xpath', query: '//span[@class="ds-sqft"]/text()' },
      { name: 'description', type: 'xpath', query: '//div[@class="ds-overview-section"]/text()' },
    ],
    sampleData: [
      {
        address: '123 Main St, San Francisco, CA 94110',
        price: '$1,250,000',
        bedrooms: '3 bd',
        bathrooms: '2 ba',
        sqft: '1,850 sqft',
        description: 'Beautiful Victorian home in the heart of the Mission District...',
      },
    ],
    usageNotes: [
      'Zillow uses dynamic content - enable JavaScript rendering',
      'Set appropriate delays to avoid rate limiting',
      'Property pages are publicly accessible',
      'Consider using proxies for large-scale scraping',
    ],
    compatibleSites: ['zillow.com'],
  },
};

export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { session } = useSession();
  const templateId = params.templateId as string;

  const template = TEMPLATE_CONFIGS[templateId];
  const [copiedQuery, setCopiedQuery] = useState<string | null>(null);

  if (!template) {
    return (
      <AppLayout>
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-2">Template not found</h2>
            <p className="text-muted-foreground mb-4">
              The template you're looking for doesn't exist.
            </p>
            <Button onClick={() => router.push('/dashboard/templates')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Templates
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  const handleUseTemplate = async () => {
    try {
      if (!session) {
        toast.error('Please sign in to use templates');
        return;
      }

      // In production, this would create a job with the template configuration
      toast.success(`Creating job from template: ${template.name}`);

      // Navigate to dashboard where JobModal would open with template data
      router.push('/dashboard');
    } catch (error) {
      console.error('Error using template', error);
      toast.error('Failed to use template');
    }
  };

  const copyQuery = (query: string, index: number) => {
    navigator.clipboard.writeText(query);
    setCopiedQuery(`${index}`);
    toast.success('Query copied to clipboard');
    setTimeout(() => setCopiedQuery(null), 2000);
  };

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push('/dashboard/templates')}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Templates
        </Button>

        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">{template.name}</h1>
              <Badge variant="outline" className="text-brand-accent border-brand-accent">
                Official
              </Badge>
            </div>
            <p className="text-lg text-muted-foreground">{template.description}</p>
          </div>
          <Button size="lg" onClick={handleUseTemplate}>
            <ExternalLink className="mr-2 h-5 w-5" />
            Use Template
          </Button>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Rating</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-1">
                <Star className="h-5 w-5 fill-yellow-500 text-yellow-500" />
                <span className="text-2xl font-bold">{template.rating}</span>
                <span className="text-muted-foreground">/5</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Uses</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Download className="h-5 w-5 text-brand-accent" />
                <span className="text-2xl font-bold">
                  {template.usageCount.toLocaleString()}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Difficulty</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge
                variant="outline"
                className={
                  template.difficulty === 'Easy'
                    ? 'border-green-600 text-green-600 text-lg'
                    : template.difficulty === 'Medium'
                    ? 'border-yellow-600 text-yellow-600 text-lg'
                    : 'border-red-600 text-red-600 text-lg'
                }
              >
                {template.difficulty}
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Category</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="secondary" className="text-lg">
                {template.category}
              </Badge>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">
              <Info className="mr-2 h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="queries">
              <Code className="mr-2 h-4 w-4" />
              Queries
            </TabsTrigger>
            <TabsTrigger value="sample">
              <FileJson className="mr-2 h-4 w-4" />
              Sample Data
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Template Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm text-muted-foreground">Author</p>
                    <p className="font-medium">{template.author}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="font-medium">
                      {new Date(template.lastUpdated).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Queries</p>
                    <p className="font-medium">{template.queries.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Compatible Sites</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {template.compatibleSites.map((site: string, index: number) => (
                        <Badge key={index} variant="outline">
                          {site}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Usage Notes</CardTitle>
                <CardDescription>
                  Important tips and best practices for using this template
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {template.usageNotes.map((note: string, index: number) => (
                    <li key={index} className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{note}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Queries Tab */}
          <TabsContent value="queries">
            <Card>
              <CardHeader>
                <CardTitle>Query Configuration</CardTitle>
                <CardDescription>
                  Extraction queries included in this template
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {template.queries.map((query: any, index: number) => (
                    <div
                      key={index}
                      className="rounded-lg border border-border p-4 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{query.name}</span>
                          <Badge variant="outline">{query.type.toUpperCase()}</Badge>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyQuery(query.query, index)}
                        >
                          {copiedQuery === `${index}` ? (
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                      <code className="block rounded bg-muted p-3 text-xs overflow-x-auto">
                        {query.query}
                      </code>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Sample Data Tab */}
          <TabsContent value="sample">
            <Card>
              <CardHeader>
                <CardTitle>Sample Output</CardTitle>
                <CardDescription>
                  Example data extracted using this template
                </CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="rounded-lg bg-muted p-4 overflow-x-auto text-xs">
                  {JSON.stringify(template.sampleData, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Bottom CTA */}
        <Card className="border-brand-accent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold mb-1">Ready to get started?</h3>
                <p className="text-sm text-muted-foreground">
                  Use this template to create a new job with pre-configured queries
                </p>
              </div>
              <Button size="lg" onClick={handleUseTemplate}>
                <ExternalLink className="mr-2 h-5 w-5" />
                Use Template
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
