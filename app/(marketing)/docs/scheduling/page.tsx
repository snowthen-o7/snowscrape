/**
 * Scheduling Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function SchedulingPage() {
  return (
    <DocLayout
      title="Scheduling & Automation"
      description="Set up automated scraping schedules to keep your data fresh."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          SnowScrape allows you to schedule jobs to run automatically at specific times.
          This is perfect for monitoring prices, tracking inventory, or collecting data at regular intervals.
        </p>

        <h2 className="text-2xl font-bold mt-8">Schedule Configuration</h2>
        <p className="text-muted-foreground">
          Schedules are defined using three components:
        </p>

        <div className="grid gap-4 md:grid-cols-3 mt-6">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Days</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Which days of the week to run (0 = Sunday, 6 = Saturday)
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Hours</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Which hours to run (0-23 in 24-hour format)
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-brand-accent">Minutes</h4>
            <p className="text-sm text-muted-foreground mt-2">
              Which minutes to run (0-59)
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">Common Schedule Examples</h2>

        <div className="space-y-4 mt-4">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Daily at 9 AM</h4>
            <pre className="text-sm bg-muted p-2 rounded mt-2">
{`{
  "days": [0, 1, 2, 3, 4, 5, 6],
  "hours": [9],
  "minutes": [0]
}`}
            </pre>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Weekdays at 6 PM</h4>
            <pre className="text-sm bg-muted p-2 rounded mt-2">
{`{
  "days": [1, 2, 3, 4, 5],
  "hours": [18],
  "minutes": [0]
}`}
            </pre>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Every 6 Hours</h4>
            <pre className="text-sm bg-muted p-2 rounded mt-2">
{`{
  "days": [0, 1, 2, 3, 4, 5, 6],
  "hours": [0, 6, 12, 18],
  "minutes": [0]
}`}
            </pre>
          </div>

          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold">Twice Daily (9 AM and 5 PM)</h4>
            <pre className="text-sm bg-muted p-2 rounded mt-2">
{`{
  "days": [0, 1, 2, 3, 4, 5, 6],
  "hours": [9, 17],
  "minutes": [0]
}`}
            </pre>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">Timezone</h2>
        <p className="text-muted-foreground">
          All schedules run in <strong>UTC timezone</strong>. When setting up schedules, convert your
          local time to UTC. For example:
        </p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4 mt-4">
          <li>9 AM EST = 14:00 UTC (hours: [14])</li>
          <li>6 PM PST = 02:00 UTC next day (hours: [2])</li>
          <li>12 PM GMT = 12:00 UTC (hours: [12])</li>
        </ul>

        <div className="rounded-lg border border-brand-accent/30 bg-brand-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-brand-accent mb-2">Pro Tip</h3>
          <p className="text-muted-foreground">
            Avoid scheduling jobs at exactly midnight (00:00) or common times like the top of the hour.
            Using minutes like :15 or :30 helps distribute load and avoid rate limits from target sites.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Managing Scheduled Jobs</h2>

        <h3 className="text-xl font-semibold mt-6">Pausing Schedules</h3>
        <p className="text-muted-foreground">
          Pause a job to temporarily stop scheduled runs without deleting the configuration.
          The job will remain paused until you resume it.
        </p>

        <h3 className="text-xl font-semibold mt-6">Manual Triggers</h3>
        <p className="text-muted-foreground">
          You can always run a scheduled job manually using the &quot;Run Now&quot; button. This doesn&apos;t
          affect the schedule - the job will still run at its next scheduled time.
        </p>

        <h3 className="text-xl font-semibold mt-6">Overlapping Runs</h3>
        <p className="text-muted-foreground">
          If a previous run is still executing when the next scheduled time arrives, SnowScrape will
          skip the new run and wait for the next scheduled time. This prevents duplicate data and
          excessive resource usage.
        </p>

        <h2 className="text-2xl font-bold mt-8">Best Practices</h2>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground ml-4">
          <li>
            <strong>Match your data freshness needs</strong> - Don&apos;t scrape hourly if daily is sufficient
          </li>
          <li>
            <strong>Consider target site load</strong> - Avoid peak hours for better success rates
          </li>
          <li>
            <strong>Set up alerts</strong> - Configure webhooks to know when scheduled jobs fail
          </li>
          <li>
            <strong>Test first</strong> - Run a job manually to verify it works before scheduling
          </li>
          <li>
            <strong>Monitor costs</strong> - Frequent schedules increase API usage
          </li>
        </ul>

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
            href="/docs/creating-jobs"
            className="rounded-lg border border-border p-4 hover:border-brand-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-brand-accent">Creating Jobs</h4>
            <p className="text-sm text-muted-foreground mt-1">Full job configuration guide</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
