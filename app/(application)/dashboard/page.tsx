/**
 * Dashboard Page
 * Main application dashboard with analytics overview
 */

'use client';

import { useUser } from '@clerk/nextjs';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { StatCard } from '@snowforge/ui';
import { EmptyState } from '@snowforge/ui';
import { DashboardSkeleton } from '@/components/LoadingSkeleton';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { Button } from '@snowforge/ui';
import { useJobs } from '@/lib/hooks/useJobs';
import { useRealtimeJobs } from '@/lib/hooks/useRealtimeJobs';
import {
  RefreshCw,
  BriefcaseIcon,
  PlayCircleIcon,
  CheckCircle2Icon,
  XCircleIcon,
  ArrowRightIcon,
  TrendingUpIcon,
} from 'lucide-react';
import { toast } from '@/lib/toast';
import { LineChart, BarChart } from '@/components/charts';
import { OnboardingTour, QuickStartGuide } from '@/components/OnboardingTour';

export default function Dashboard() {
  const { isLoaded: isUserLoaded } = useUser();

  // Use both hooks: useJobs for initial load, useRealtimeJobs for updates
  const {
    data: initialJobs = [],
    isLoading,
    isError,
    refetch,
  } = useJobs();

  // Real-time updates (will fall back to polling if WebSocket unavailable)
  const {
    jobs: realtimeJobs,
    status: connectionStatus,
    refresh: refreshRealtime,
  } = useRealtimeJobs({ enabled: isUserLoaded });

  // Use realtime jobs if available, otherwise use initial jobs
  const jobs = realtimeJobs.length > 0 ? realtimeJobs : initialJobs;

  // Calculate metrics
  const totalJobs = jobs.length;
  const runningJobs = jobs.filter((job) => job.status === 'running').length;
  const successJobs = jobs.filter((job) => job.status === 'success').length;
  const failedJobs = jobs.filter((job) => job.status === 'failed').length;

  // Sample data for charts (in production, this would come from analytics API)
  const apiCallsData = [
    { date: 'Jan 14', calls: 1200 },
    { date: 'Jan 15', calls: 1890 },
    { date: 'Jan 16', calls: 2100 },
    { date: 'Jan 17', calls: 1750 },
    { date: 'Jan 18', calls: 2300 },
    { date: 'Jan 19', calls: 2800 },
    { date: 'Jan 20', calls: 3200 },
  ];

  const dataVolumeData = [
    { date: 'Jan 14', volume: 45 },
    { date: 'Jan 15', volume: 62 },
    { date: 'Jan 16', volume: 78 },
    { date: 'Jan 17', volume: 58 },
    { date: 'Jan 18', volume: 85 },
    { date: 'Jan 19', volume: 92 },
    { date: 'Jan 20', volume: 110 },
  ];

  const handleRefresh = () => {
    refetch();
    refreshRealtime();
    toast.success('Data refreshed');
  };

  // Show skeleton during initial load
  if (isLoading || !isUserLoaded) {
    return (
      <AppLayout>
        <DashboardSkeleton />
      </AppLayout>
    );
  }

  // Show error state with helpful options
  if (isError) {
    return (
      <AppLayout>
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="text-center space-y-4 max-w-md">
            <EmptyState
              icon={<XCircleIcon className="h-12 w-12" />}
              title="Unable to load dashboard data"
              description="We couldn't connect to the server. This might be a temporary issue."
              action={{
                label: 'Try Again',
                onClick: handleRefresh,
              }}
            />
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Page Header */}
        <PageHeader
          title="Dashboard"
          description="Overview of your scraping activity and analytics"
          actions={
            <div className="flex items-center gap-2">
              <ConnectionStatus
                isConnected={connectionStatus.isConnected}
                isPolling={connectionStatus.isPolling}
                connectionType={connectionStatus.connectionType}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isLoading}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}
                />
                Refresh
              </Button>
            </div>
          }
        />

        {/* Quick Start Guide */}
        <QuickStartGuide />

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Link href="/dashboard/jobs" className="block">
            <StatCard
              title="Total Jobs"
              value={totalJobs}
              icon={<BriefcaseIcon className="h-5 w-5" />}
            />
          </Link>
          <Link href="/dashboard/jobs?status=running" className="block">
            <StatCard
              title="Running"
              value={runningJobs}
              icon={<PlayCircleIcon className="h-5 w-5" />}
              trend={runningJobs > 0 ? 'up' : 'neutral'}
            />
          </Link>
          <Link href="/dashboard/jobs?status=success" className="block">
            <StatCard
              title="Successful"
              value={successJobs}
              icon={<CheckCircle2Icon className="h-5 w-5" />}
            />
          </Link>
          <Link href="/dashboard/jobs?status=failed" className="block">
            <StatCard
              title="Failed"
              value={failedJobs}
              icon={<XCircleIcon className="h-5 w-5" />}
              trend={failedJobs > 0 ? 'down' : 'neutral'}
            />
          </Link>
        </div>

        {/* Performance Charts */}
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-border bg-card p-6">
            <LineChart
              data={apiCallsData}
              xDataKey="date"
              yDataKey="calls"
              lineColor="#00D9FF"
              height={250}
              title="API Calls (Last 7 Days)"
            />
          </div>
          <div className="rounded-2xl border border-border bg-card p-6">
            <BarChart
              data={dataVolumeData}
              xDataKey="date"
              yDataKey="volume"
              barColor="#00D9FF"
              height={250}
              title="Data Volume (MB)"
            />
          </div>
        </div>

        {/* Quick Actions / Recent Activity */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Quick Actions */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <Link
                href="/dashboard/jobs"
                className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <BriefcaseIcon className="h-5 w-5 text-muted-foreground" />
                  <span className="font-medium">View All Jobs</span>
                </div>
                <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
              </Link>
              <Link
                href="/dashboard/templates"
                className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <TrendingUpIcon className="h-5 w-5 text-muted-foreground" />
                  <span className="font-medium">Browse Templates</span>
                </div>
                <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
              </Link>
              <Link
                href="/dashboard/analytics"
                className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <TrendingUpIcon className="h-5 w-5 text-muted-foreground" />
                  <span className="font-medium">View Analytics</span>
                </div>
                <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
              </Link>
            </div>
          </div>

          {/* Recent Activity Summary */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Activity Summary</h3>
            {totalJobs === 0 ? (
              <div className="text-center py-8">
                <BriefcaseIcon className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">No jobs yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Create your first job using the sidebar
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Success Rate</span>
                  <span className="font-semibold">
                    {totalJobs > 0
                      ? Math.round((successJobs / totalJobs) * 100)
                      : 0}
                    %
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all"
                    style={{
                      width: `${totalJobs > 0 ? (successJobs / totalJobs) * 100 : 0}%`,
                    }}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <p className="text-2xl font-bold text-green-600">{successJobs}</p>
                    <p className="text-xs text-muted-foreground">Completed</p>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <p className="text-2xl font-bold text-blue-600">{runningJobs}</p>
                    <p className="text-xs text-muted-foreground">In Progress</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Onboarding Tour */}
      <OnboardingTour />
    </AppLayout>
  );
}
