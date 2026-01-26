/**
 * Job Details Page
 * Comprehensive view of a single job with analytics and history
 */

'use client';

import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/EmptyState';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {  } from '@snowforge/ui';
import {
  ArrowLeft,
  Play,
  Pause,
  Download,
  Trash2,
  Clock,
  Calendar,
  TrendingUp,
  DollarSign,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { useJobs, usePauseJob, useResumeJob, useDeleteJob } from '@/lib/hooks/useJobs';
import { useRealtimeJob } from '@/lib/hooks/useRealtimeJobs';
import { StatCard } from '@/components/StatCard';
import { LineChart } from '@/components/charts';
import { toast } from '@/lib/toast';
import { useState } from 'react';
import { ConfirmDialog } from '@/components/ConfirmDialog';

export default function JobDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const { data: jobs = [] } = useJobs();
  const { job: realtimeJob } = useRealtimeJob(jobId, { enabled: !!jobId });

  const job = realtimeJob || jobs.find((j) => j.job_id === jobId);

  const pauseJobMutation = usePauseJob();
  const resumeJobMutation = useResumeJob();
  const deleteJobMutation = useDeleteJob();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Sample analytics data (would come from API in production)
  const runtimeTrends = [
    { date: 'Jan 14', runtime: 12 },
    { date: 'Jan 15', runtime: 15 },
    { date: 'Jan 16', runtime: 11 },
    { date: 'Jan 17', runtime: 14 },
    { date: 'Jan 18', runtime: 13 },
    { date: 'Jan 19', runtime: 10 },
    { date: 'Jan 20', runtime: 12 },
  ];

  const executionHistory = [
    {
      id: '1',
      timestamp: '2026-01-20 14:30:00',
      status: 'success',
      runtime: 12,
      recordsExtracted: 1250,
    },
    {
      id: '2',
      timestamp: '2026-01-19 14:30:00',
      status: 'success',
      runtime: 10,
      recordsExtracted: 1180,
    },
    {
      id: '3',
      timestamp: '2026-01-18 14:30:00',
      status: 'success',
      runtime: 13,
      recordsExtracted: 1320,
    },
    {
      id: '4',
      timestamp: '2026-01-17 14:30:00',
      status: 'failed',
      runtime: 8,
      recordsExtracted: 0,
    },
    {
      id: '5',
      timestamp: '2026-01-16 14:30:00',
      status: 'success',
      runtime: 11,
      recordsExtracted: 1200,
    },
  ];

  const handlePause = async () => {
    try {
      await pauseJobMutation.mutateAsync(jobId);
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleResume = async () => {
    try {
      await resumeJobMutation.mutateAsync(jobId);
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleDelete = async () => {
    try {
      await deleteJobMutation.mutateAsync(jobId);
      router.push('/dashboard');
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleDownload = async (format: string) => {
    try {
      const token = await (window as any).Clerk?.session?.getToken();
      if (!token) {
        toast.error('Not authenticated');
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/download?format=${format}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            ...(process.env.NEXT_PUBLIC_API_KEY && {
              'x-api-key': process.env.NEXT_PUBLIC_API_KEY,
            }),
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to download results');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${jobId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Download started');
    } catch (error) {
      console.error('Error downloading job', error);
      toast.error('Failed to download results');
    }
  };

  if (!job) {
    return (
      <AppLayout>
        <div className="flex min-h-[60vh] items-center justify-center">
          <p className="text-muted-foreground">Loading job details...</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push('/dashboard')}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>

        {/* Page Header */}
        <div className="space-y-4">
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-bold tracking-tight">{job.name}</h1>
                <StatusBadge status={job.status as any} size="md" />
              </div>
              <p className="text-muted-foreground">Job ID: {job.job_id}</p>
            </div>
            <div className="flex gap-2">
              {job.status === 'running' ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePause}
                  disabled={pauseJobMutation.isPending}
                >
                  <Pause className="mr-2 h-4 w-4" />
                  Pause
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleResume}
                  disabled={resumeJobMutation.isPending}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Resume
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownload('json')}
              >
                <Download className="mr-2 h-4 w-4" />
                Download
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Success Rate"
            value="75%"
            icon={<CheckCircle2 className="h-5 w-5" />}
            trend="up"
            change={5}
            changeLabel="vs last week"
          />
          <StatCard
            title="Avg Runtime"
            value="12s"
            icon={<Clock className="h-5 w-5" />}
          />
          <StatCard
            title="Total Runs"
            value="150"
            icon={<TrendingUp className="h-5 w-5" />}
          />
          <StatCard
            title="Est. Cost"
            value="$2.50"
            icon={<DollarSign className="h-5 w-5" />}
            changeLabel="this month"
          />
        </div>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Job Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Job Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Target Source</span>
                    <span className="text-sm font-medium">{job.source}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Schedule</span>
                    <Badge variant="outline">
                      {job.scheduling.days.length > 0
                        ? `${job.scheduling.days.join(', ')} - ${job.scheduling.hours.join(':')}h`
                        : 'Manual'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Created</span>
                    <span className="text-sm">{new Date(job.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Last Run</span>
                    <span className="text-sm">
                      {job.last_run
                        ? new Date(job.last_run).toLocaleString()
                        : 'Never'}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Quick Stats */}
              <Card>
                <CardHeader>
                  <CardTitle>Performance Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm text-muted-foreground">Successful Runs</span>
                    </div>
                    <span className="text-lg font-bold">112</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-600" />
                      <span className="text-sm text-muted-foreground">Failed Runs</span>
                    </div>
                    <span className="text-lg font-bold">38</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-yellow-600" />
                      <span className="text-sm text-muted-foreground">Avg Records/Run</span>
                    </div>
                    <span className="text-lg font-bold">1,240</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Runtime Trends */}
            <Card>
              <CardHeader>
                <CardTitle>Runtime Trends (Last 7 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <LineChart
                  data={runtimeTrends}
                  xDataKey="date"
                  yDataKey="runtime"
                  lineColor="#00D9FF"
                  height={250}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Configuration Tab */}
          <TabsContent value="config" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Query Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {job.queries && job.queries.length > 0 ? (
                  job.queries.map((query, index) => (
                    <div key={index} className="rounded-lg border border-border p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{query.name}</span>
                        <Badge variant="outline">{query.type}</Badge>
                      </div>
                      <code className="block rounded bg-muted p-2 text-xs">
                        {query.query}
                      </code>
                    </div>
                  ))
                ) : (
                  <EmptyState
                    title="No queries configured"
                    description="Add queries to extract data from the target URL"
                  />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Advanced Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">JavaScript Rendering</span>
                  <Badge variant="outline">Disabled</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Proxy Rotation</span>
                  <Badge variant="outline">Enabled</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Retry Attempts</span>
                  <span className="text-sm font-medium">3</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Timeout</span>
                  <span className="text-sm font-medium">30s</span>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results">
            <Card>
              <CardHeader>
                <CardTitle>Latest Results</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center justify-center py-12">
                  <Download className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium mb-2">Export Results</p>
                  <p className="text-sm text-muted-foreground mb-6">
                    Download the latest extracted data in your preferred format
                  </p>
                  <div className="flex gap-2">
                    <Button onClick={() => handleDownload('json')}>JSON</Button>
                    <Button variant="outline" onClick={() => handleDownload('csv')}>
                      CSV
                    </Button>
                    <Button variant="outline" onClick={() => handleDownload('xlsx')}>
                      Excel
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs">
            <Card>
              <CardHeader>
                <CardTitle>Execution Logs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg bg-muted p-4 font-mono text-xs space-y-1">
                  <div className="text-muted-foreground">[2026-01-20 14:30:00] Starting job execution...</div>
                  <div className="text-muted-foreground">[2026-01-20 14:30:02] Connecting to target URL...</div>
                  <div className="text-green-600">[2026-01-20 14:30:03] Connection successful</div>
                  <div className="text-muted-foreground">[2026-01-20 14:30:04] Executing queries...</div>
                  <div className="text-green-600">[2026-01-20 14:30:08] Extracted 1250 records</div>
                  <div className="text-muted-foreground">[2026-01-20 14:30:09] Saving results...</div>
                  <div className="text-green-600">[2026-01-20 14:30:12] Job completed successfully</div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Cost Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">This Month</span>
                    <span className="text-lg font-bold">$2.50</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Last Month</span>
                    <span className="text-sm">$2.30</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Average per Run</span>
                    <span className="text-sm">$0.017</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Projected (Month)</span>
                    <span className="text-sm font-medium">$2.80</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Data Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Total Records</span>
                    <span className="text-lg font-bold">186,000</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Storage Used</span>
                    <span className="text-sm">125 MB</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Avg Records/Run</span>
                    <span className="text-sm">1,240</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Data Quality</span>
                    <Badge variant="outline" className="text-green-600 border-green-600">
                      98.5%
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history">
            <Card>
              <CardHeader>
                <CardTitle>Execution History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {executionHistory.map((execution) => (
                    <div
                      key={execution.id}
                      className="flex items-center justify-between rounded-lg border border-border p-4"
                    >
                      <div className="flex items-center gap-4">
                        <StatusBadge
                          status={execution.status as any}
                          size="sm"
                        />
                        <div>
                          <p className="text-sm font-medium">{execution.timestamp}</p>
                          <p className="text-xs text-muted-foreground">
                            Runtime: {execution.runtime}s · Records: {execution.recordsExtracted.toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        View Details
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDelete}
        title="Delete Job"
        description="Are you sure you want to delete this job? This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
      />
    </AppLayout>
  );
}
