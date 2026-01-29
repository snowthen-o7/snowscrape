/**
 * Creating Jobs Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function CreatingJobsPage() {
  return (
    <DocLayout
      title="Creating Jobs"
      description="Learn how to configure scraping jobs with all available options and best practices."
    >
      <section className="space-y-6">
        <h2 className="text-2xl font-bold">Job Configuration Overview</h2>
        <p className="text-muted-foreground">
          A scraping job in SnowScrape consists of several components that work together to extract data from websites.
          Understanding each component helps you create efficient and reliable scrapers.
        </p>

        <h2 className="text-2xl font-bold mt-8">Basic Configuration</h2>

        <h3 className="text-xl font-semibold mt-6">Job Name</h3>
        <p className="text-muted-foreground">
          Choose a descriptive name that helps you identify the job later. Good naming conventions include:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
          <li><code className="text-sm bg-muted px-1 rounded">Amazon - Product Prices - Electronics</code></li>
          <li><code className="text-sm bg-muted px-1 rounded">LinkedIn - Job Postings - Software Engineer</code></li>
          <li><code className="text-sm bg-muted px-1 rounded">News Site - Headlines - Daily</code></li>
        </ul>

        <h3 className="text-xl font-semibold mt-6">Source URL</h3>
        <p className="text-muted-foreground">
          The URL of the page you want to scrape. SnowScrape supports:
        </p>
        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>Single URLs</strong> - Scrape one page (e.g., <code className="bg-muted px-1 rounded">https://example.com/product/123</code>)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>URL Lists</strong> - Upload a CSV file with multiple URLs to scrape</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>Dynamic URLs</strong> - Use pagination patterns like <code className="bg-muted px-1 rounded">page=[1-100]</code></span>
            </li>
          </ul>
        </div>

        <h2 className="text-2xl font-bold mt-8">Extraction Queries</h2>
        <p className="text-muted-foreground">
          Queries define what data to extract from each page. Each query has:
        </p>

        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Field</th>
                <th className="text-left p-3 font-semibold">Description</th>
                <th className="text-left p-3 font-semibold">Example</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              <tr className="border-b border-border">
                <td className="p-3 font-mono">name</td>
                <td className="p-3 text-muted-foreground">Column name in output</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">product_title</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">type</td>
                <td className="p-3 text-muted-foreground">Query language</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">xpath</code>, <code className="bg-muted px-1 rounded">css</code>, <code className="bg-muted px-1 rounded">regex</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">query</td>
                <td className="p-3 text-muted-foreground">The selector expression</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">//h1[@class=&apos;title&apos;]/text()</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">join</td>
                <td className="p-3 text-muted-foreground">Combine multiple matches</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">true</code> or <code className="bg-muted px-1 rounded">false</code></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <h4 className="font-semibold mb-2">Example Query Configuration</h4>
          <pre className="text-sm overflow-x-auto p-4 bg-card rounded border border-border">
{`{
  "queries": [
    {
      "name": "title",
      "type": "xpath",
      "query": "//h1[@id='product-title']/text()"
    },
    {
      "name": "price",
      "type": "css",
      "query": ".price-value::text"
    },
    {
      "name": "description",
      "type": "xpath",
      "query": "//div[@class='description']//text()",
      "join": true
    }
  ]
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Rate Limiting</h2>
        <p className="text-muted-foreground">
          Control how fast SnowScrape makes requests to avoid overwhelming target servers or getting blocked.
        </p>
        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <h4 className="font-semibold mb-2">Recommended Settings</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li><strong>Low traffic sites:</strong> 10-20 requests/minute</li>
            <li><strong>Medium traffic sites:</strong> 5-10 requests/minute</li>
            <li><strong>High traffic / protected sites:</strong> 1-3 requests/minute</li>
          </ul>
        </div>

        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-amber-600 dark:text-amber-400 mb-2">Important</h3>
          <p className="text-muted-foreground">
            Always respect the target website&apos;s <code className="bg-muted px-1 rounded">robots.txt</code> and terms of service.
            Aggressive scraping can lead to IP blocks or legal issues.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Scheduling</h2>
        <p className="text-muted-foreground">
          Set up recurring scrapes to keep your data fresh. SnowScrape supports flexible scheduling:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
          <li><strong>Days</strong> - Select which days of the week to run</li>
          <li><strong>Hours</strong> - Choose specific hours (24-hour format)</li>
          <li><strong>Minutes</strong> - Fine-tune the exact minute</li>
        </ul>

        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <h4 className="font-semibold mb-2">Schedule Examples</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li><strong>Daily at 9 AM:</strong> Days: [0-6], Hours: [9], Minutes: [0]</li>
            <li><strong>Weekdays at 6 PM:</strong> Days: [1-5], Hours: [18], Minutes: [0]</li>
            <li><strong>Every 6 hours:</strong> Days: [0-6], Hours: [0, 6, 12, 18], Minutes: [0]</li>
          </ul>
        </div>

        <h2 className="text-2xl font-bold mt-8">Advanced Options</h2>

        <h3 className="text-xl font-semibold mt-6">JavaScript Rendering</h3>
        <p className="text-muted-foreground">
          Enable this for websites that load content dynamically with JavaScript. SnowScrape will use a headless
          browser to render the page before extracting data.
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          <Link href="/docs/javascript-rendering" className="text-accent-foreground hover:underline">
            Learn more about JavaScript rendering →
          </Link>
        </p>

        <h3 className="text-xl font-semibold mt-6">Proxy Configuration</h3>
        <p className="text-muted-foreground">
          Use proxies to avoid IP blocks and access geo-restricted content. Options include:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
          <li><strong>Rotation Strategy</strong> - Round-robin, random, or sticky sessions</li>
          <li><strong>Geo-targeting</strong> - Route requests through specific countries</li>
          <li><strong>Automatic Retries</strong> - Retry failed requests with different proxies</li>
        </ul>
        <p className="text-sm text-muted-foreground mt-2">
          <Link href="/docs/proxy-rotation" className="text-accent-foreground hover:underline">
            Learn more about proxy rotation →
          </Link>
        </p>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/queries"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Query Types</h4>
            <p className="text-sm text-muted-foreground mt-1">Deep dive into XPath, CSS, and Regex</p>
          </Link>
          <Link
            href="/docs/exporting-data"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Exporting Data</h4>
            <p className="text-sm text-muted-foreground mt-1">Download and integrate your scraped data</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
