/**
 * Templates Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function TemplatesPage() {
  return (
    <DocLayout
      title="Using Templates"
      description="Get started quickly with pre-built scraping templates for popular websites."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          Templates are pre-configured scraping jobs for popular websites and use cases. They include
          tested queries, optimal rate limits, and recommended settings - saving you hours of configuration.
        </p>

        <h2 className="text-2xl font-bold mt-8">Why Use Templates?</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-green-500">Faster Setup</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Skip the trial and error of writing queries. Templates are tested and ready to use.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-green-500">Best Practices</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Templates include recommended rate limits and settings for reliable scraping.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-green-500">Regular Updates</h4>
            <p className="text-sm text-muted-foreground mt-2">
              We update templates when websites change their structure.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-green-500">Fully Customizable</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Start from a template and modify it to fit your specific needs.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">Available Categories</h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 mt-4">
          <div className="rounded-lg border border-border p-4">
            <h4 className="font-semibold">E-Commerce</h4>
            <p className="text-sm text-muted-foreground">Amazon, eBay, Shopify stores</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <h4 className="font-semibold">Social Media</h4>
            <p className="text-sm text-muted-foreground">LinkedIn, Twitter, Instagram</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <h4 className="font-semibold">Real Estate</h4>
            <p className="text-sm text-muted-foreground">Zillow, Realtor, Redfin</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <h4 className="font-semibold">Job Boards</h4>
            <p className="text-sm text-muted-foreground">Indeed, LinkedIn Jobs, Glassdoor</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <h4 className="font-semibold">News & Media</h4>
            <p className="text-sm text-muted-foreground">Google News, RSS feeds, news sites</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <h4 className="font-semibold">Business Data</h4>
            <p className="text-sm text-muted-foreground">Yellow Pages, Yelp, Google Maps</p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">How to Use Templates</h2>
        <ol className="list-decimal list-inside space-y-3 text-muted-foreground ml-4">
          <li>Navigate to <strong>Templates</strong> in the sidebar</li>
          <li>Browse or search for a template that matches your needs</li>
          <li>Click <strong>Use Template</strong> to create a new job</li>
          <li>Customize the job name and source URLs</li>
          <li>Optionally modify queries or settings</li>
          <li>Save and run your job</li>
        </ol>

        <h2 className="text-2xl font-bold mt-8">Template Structure</h2>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <h4 className="font-semibold mb-2">Example: Amazon Product Template</h4>
          <pre className="text-sm overflow-x-auto bg-card p-3 rounded border border-border">
{`{
  "name": "Amazon Product",
  "description": "Extract product details from Amazon product pages",
  "source_pattern": "https://www.amazon.com/dp/{ASIN}",
  "queries": [
    {
      "name": "title",
      "type": "xpath",
      "query": "//span[@id='productTitle']/text()"
    },
    {
      "name": "price",
      "type": "xpath",
      "query": "//span[@class='a-price-whole']/text()"
    },
    {
      "name": "rating",
      "type": "css",
      "query": "#acrPopover span.a-size-base::text"
    },
    {
      "name": "reviews_count",
      "type": "xpath",
      "query": "//span[@id='acrCustomerReviewText']/text()"
    },
    {
      "name": "availability",
      "type": "xpath",
      "query": "//div[@id='availability']//span/text()"
    }
  ],
  "rate_limit": 5,
  "render_config": {
    "enabled": true,
    "wait_strategy": "domcontentloaded"
  }
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Creating Your Own Templates</h2>
        <p className="text-muted-foreground">
          Save any job configuration as a template to reuse later:
        </p>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground ml-4 mt-4">
          <li>Create and test a job until it works correctly</li>
          <li>Open the job settings</li>
          <li>Click <strong>Save as Template</strong></li>
          <li>Give it a name and description</li>
          <li>Choose to keep it private or share with your team</li>
        </ol>

        <div className="rounded-lg border border-brand-accent/30 bg-brand-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-brand-accent mb-2">Pro Tip</h3>
          <p className="text-muted-foreground">
            Templates with placeholder patterns like <code className="bg-muted px-1 rounded">&#123;ASIN&#125;</code> or
            <code className="bg-muted px-1 rounded">&#123;SKU&#125;</code> make it easy to scrape multiple items -
            just replace the placeholder with your target values.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Template Limitations</h2>
        <p className="text-muted-foreground">
          Keep in mind that websites change frequently. If a template stops working:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4 mt-4">
          <li>Check for template updates in the marketplace</li>
          <li>Inspect the target page to find new selectors</li>
          <li>Report broken templates to help us update them</li>
        </ul>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/dashboard/templates"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Browse Templates</h4>
            <p className="text-sm text-muted-foreground mt-1">Explore available templates</p>
          </Link>
          <Link
            href="/docs/queries"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Query Types</h4>
            <p className="text-sm text-muted-foreground mt-1">Learn to write your own queries</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
