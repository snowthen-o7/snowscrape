/**
 * API Authentication Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function APIAuthenticationPage() {
  return (
    <DocLayout
      title="API Authentication"
      description="Learn how to authenticate your API requests to SnowScrape."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          SnowScrape uses Bearer token authentication for all API requests. Your token is generated when you
          log in and can be retrieved from your account settings.
        </p>

        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-6">
          <h3 className="text-lg font-semibold text-amber-600 dark:text-amber-400 mb-2">Security Notice</h3>
          <p className="text-muted-foreground">
            Keep your API token secure. Never share it publicly or commit it to version control.
            If your token is compromised, regenerate it immediately from your account settings.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Getting Your API Token</h2>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground ml-4">
          <li>Log in to your SnowScrape account</li>
          <li>Navigate to <strong>Settings → API Keys</strong></li>
          <li>Click <strong>Generate New Key</strong></li>
          <li>Copy your token and store it securely</li>
        </ol>

        <h2 className="text-2xl font-bold mt-8">Making Authenticated Requests</h2>
        <p className="text-muted-foreground">
          Include your token in the <code className="bg-muted px-1 rounded">Authorization</code> header of every request:
        </p>

        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <h4 className="font-semibold mb-2">Header Format</h4>
          <pre className="text-sm overflow-x-auto">
{`Authorization: Bearer YOUR_API_TOKEN`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Example: cURL</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`curl -X GET "https://api.snowscrape.com/jobs/status" \\
  -H "Authorization: Bearer sk_live_abc123..." \\
  -H "Content-Type: application/json"`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Example: JavaScript (fetch)</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`const response = await fetch('https://api.snowscrape.com/jobs/status', {
  method: 'GET',
  headers: {
    'Authorization': \`Bearer \${process.env.SNOWSCRAPE_API_KEY}\`,
    'Content-Type': 'application/json',
  },
});

const data = await response.json();`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Example: Python (requests)</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`import os
import requests

api_key = os.environ.get('SNOWSCRAPE_API_KEY')

response = requests.get(
    'https://api.snowscrape.com/jobs/status',
    headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
)

data = response.json()`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">API Base URL</h2>
        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <code className="text-brand-accent font-mono">https://api.snowscrape.com</code>
          <p className="text-sm text-muted-foreground mt-2">
            All API endpoints are relative to this base URL.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Token Types</h2>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Token Prefix</th>
                <th className="text-left p-3 font-semibold">Environment</th>
                <th className="text-left p-3 font-semibold">Usage</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">sk_live_</td>
                <td className="p-3 text-muted-foreground">Production</td>
                <td className="p-3 text-muted-foreground">Use in production applications</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">sk_test_</td>
                <td className="p-3 text-muted-foreground">Testing</td>
                <td className="p-3 text-muted-foreground">For development and testing</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Error Responses</h2>
        <p className="text-muted-foreground">
          Authentication errors return specific HTTP status codes:
        </p>

        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Status Code</th>
                <th className="text-left p-3 font-semibold">Meaning</th>
                <th className="text-left p-3 font-semibold">Solution</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-500">401</td>
                <td className="p-3 text-muted-foreground">Unauthorized</td>
                <td className="p-3 text-muted-foreground">Token missing or invalid format</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-500">403</td>
                <td className="p-3 text-muted-foreground">Forbidden</td>
                <td className="p-3 text-muted-foreground">Token valid but lacks permission</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <h4 className="font-semibold mb-2">Error Response Example</h4>
          <pre className="text-sm overflow-x-auto">
{`{
  "error": "unauthorized",
  "message": "Invalid or expired API token",
  "status": 401
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Best Practices</h2>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground ml-4">
          <li>Store API tokens in environment variables, never hardcode them</li>
          <li>Use test tokens (<code className="bg-muted px-1 rounded">sk_test_</code>) during development</li>
          <li>Rotate tokens periodically for security</li>
          <li>Monitor your API usage in the dashboard for unusual activity</li>
          <li>Use separate tokens for different applications or environments</li>
        </ul>

        <div className="rounded-lg border border-brand-accent/30 bg-brand-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-brand-accent mb-2">Using Environment Variables</h3>
          <p className="text-muted-foreground mb-4">
            Store your token securely using environment variables:
          </p>
          <pre className="text-sm overflow-x-auto bg-card p-3 rounded border border-border">
{`# .env file (never commit this!)
SNOWSCRAPE_API_KEY=sk_live_abc123...

# Access in your code
process.env.SNOWSCRAPE_API_KEY  # Node.js
os.environ['SNOWSCRAPE_API_KEY']  # Python`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/api/jobs"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Jobs API</h4>
            <p className="text-sm text-muted-foreground mt-1">Create and manage jobs via API</p>
          </Link>
          <Link
            href="/docs/api/rate-limits"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Rate Limits</h4>
            <p className="text-sm text-muted-foreground mt-1">Understand API usage limits</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
