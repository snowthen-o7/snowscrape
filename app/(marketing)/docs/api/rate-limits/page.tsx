/**
 * Rate Limits Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function RateLimitsPage() {
  return (
    <DocLayout
      title="Rate Limits & Quotas"
      description="Understand API rate limits and how to work within them effectively."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          SnowScrape enforces rate limits to ensure fair usage and platform stability. Understanding
          these limits helps you design applications that work reliably.
        </p>

        <h2 className="text-2xl font-bold mt-8">API Rate Limits</h2>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Plan</th>
                <th className="text-left p-3 font-semibold">Requests/Minute</th>
                <th className="text-left p-3 font-semibold">Requests/Day</th>
                <th className="text-left p-3 font-semibold">Concurrent Jobs</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-semibold">Free</td>
                <td className="p-3 text-muted-foreground">60</td>
                <td className="p-3 text-muted-foreground">1,000</td>
                <td className="p-3 text-muted-foreground">2</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-semibold">Starter</td>
                <td className="p-3 text-muted-foreground">120</td>
                <td className="p-3 text-muted-foreground">10,000</td>
                <td className="p-3 text-muted-foreground">5</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-semibold">Pro</td>
                <td className="p-3 text-muted-foreground">300</td>
                <td className="p-3 text-muted-foreground">50,000</td>
                <td className="p-3 text-muted-foreground">10</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-semibold">Enterprise</td>
                <td className="p-3 text-muted-foreground">Custom</td>
                <td className="p-3 text-muted-foreground">Custom</td>
                <td className="p-3 text-muted-foreground">Custom</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Rate Limit Headers</h2>
        <p className="text-muted-foreground">
          Every API response includes headers to help you track your usage:
        </p>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705766400`}
          </pre>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Header</th>
                <th className="text-left p-3 font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">X-RateLimit-Limit</td>
                <td className="p-3 text-muted-foreground">Maximum requests allowed per window</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">X-RateLimit-Remaining</td>
                <td className="p-3 text-muted-foreground">Requests remaining in current window</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">X-RateLimit-Reset</td>
                <td className="p-3 text-muted-foreground">Unix timestamp when the window resets</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Handling Rate Limits</h2>
        <p className="text-muted-foreground">
          When you exceed the rate limit, the API returns a <code className="bg-muted px-1 rounded">429 Too Many Requests</code> response:
        </p>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": "rate_limited",
  "message": "API rate limit exceeded. Please retry after 60 seconds.",
  "retry_after": 60
}`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Retry with Exponential Backoff</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`async function requestWithRetry(url, options, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const response = await fetch(url, options);

    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After') || 60;
      const delay = Math.min(retryAfter * 1000, Math.pow(2, attempt) * 1000);

      console.log(\`Rate limited. Retrying in \${delay}ms...\`);
      await new Promise(resolve => setTimeout(resolve, delay));
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Scraping Rate Limits</h2>
        <p className="text-muted-foreground">
          In addition to API limits, job execution has separate rate controls:
        </p>
        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <h4 className="font-semibold mb-2">Per-Job Rate Limit</h4>
          <p className="text-sm text-muted-foreground">
            Set via <code className="bg-muted px-1 rounded">rate_limit</code> in job config. Controls how fast
            SnowScrape makes requests to target websites (requests per minute).
          </p>
        </div>
        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <h4 className="font-semibold mb-2">Global Scrape Limits</h4>
          <p className="text-sm text-muted-foreground">
            Total pages scraped per day across all jobs. Varies by plan.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Usage Quotas</h2>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Resource</th>
                <th className="text-left p-3 font-semibold">Free</th>
                <th className="text-left p-3 font-semibold">Starter</th>
                <th className="text-left p-3 font-semibold">Pro</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3">Pages/month</td>
                <td className="p-3 text-muted-foreground">1,000</td>
                <td className="p-3 text-muted-foreground">25,000</td>
                <td className="p-3 text-muted-foreground">100,000</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">JS Rendering pages</td>
                <td className="p-3 text-muted-foreground">100</td>
                <td className="p-3 text-muted-foreground">5,000</td>
                <td className="p-3 text-muted-foreground">25,000</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Data storage</td>
                <td className="p-3 text-muted-foreground">100 MB</td>
                <td className="p-3 text-muted-foreground">5 GB</td>
                <td className="p-3 text-muted-foreground">50 GB</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Data retention</td>
                <td className="p-3 text-muted-foreground">7 days</td>
                <td className="p-3 text-muted-foreground">30 days</td>
                <td className="p-3 text-muted-foreground">90 days</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Best Practices</h2>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground ml-4">
          <li>
            <strong>Batch operations</strong> - Create multiple jobs in one request when possible
          </li>
          <li>
            <strong>Use webhooks</strong> - Instead of polling for job status, use webhooks
          </li>
          <li>
            <strong>Cache responses</strong> - Store results locally to avoid re-downloading
          </li>
          <li>
            <strong>Monitor usage</strong> - Track rate limit headers to avoid hitting limits
          </li>
          <li>
            <strong>Implement backoff</strong> - Always handle 429 responses gracefully
          </li>
        </ul>

        <div className="rounded-lg border border-accent/30 bg-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-accent-foreground mb-2">Need Higher Limits?</h3>
          <p className="text-muted-foreground">
            Contact our sales team for Enterprise plans with custom rate limits and dedicated resources.
            <Link href="/contact" className="text-accent-foreground hover:underline ml-1">Get in touch →</Link>
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/api/authentication"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Authentication</h4>
            <p className="text-sm text-muted-foreground mt-1">Set up API authentication</p>
          </Link>
          <Link
            href="/pricing"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Pricing</h4>
            <p className="text-sm text-muted-foreground mt-1">Compare plan limits and features</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
