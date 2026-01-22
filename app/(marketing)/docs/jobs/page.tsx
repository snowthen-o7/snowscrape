/**
 * Understanding Jobs Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function JobsConceptPage() {
  return (
    <DocLayout
      title="Understanding Jobs"
      description="Learn how scraping jobs work in SnowScrape and their lifecycle."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          A <strong>job</strong> is the fundamental unit of work in SnowScrape. It defines what to scrape,
          how to extract data, and when to run. Understanding jobs is essential for effective web scraping.
        </p>

        <h2 className="text-2xl font-bold mt-8">Job Anatomy</h2>
        <p className="text-muted-foreground">
          Every job consists of these core components:
        </p>

        <div className="grid gap-4 md:grid-cols-2 mt-6">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Source</h4>
            <p className="text-sm text-muted-foreground mt-2">
              The URL(s) to scrape. Can be a single page, a list of URLs, or a pattern with pagination.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Queries</h4>
            <p className="text-sm text-muted-foreground mt-2">
              XPath, CSS, or Regex patterns that define what data to extract from each page.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Schedule</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Optional configuration for when the job should run automatically.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Configuration</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Advanced options like rate limiting, proxy settings, and JavaScript rendering.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">Job Lifecycle</h2>
        <p className="text-muted-foreground">
          Jobs progress through various states during their lifecycle:
        </p>

        <div className="rounded-lg border border-border p-6 bg-card mt-4">
          <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gray-500/20 flex items-center justify-center">
                <span className="text-xs font-bold">1</span>
              </div>
              <span className="font-medium">Created</span>
            </div>
            <div className="hidden md:block text-muted-foreground">→</div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gray-500/20 flex items-center justify-center">
                <span className="text-xs font-bold">2</span>
              </div>
              <span className="font-medium">Scheduled</span>
            </div>
            <div className="hidden md:block text-muted-foreground">→</div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                <span className="text-xs font-bold">3</span>
              </div>
              <span className="font-medium">Running</span>
            </div>
            <div className="hidden md:block text-muted-foreground">→</div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="text-xs font-bold">4</span>
              </div>
              <span className="font-medium">Success/Failed</span>
            </div>
          </div>
        </div>

        <h3 className="text-xl font-semibold mt-6">Status Definitions</h3>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Status</th>
                <th className="text-left p-3 font-semibold">Description</th>
                <th className="text-left p-3 font-semibold">Next Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-gray-500"></span>Scheduled</span></td>
                <td className="p-3 text-muted-foreground">Waiting for scheduled time</td>
                <td className="p-3 text-muted-foreground">Run now, Edit, Delete</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500"></span>Running</span></td>
                <td className="p-3 text-muted-foreground">Currently executing</td>
                <td className="p-3 text-muted-foreground">Pause, View Progress</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber-500"></span>Paused</span></td>
                <td className="p-3 text-muted-foreground">Manually paused</td>
                <td className="p-3 text-muted-foreground">Resume, Delete</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-green-500"></span>Success</span></td>
                <td className="p-3 text-muted-foreground">Completed successfully</td>
                <td className="p-3 text-muted-foreground">Download, Run Again</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500"></span>Failed</span></td>
                <td className="p-3 text-muted-foreground">Execution failed</td>
                <td className="p-3 text-muted-foreground">View Logs, Retry, Edit</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Job Execution</h2>
        <p className="text-muted-foreground">
          When a job runs, SnowScrape performs these steps:
        </p>
        <ol className="list-decimal list-inside space-y-3 text-muted-foreground ml-4 mt-4">
          <li>
            <strong>URL Resolution</strong> - Expands URL patterns and loads URL lists
          </li>
          <li>
            <strong>Request Queuing</strong> - Creates a queue of pages to scrape with rate limiting
          </li>
          <li>
            <strong>Page Fetching</strong> - Downloads each page (with optional JS rendering)
          </li>
          <li>
            <strong>Data Extraction</strong> - Applies queries to extract structured data
          </li>
          <li>
            <strong>Result Storage</strong> - Saves extracted data to your account
          </li>
          <li>
            <strong>Webhook Notification</strong> - Sends completion notification (if configured)
          </li>
        </ol>

        <h2 className="text-2xl font-bold mt-8">Job Types</h2>

        <h3 className="text-xl font-semibold mt-6">One-Time Jobs</h3>
        <p className="text-muted-foreground">
          Run once manually or triggered via API. Good for ad-hoc data collection.
        </p>

        <h3 className="text-xl font-semibold mt-6">Scheduled Jobs</h3>
        <p className="text-muted-foreground">
          Run automatically on a schedule. Perfect for monitoring prices, tracking changes,
          or collecting data at regular intervals.
        </p>

        <h3 className="text-xl font-semibold mt-6">Template-Based Jobs</h3>
        <p className="text-muted-foreground">
          Created from pre-built templates for popular websites. Fastest way to get started
          with proven configurations.
        </p>

        <div className="rounded-lg border border-brand-accent/30 bg-brand-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-brand-accent mb-2">Best Practice</h3>
          <p className="text-muted-foreground">
            Start with a small test run (one or two URLs) to verify your queries work correctly
            before running a full scrape on hundreds of pages.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/creating-jobs"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Creating Jobs</h4>
            <p className="text-sm text-muted-foreground mt-1">Step-by-step job creation guide</p>
          </Link>
          <Link
            href="/docs/scheduling"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Scheduling</h4>
            <p className="text-sm text-muted-foreground mt-1">Set up recurring scrapes</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
