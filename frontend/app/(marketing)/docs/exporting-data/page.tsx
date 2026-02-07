/**
 * Exporting Data Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function ExportingDataPage() {
  return (
    <DocLayout
      title="Exporting Data"
      description="Download your scraped data in multiple formats and integrate with your existing tools."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          SnowScrape supports multiple export formats to fit your workflow. Each format has its advantages
          depending on your use case.
        </p>

        <h2 className="text-2xl font-bold mt-8">Available Formats</h2>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mt-6">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">JSON</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Best for APIs and web applications. Preserves data types and nested structures.
            </p>
            <code className="text-xs bg-muted px-2 py-1 rounded mt-2 block">.json</code>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">CSV</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Universal format for spreadsheets. Compatible with Excel, Google Sheets, databases.
            </p>
            <code className="text-xs bg-muted px-2 py-1 rounded mt-2 block">.csv</code>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">Excel</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Native Excel format with formatting. Supports multiple sheets and formulas.
            </p>
            <code className="text-xs bg-muted px-2 py-1 rounded mt-2 block">.xlsx</code>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">Parquet</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Columnar format for big data. Efficient for analytics and data warehouses.
            </p>
            <code className="text-xs bg-muted px-2 py-1 rounded mt-2 block">.parquet</code>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">SQL</h4>
            <p className="text-sm text-muted-foreground mt-2">
              SQL INSERT statements for direct database import. Supports MySQL, PostgreSQL, SQLite.
            </p>
            <code className="text-xs bg-muted px-2 py-1 rounded mt-2 block">.sql</code>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">How to Export</h2>

        <h3 className="text-xl font-semibold mt-6">From the Dashboard</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground ml-4">
          <li>Navigate to the <strong>Jobs</strong> page</li>
          <li>Find your completed job</li>
          <li>Click the <strong>Download</strong> button (or use the dropdown menu)</li>
          <li>Select your preferred format</li>
          <li>The file will download automatically</li>
        </ol>

        <h3 className="text-xl font-semibold mt-6">Via API</h3>
        <p className="text-muted-foreground">
          Use the Jobs API to programmatically download results:
        </p>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <pre className="text-sm overflow-x-auto">
{`GET /api/jobs/{job_id}/download?format=json

# Response: File download with appropriate content-type

# Available formats: json, csv, xlsx, parquet, sql`}
          </pre>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          <Link href="/docs/api/jobs" className="text-accent-foreground hover:underline">
            See full API documentation →
          </Link>
        </p>

        <h2 className="text-2xl font-bold mt-8">Format Comparison</h2>

        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Format</th>
                <th className="text-left p-3 font-semibold">File Size</th>
                <th className="text-left p-3 font-semibold">Read Speed</th>
                <th className="text-left p-3 font-semibold">Best For</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">JSON</td>
                <td className="p-3 text-muted-foreground">Medium</td>
                <td className="p-3 text-muted-foreground">Fast</td>
                <td className="p-3 text-muted-foreground">APIs, web apps, nested data</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">CSV</td>
                <td className="p-3 text-muted-foreground">Small</td>
                <td className="p-3 text-muted-foreground">Fast</td>
                <td className="p-3 text-muted-foreground">Spreadsheets, simple data</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">Excel</td>
                <td className="p-3 text-muted-foreground">Medium</td>
                <td className="p-3 text-muted-foreground">Medium</td>
                <td className="p-3 text-muted-foreground">Business reports, sharing</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">Parquet</td>
                <td className="p-3 text-muted-foreground">Smallest</td>
                <td className="p-3 text-muted-foreground">Fastest</td>
                <td className="p-3 text-muted-foreground">Big data, analytics</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">SQL</td>
                <td className="p-3 text-muted-foreground">Large</td>
                <td className="p-3 text-muted-foreground">N/A</td>
                <td className="p-3 text-muted-foreground">Direct DB import</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Webhook Delivery</h2>
        <p className="text-muted-foreground">
          Instead of downloading manually, configure webhooks to automatically send data when a job completes:
        </p>

        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <h4 className="font-semibold mb-2">Webhook Payload Example</h4>
          <pre className="text-sm overflow-x-auto">
{`{
  "event": "job.completed",
  "job_id": "job_abc123",
  "job_name": "Product Prices",
  "status": "success",
  "results_count": 150,
  "download_url": "https://api.snowscrape.com/jobs/job_abc123/download",
  "completed_at": "2024-01-20T15:30:00Z"
}`}
          </pre>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          <Link href="/docs/api/webhooks" className="text-accent-foreground hover:underline">
            Learn how to set up webhooks →
          </Link>
        </p>

        <h2 className="text-2xl font-bold mt-8">Data Integrations</h2>
        <p className="text-muted-foreground">
          SnowScrape integrates with popular tools and platforms:
        </p>

        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Google Sheets</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Automatically sync results to a Google Sheet for easy sharing and collaboration.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Airtable</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Push scraped data directly to Airtable bases for database-like organization.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Amazon S3</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Store results in your S3 bucket for long-term archival and big data pipelines.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Zapier</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Connect to 5,000+ apps and automate workflows when scrapes complete.
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-accent/30 bg-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-accent-foreground mb-2">Need a Different Format?</h3>
          <p className="text-muted-foreground">
            Contact our support team if you need a format we don&apos;t currently support. We&apos;re always looking
            to expand our export capabilities based on user feedback.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/api/webhooks"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Webhooks</h4>
            <p className="text-sm text-muted-foreground mt-1">Automate data delivery with webhooks</p>
          </Link>
          <Link
            href="/docs/api/jobs"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Jobs API</h4>
            <p className="text-sm text-muted-foreground mt-1">Programmatic access to your data</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
