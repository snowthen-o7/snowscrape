/**
 * Webhooks API Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function WebhooksAPIPage() {
  return (
    <DocLayout
      title="Webhooks"
      description="Receive real-time notifications when jobs complete or fail."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          Webhooks allow SnowScrape to send HTTP POST requests to your server when specific events occur.
          This is useful for triggering workflows, updating databases, or sending notifications.
        </p>

        <h2 className="text-2xl font-bold mt-8">Supported Events</h2>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Event</th>
                <th className="text-left p-3 font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">job.completed</td>
                <td className="p-3 text-muted-foreground">Job finished successfully</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">job.failed</td>
                <td className="p-3 text-muted-foreground">Job execution failed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">job.started</td>
                <td className="p-3 text-muted-foreground">Job started executing</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">job.paused</td>
                <td className="p-3 text-muted-foreground">Job was paused</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Webhook Payload</h2>
        <p className="text-muted-foreground">
          All webhook requests include a JSON payload with event details:
        </p>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`{
  "event": "job.completed",
  "timestamp": "2024-01-20T15:30:00Z",
  "data": {
    "job_id": "job_abc123",
    "job_name": "Product Prices",
    "status": "success",
    "results_count": 150,
    "duration_ms": 45000,
    "download_url": "https://api.snowscrape.com/jobs/job_abc123/download"
  }
}`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Failure Payload</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`{
  "event": "job.failed",
  "timestamp": "2024-01-20T15:30:00Z",
  "data": {
    "job_id": "job_abc123",
    "job_name": "Product Prices",
    "status": "failed",
    "error": {
      "code": "TIMEOUT",
      "message": "Request timeout after 30000ms",
      "failed_urls": 12,
      "successful_urls": 138
    }
  }
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Setting Up Webhooks</h2>

        <h3 className="text-xl font-semibold mt-6">Via Dashboard</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground ml-4">
          <li>Go to <strong>Webhooks</strong> in the sidebar</li>
          <li>Click <strong>Create Webhook</strong></li>
          <li>Enter your endpoint URL</li>
          <li>Select which events to subscribe to</li>
          <li>Save and test the webhook</li>
        </ol>

        <h3 className="text-xl font-semibold mt-6">Via API</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`POST /webhooks

{
  "url": "https://your-server.com/webhook",
  "events": ["job.completed", "job.failed"],
  "secret": "your_webhook_secret"
}`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Verifying Webhooks</h2>
        <p className="text-muted-foreground">
          Each webhook request includes a signature header for verification:
        </p>
        <div className="rounded-lg border border-border p-4 bg-card mt-4">
          <code className="font-mono text-sm">X-SnowScrape-Signature: sha256=abc123...</code>
        </div>

        <h3 className="text-xl font-semibold mt-6">Verification Code (Node.js)</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expected = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}`}
          </pre>
        </div>

        <h3 className="text-xl font-semibold mt-6">Verification Code (Python)</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)`}
          </pre>
        </div>

        <h2 className="text-2xl font-bold mt-8">Retry Policy</h2>
        <p className="text-muted-foreground">
          SnowScrape retries failed webhook deliveries with exponential backoff:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4 mt-4">
          <li>First retry: 1 minute after failure</li>
          <li>Second retry: 5 minutes</li>
          <li>Third retry: 30 minutes</li>
          <li>Fourth retry: 2 hours</li>
          <li>Fifth retry (final): 24 hours</li>
        </ul>
        <p className="text-muted-foreground mt-4">
          Webhooks are considered successful if your server returns a 2xx status code within 10 seconds.
        </p>

        <h2 className="text-2xl font-bold mt-8">Best Practices</h2>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground ml-4">
          <li>
            <strong>Respond quickly</strong> - Return 200 immediately, process async
          </li>
          <li>
            <strong>Handle duplicates</strong> - Use the event ID for idempotency
          </li>
          <li>
            <strong>Verify signatures</strong> - Always validate the webhook origin
          </li>
          <li>
            <strong>Use HTTPS</strong> - Webhook URLs must use HTTPS in production
          </li>
          <li>
            <strong>Monitor failures</strong> - Check the webhook logs for delivery issues
          </li>
        </ul>

        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-amber-600 dark:text-amber-400 mb-2">Security Note</h3>
          <p className="text-muted-foreground">
            Never expose your webhook secret. Store it securely in environment variables and
            regenerate it if compromised.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/api/jobs"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Jobs API</h4>
            <p className="text-sm text-muted-foreground mt-1">Manage jobs programmatically</p>
          </Link>
          <Link
            href="/docs/exporting-data"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Exporting Data</h4>
            <p className="text-sm text-muted-foreground mt-1">Download results in various formats</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
