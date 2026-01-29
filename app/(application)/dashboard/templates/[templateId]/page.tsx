/**
 * Template Detail Page
 * View template details and use it to create a new job
 */

'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@snowforge/ui';
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
import { JobModal } from '@/components/JobModal';
import { Job } from '@/lib/types';

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
  'google-serp': {
    name: 'Google Search Results',
    description:
      'Scrape Google search results including organic listings, featured snippets, and related searches',
    category: 'SEO',
    difficulty: 'Easy',
    rating: 4.9,
    usageCount: 2100,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-18',
    queries: [
      { name: 'title', type: 'xpath', query: '//h3[@class="LC20lb"]/text()' },
      { name: 'url', type: 'xpath', query: '//div[@class="yuRUbf"]/a/@href' },
      { name: 'description', type: 'xpath', query: '//div[@class="VwiC3b"]/span/text()' },
      { name: 'position', type: 'xpath', query: 'count(preceding::div[@class="g"])+1' },
      {
        name: 'featured_snippet',
        type: 'xpath',
        query: '//div[@class="xpdopen"]//span/text()',
      },
    ],
    sampleData: [
      {
        title: 'Web Scraping - Wikipedia',
        url: 'https://en.wikipedia.org/wiki/Web_scraping',
        description: 'Web scraping, web harvesting, or web data extraction is data scraping used for extracting data from websites...',
        position: 1,
        featured_snippet: null,
      },
    ],
    usageNotes: [
      'Google frequently changes their DOM structure - verify selectors',
      'Use proxies to avoid IP blocking',
      'Respect rate limits (1-2 requests per second max)',
      'Consider using Google Search API for production use',
      'JavaScript rendering may be required for some results',
    ],
    compatibleSites: ['google.com', 'google.co.uk', 'google.de', 'google.fr'],
  },
  'news-articles': {
    name: 'News Article Scraper',
    description:
      'Extract article content, headlines, author information, and publication dates from news websites',
    category: 'Content',
    difficulty: 'Easy',
    rating: 4.5,
    usageCount: 650,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-08',
    queries: [
      { name: 'headline', type: 'xpath', query: '//h1/text()' },
      { name: 'author', type: 'xpath', query: '//span[@class="byline"]//text()' },
      { name: 'publish_date', type: 'xpath', query: '//time/@datetime' },
      { name: 'content', type: 'xpath', query: '//article//p/text()' },
      { name: 'category', type: 'xpath', query: '//meta[@property="article:section"]/@content' },
    ],
    sampleData: [
      {
        headline: 'Tech Giants Report Record Earnings',
        author: 'Jane Smith',
        publish_date: '2026-01-20T10:30:00Z',
        content: 'Major technology companies announced quarterly results that exceeded...',
        category: 'Technology',
      },
    ],
    usageNotes: [
      'Works best with standard article page structures',
      'Selectors may need adjustment for different news sites',
      'Some sites require JavaScript rendering',
      'Respect robots.txt and copyright considerations',
    ],
    compatibleSites: ['Most news websites with standard HTML structure'],
  },
  'job-listings-indeed': {
    name: 'Indeed Job Listings',
    description:
      'Extract job postings from Indeed including title, company, location, salary, and full job description',
    category: 'Jobs',
    difficulty: 'Medium',
    rating: 4.6,
    usageCount: 980,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-14',
    queries: [
      { name: 'job_title', type: 'xpath', query: '//h1[@class="jobsearch-JobInfoHeader-title"]/text()' },
      { name: 'company', type: 'xpath', query: '//div[@data-company-name="true"]/a/text()' },
      { name: 'location', type: 'xpath', query: '//div[@data-testid="job-location"]/text()' },
      { name: 'salary', type: 'xpath', query: '//div[@id="salaryInfoAndJobType"]/span/text()' },
      { name: 'description', type: 'xpath', query: '//div[@id="jobDescriptionText"]//text()' },
      { name: 'posted_date', type: 'xpath', query: '//span[@class="date"]/text()' },
    ],
    sampleData: [
      {
        job_title: 'Senior Software Engineer',
        company: 'Tech Corp Inc.',
        location: 'San Francisco, CA',
        salary: '$150,000 - $200,000 a year',
        description: 'We are looking for an experienced software engineer to join our team...',
        posted_date: 'Posted 3 days ago',
      },
    ],
    usageNotes: [
      'Indeed uses dynamic content - enable JavaScript rendering',
      'Set rate_limit to 1-2 to avoid blocking',
      'Job listings change frequently, schedule regular scrapes',
      'Some content may require authentication',
      'Consider using Indeed API for commercial use',
    ],
    compatibleSites: ['indeed.com', 'indeed.co.uk', 'indeed.ca'],
  },
  'event-listings': {
    name: 'Event Listings Scraper',
    description:
      'Extract event details from platforms like Eventbrite including name, date, venue, and ticket information',
    category: 'Events',
    difficulty: 'Easy',
    rating: 4.4,
    usageCount: 430,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-05',
    queries: [
      { name: 'event_name', type: 'xpath', query: '//h1[@class="event-title"]/text()' },
      { name: 'date', type: 'xpath', query: '//time[@class="event-date"]/@datetime' },
      { name: 'venue', type: 'xpath', query: '//div[@class="location-info"]//p/text()' },
      { name: 'price', type: 'xpath', query: '//div[@class="ticket-price"]/text()' },
      { name: 'organizer', type: 'xpath', query: '//a[@class="organizer-name"]/text()' },
      { name: 'description', type: 'xpath', query: '//div[@class="event-description"]//text()' },
    ],
    sampleData: [
      {
        event_name: 'Tech Conference 2026',
        date: '2026-03-15T09:00:00Z',
        venue: 'Moscone Center, San Francisco, CA',
        price: '$299 - $899',
        organizer: 'TechEvents Inc.',
        description: 'Join us for the biggest tech conference of the year...',
      },
    ],
    usageNotes: [
      'Works with Eventbrite and similar event platforms',
      'Event data changes frequently as events sell out',
      'Some events require login to view ticket prices',
      'Consider timezone handling for event dates',
    ],
    compatibleSites: ['eventbrite.com', 'meetup.com'],
  },
  'stock-market-data': {
    name: 'Stock Market Data',
    description:
      'Scrape stock prices, market cap, volume, P/E ratio, and other financial metrics from Yahoo Finance',
    category: 'Finance',
    difficulty: 'Medium',
    rating: 4.7,
    usageCount: 1120,
    author: 'SnowScrape Team',
    lastUpdated: '2026-01-17',
    queries: [
      { name: 'symbol', type: 'xpath', query: '//h1[@class="D(ib) Fz(18px)"]/text()' },
      { name: 'price', type: 'xpath', query: '//fin-streamer[@data-field="regularMarketPrice"]/@value' },
      { name: 'change', type: 'xpath', query: '//fin-streamer[@data-field="regularMarketChange"]/@value' },
      { name: 'change_percent', type: 'xpath', query: '//fin-streamer[@data-field="regularMarketChangePercent"]/@value' },
      { name: 'market_cap', type: 'xpath', query: '//td[@data-test="MARKET_CAP-value"]/text()' },
      { name: 'volume', type: 'xpath', query: '//td[@data-test="TD_VOLUME-value"]/text()' },
      { name: 'pe_ratio', type: 'xpath', query: '//td[@data-test="PE_RATIO-value"]/text()' },
    ],
    sampleData: [
      {
        symbol: 'AAPL',
        price: '187.44',
        change: '+2.35',
        change_percent: '+1.27%',
        market_cap: '2.91T',
        volume: '48,234,521',
        pe_ratio: '29.45',
      },
    ],
    usageNotes: [
      'Yahoo Finance uses dynamic JavaScript - enable rendering',
      'Data updates in real-time during market hours',
      'For historical data, use separate API endpoints',
      'Consider financial data licensing for commercial use',
      'Rate limit carefully to avoid IP blocks',
    ],
    compatibleSites: ['finance.yahoo.com', 'google.com/finance'],
  },
};

