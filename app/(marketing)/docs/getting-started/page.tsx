/**
 * Getting Started Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function GettingStartedPage() {
  return (
    <DocLayout
      title="Getting Started"
      description="Learn how to set up your SnowScrape account and create your first scraping job in minutes."
    >
      <section className="space-y-6">
        <div className="rounded-lg border border-border bg-muted/30 p-6">
          <h3 className="text-lg font-semibold mb-2">Prerequisites</h3>
          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
            <li>A SnowScrape account (sign up at snowscrape.com)</li>
            <li>Basic understanding of HTML structure</li>
            <li>Target website URLs you want to scrape</li>
          </ul>
        </div>

        <h2 className="text-2xl font-bold mt-8">Step 1: Create Your Account</h2>
        <p className="text-muted-foreground">
          Visit <Link href="/sign-up" className="text-brand-accent hover:underline">snowscrape.com/sign-up</Link> to
          create your free account. You can sign up with your email or use Google/GitHub authentication for quick access.
        </p>

        <h2 className="text-2xl font-bold mt-8">Step 2: Access Your Dashboard</h2>
        <p className="text-muted-foreground">
          Once logged in, you&apos;ll be directed to your dashboard. This is your command center for managing all
          scraping jobs, viewing analytics, and configuring settings.
        </p>
        <div className="rounded-lg border border-border p-4 bg-card">
          <h4 className="font-semibold mb-2">Dashboard Overview</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
            <li><strong>Stats Cards</strong> - Quick overview of your jobs (total, running, successful, failed)</li>
            <li><strong>Charts</strong> - API usage and data volume trends</li>
            <li><strong>Quick Actions</strong> - Fast navigation to common tasks</li>
            <li><strong>Activity Summary</strong> - Success rate and job status breakdown</li>
          </ul>
        </div>

        <h2 className="text-2xl font-bold mt-8">Step 3: Create Your First Job</h2>
        <p className="text-muted-foreground">
          Click the <strong>&quot;New Job&quot;</strong> button in the sidebar to create your first scraping job. You&apos;ll need to provide:
        </p>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground ml-4">
          <li><strong>Job Name</strong> - A descriptive name for your job (e.g., &quot;Product Prices&quot;)</li>
          <li><strong>Source URL</strong> - The website URL you want to scrape</li>
          <li><strong>Extraction Queries</strong> - Define what data to extract using XPath, CSS selectors, or regex</li>
          <li><strong>Schedule (optional)</strong> - Set up recurring scrapes</li>
        </ol>

        <div className="rounded-lg border border-brand-accent/30 bg-brand-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-brand-accent mb-2">Pro Tip</h3>
          <p className="text-muted-foreground">
            Start with a simple job that extracts just one or two data points. Once you understand how queries work,
            you can add more complex extraction rules.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Step 4: Run and Monitor</h2>
        <p className="text-muted-foreground">
          After creating your job, it will start automatically (or on schedule if configured). Monitor progress in real-time
          from the Jobs page. You&apos;ll see:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
          <li><strong>Status</strong> - Running, Success, Failed, Paused, or Scheduled</li>
          <li><strong>Progress</strong> - Number of URLs processed</li>
          <li><strong>Results</strong> - Preview extracted data</li>
        </ul>

        <h2 className="text-2xl font-bold mt-8">Step 5: Export Your Data</h2>
        <p className="text-muted-foreground">
          Once your job completes, download results in your preferred format:
        </p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
          {['JSON', 'CSV', 'Excel', 'Parquet', 'SQL'].map((format) => (
            <div key={format} className="rounded-lg border border-border p-3 text-center bg-card">
              <span className="font-mono text-sm">{format}</span>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/creating-jobs"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Creating Jobs</h4>
            <p className="text-sm text-muted-foreground mt-1">Learn job configuration in detail</p>
          </Link>
          <Link
            href="/docs/queries"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Query Types</h4>
            <p className="text-sm text-muted-foreground mt-1">Master XPath, CSS, and Regex selectors</p>
          </Link>
          <Link
            href="/docs/templates"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Using Templates</h4>
            <p className="text-sm text-muted-foreground mt-1">Start faster with pre-built templates</p>
          </Link>
          <Link
            href="/docs/api/authentication"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">API Access</h4>
            <p className="text-sm text-muted-foreground mt-1">Integrate SnowScrape with your apps</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
