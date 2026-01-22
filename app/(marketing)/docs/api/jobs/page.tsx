/**
 * Jobs API Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function JobsAPIPage() {
  return (
    <DocLayout
      title="Jobs API"
      description="Complete reference for the Jobs API endpoints to create, manage, and monitor scraping jobs."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          The Jobs API allows you to programmatically create, update, and manage scraping jobs. All endpoints
          require authentication via Bearer token.
        </p>

        <div className="rounded-lg border border-border p-4 bg-card">
          <h4 className="font-semibold mb-2">Base URL</h4>
          <code className="text-brand-accent font-mono">https://api.snowscrape.com</code>
        </div>

        <h2 className="text-2xl font-bold mt-8">Endpoints Overview</h2>

        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Method</th>
                <th className="text-left p-3 font-semibold">Endpoint</th>
                <th className="text-left p-3 font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-green-500/20 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-xs font-mono">GET</span></td>
                <td className="p-3 font-mono">/jobs/status</td>
                <td className="p-3 text-muted-foreground">List all jobs</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-green-500/20 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-xs font-mono">GET</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;</td>
                <td className="p-3 text-muted-foreground">Get job details</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-blue-500/20 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded text-xs font-mono">POST</span></td>
                <td className="p-3 font-mono">/jobs</td>
                <td className="p-3 text-muted-foreground">Create a new job</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 px-2 py-0.5 rounded text-xs font-mono">PUT</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;</td>
                <td className="p-3 text-muted-foreground">Update a job</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-red-500/20 text-red-600 dark:text-red-400 px-2 py-0.5 rounded text-xs font-mono">DELETE</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;</td>
                <td className="p-3 text-muted-foreground">Delete a job</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-blue-500/20 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded text-xs font-mono">POST</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;/run</td>
                <td className="p-3 text-muted-foreground">Trigger job immediately</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-blue-500/20 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded text-xs font-mono">POST</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;/pause</td>
                <td className="p-3 text-muted-foreground">Pause a running job</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-blue-500/20 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded text-xs font-mono">POST</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;/resume</td>
                <td className="p-3 text-muted-foreground">Resume a paused job</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-green-500/20 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-xs font-mono">GET</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;/results</td>
                <td className="p-3 text-muted-foreground">Get job results</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="bg-green-500/20 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-xs font-mono">GET</span></td>
                <td className="p-3 font-mono">/jobs/&#123;id&#125;/download</td>
                <td className="p-3 text-muted-foreground">Download results as file</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">List All Jobs</h2>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-green-500/20 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-sm font-mono">GET</span>
            <code className="font-mono">/jobs/status</code>
          </div>
          <p className="text-muted-foreground text-sm mb-4">
            Returns a list of all jobs for the authenticated user.
          </p>
          <h5 className="font-semibold text-sm mb-2">Response</h5>
          <pre className="text-sm overflow-x-auto bg-card p-3 rounded border border-border">
{`{
  "jobs": [
    {
      "job_id": "job_abc123",
      "name": "Product Scraper",
      "source": "https://example.com/products",
      "status": "success",
      "created_at": "2024-01-15T10:00:00Z",
      "last_run": "2024-01-20T14:30:00Z",
      "results_count": 150
    }
  ],
  "count": 1
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Create a Job</h2>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-blue-500/20 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded text-sm font-mono">POST</span>
            <code className="font-mono">/jobs</code>
          </div>
          <p className="text-muted-foreground text-sm mb-4">
            Creates a new scraping job with the specified configuration.
          </p>
          <h5 className="font-semibold text-sm mb-2">Request Body</h5>
          <pre className="text-sm overflow-x-auto bg-card p-3 rounded border border-border">
{`{
  "name": "Product Prices",
  "source": "https://example.com/products",
  "rate_limit": 10,
  "queries": [
    {
      "name": "title",
      "type": "xpath",
      "query": "//h1[@class='product-title']/text()"
    },
    {
      "name": "price",
      "type": "css",
      "query": ".price-value::text"
    }
  ],
  "scheduling": {
    "days": [1, 2, 3, 4, 5],
    "hours": [9],
    "minutes": [0]
  },
  "render_config": {
    "enabled": true,
    "wait_strategy": "networkidle",
    "wait_timeout_ms": 5000
  },
  "proxy_config": {
    "enabled": true,
    "rotation_strategy": "round-robin",
    "geo_targeting": "US"
  }
}`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Request Parameters</h3>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Parameter</th>
                <th className="text-left p-3 font-semibold">Type</th>
                <th className="text-left p-3 font-semibold">Required</th>
                <th className="text-left p-3 font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">name</td>
                <td className="p-3 text-muted-foreground">string</td>
                <td className="p-3 text-green-500">Yes</td>
                <td className="p-3 text-muted-foreground">Job display name</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">source</td>
                <td className="p-3 text-muted-foreground">string</td>
                <td className="p-3 text-green-500">Yes</td>
                <td className="p-3 text-muted-foreground">URL to scrape</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">queries</td>
                <td className="p-3 text-muted-foreground">array</td>
                <td className="p-3 text-green-500">Yes</td>
                <td className="p-3 text-muted-foreground">Data extraction queries</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">rate_limit</td>
                <td className="p-3 text-muted-foreground">number</td>
                <td className="p-3 text-muted-foreground">No</td>
                <td className="p-3 text-muted-foreground">Requests per minute (default: 10)</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">scheduling</td>
                <td className="p-3 text-muted-foreground">object</td>
                <td className="p-3 text-muted-foreground">No</td>
                <td className="p-3 text-muted-foreground">Cron-like schedule config</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">render_config</td>
                <td className="p-3 text-muted-foreground">object</td>
                <td className="p-3 text-muted-foreground">No</td>
                <td className="p-3 text-muted-foreground">JavaScript rendering options</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">proxy_config</td>
                <td className="p-3 text-muted-foreground">object</td>
                <td className="p-3 text-muted-foreground">No</td>
                <td className="p-3 text-muted-foreground">Proxy rotation settings</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Download Results</h2>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-green-500/20 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-sm font-mono">GET</span>
            <code className="font-mono">/jobs/&#123;id&#125;/download?format=json</code>
          </div>
          <p className="text-muted-foreground text-sm mb-4">
            Downloads job results in the specified format.
          </p>
          <h5 className="font-semibold text-sm mb-2">Query Parameters</h5>
          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
            <li><code className="bg-muted px-1 rounded">format</code>: json, csv, xlsx, parquet, sql</li>
          </ul>
        </div>

        <h2 className="text-2xl font-bold mt-8">Job Status Values</h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 mt-4">
          <div className="flex items-center gap-2 p-3 rounded-lg border border-border">
            <span className="w-3 h-3 rounded-full bg-blue-500"></span>
            <span className="font-mono text-sm">running</span>
            <span className="text-muted-foreground text-sm ml-auto">Job is executing</span>
          </div>
          <div className="flex items-center gap-2 p-3 rounded-lg border border-border">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="font-mono text-sm">success</span>
            <span className="text-muted-foreground text-sm ml-auto">Completed successfully</span>
          </div>
          <div className="flex items-center gap-2 p-3 rounded-lg border border-border">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            <span className="font-mono text-sm">failed</span>
            <span className="text-muted-foreground text-sm ml-auto">Execution failed</span>
          </div>
          <div className="flex items-center gap-2 p-3 rounded-lg border border-border">
            <span className="w-3 h-3 rounded-full bg-amber-500"></span>
            <span className="font-mono text-sm">paused</span>
            <span className="text-muted-foreground text-sm ml-auto">Manually paused</span>
          </div>
          <div className="flex items-center gap-2 p-3 rounded-lg border border-border">
            <span className="w-3 h-3 rounded-full bg-gray-500"></span>
            <span className="font-mono text-sm">scheduled</span>
            <span className="text-muted-foreground text-sm ml-auto">Waiting for schedule</span>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">Error Responses</h2>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`// 400 Bad Request
{
  "error": "validation_error",
  "message": "Invalid query configuration",
  "details": {
    "queries[0].type": "Must be one of: xpath, css, regex"
  }
}

// 404 Not Found
{
  "error": "not_found",
  "message": "Job not found"
}

// 429 Too Many Requests
{
  "error": "rate_limited",
  "message": "API rate limit exceeded",
  "retry_after": 60
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Code Examples</h2>

        <h3 className="text-xl font-semibold mt-6">Create and Run a Job (Python)</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`import requests
import os

API_KEY = os.environ['SNOWSCRAPE_API_KEY']
BASE_URL = 'https://api.snowscrape.com'

# Create a job
job_config = {
    "name": "Example Scraper",
    "source": "https://example.com/page",
    "queries": [
        {"name": "title", "type": "xpath", "query": "//h1/text()"},
        {"name": "content", "type": "css", "query": "article p::text", "join": True}
    ]
}

response = requests.post(
    f'{BASE_URL}/jobs',
    json=job_config,
    headers={'Authorization': f'Bearer {API_KEY}'}
)

job = response.json()
print(f"Created job: {job['job_id']}")

# Trigger the job
requests.post(
    f'{BASE_URL}/jobs/{job["job_id"]}/run',
    headers={'Authorization': f'Bearer {API_KEY}'}
)`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/api/webhooks"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Webhooks</h4>
            <p className="text-sm text-muted-foreground mt-1">Get notified when jobs complete</p>
          </Link>
          <Link
            href="/docs/api/rate-limits"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Rate Limits</h4>
            <p className="text-sm text-muted-foreground mt-1">Understand API usage quotas</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