export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { session } = useSession();
  const templateId = params.templateId as string;

  const template = TEMPLATE_CONFIGS[templateId];
  const [copiedQuery, setCopiedQuery] = useState<string | null>(null);
  const [showJobModal, setShowJobModal] = useState(false);

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

  const handleUseTemplate = () => {
    if (!session) {
      toast.error('Please sign in to use templates');
      return;
    }

    // Open the job modal with template data pre-filled
    setShowJobModal(true);
  };

  // Create a Job-like object from template data for the modal
  const getTemplateAsJobData = (): Partial<Job> | null => {
    if (!template) return null;

    return {
      name: `${template.name} Job`,
      rate_limit: 2,
      source: template.compatibleSites?.[0] ? `https://${template.compatibleSites[0]}` : '',
      queries: template.queries.map((q: any) => ({
        name: q.name,
        type: q.type,
        query: q.query,
        join: false,
      })),
      file_mapping: { delimiter: ',', enclosure: '', escape: '', url_column: '' },
      scheduling: { days: [], hours: [], minutes: [] },
      proxy_config: {
        enabled: false,
        geo_targeting: 'any',
        rotation_strategy: 'random',
        max_retries: 3,
        fallback_to_direct: true,
      },
      render_config: {
        enabled: template.difficulty === 'Medium' || template.difficulty === 'Hard',
        wait_strategy: 'networkidle',
        wait_timeout_ms: 30000,
        wait_for_selector: null,
        capture_screenshot: false,
        screenshot_full_page: false,
        block_resources: [],
        fallback_to_standard: true,
      },
      export_config: {
        enabled: false,
        formats: ['json'],
        destination: 's3',
        s3_bucket: null,
        webhook_url: null,
        include_screenshots: false,
        compress: false,
      },
      notification_config: {
        enabled: false,
        email_on_success: false,
        email_on_failure: true,
        email_addresses: [],
        webhook_on_success: false,
        webhook_on_failure: true,
        webhook_url: null,
      },
    };
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
              <Badge variant="outline" className="text-accent-foreground border-accent">
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
                <Download className="h-5 w-5 text-accent-foreground" />
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
        <Card className="border-accent">
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

      {/* Job Modal with template data pre-filled */}
      {showJobModal && (
        <JobModal
          closeModal={() => setShowJobModal(false)}
          jobDetails={getTemplateAsJobData() as Job | null}
          session={session ?? null}
        />
      )}
    </AppLayout>
  );
}
