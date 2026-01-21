/**
 * Dashboard Page (Refactored)
 * Main application dashboard with jobs overview
 */

'use client';

import { useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { JobModal } from '@/components/JobModal';
import { JobCard } from '@/components/JobCard';
import { ResultPreviewModal } from '@/components/ResultPreviewModal';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageHeader } from '@/components/PageHeader';
import { StatCard } from '@/components/StatCard';
import { EmptyState } from '@/components/EmptyState';
import { DashboardSkeleton } from '@/components/LoadingSkeleton';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useJobs,
  useDeleteJob,
  usePauseJob,
  useResumeJob,
} from '@/lib/hooks/useJobs';
import { useRealtimeJobs } from '@/lib/hooks/useRealtimeJobs';
import { Job } from '@/lib/types';
import {
  Search,
  RefreshCw,
  Plus,
  BriefcaseIcon,
  PlayCircleIcon,
  CheckCircle2Icon,
  XCircleIcon,
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

  const deleteJobMutation = useDeleteJob();
  const pauseJobMutation = usePauseJob();
  const resumeJobMutation = useResumeJob();

  const [jobModalOpen, setJobModalOpen] = useState<{
    isOpen: boolean;
    jobDetails?: Job | null;
  }>({ isOpen: false, jobDetails: null });

  const [previewModalOpen, setPreviewModalOpen] = useState<{
    isOpen: boolean;
    job?: Job | null;
  }>({ isOpen: false, job: null });

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

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

  // Filter and search jobs
  const filteredJobs = jobs.filter((job) => {
    const matchesSearch = job.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || job.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Handle job actions
  const handlePauseJob = async (jobId: string) => {
    try {
      await pauseJobMutation.mutateAsync(jobId);
    } catch (error) {
      // Error is handled by the mutation
    }
  };

  const handleResumeJob = async (jobId: string) => {
    try {
      await resumeJobMutation.mutateAsync(jobId);
    } catch (error) {
      // Error is handled by the mutation
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    try {
      await deleteJobMutation.mutateAsync(jobId);
    } catch (error) {
      // Error is handled by the mutation
    }
  };

  const handleDownloadJob = async (jobId: string, format: string) => {
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

  const handleRefresh = () => {
    refetch();
    refreshRealtime();
    toast.success('Jobs refreshed');
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
          <div className="text-center space-y-4">
            <EmptyState
              icon={<XCircleIcon className="h-12 w-12" />}
              title="Unable to load jobs"
              description="We couldn't connect to the server. This might be a temporary issue."
              action={{
                label: 'Try Again',
                onClick: handleRefresh,
              }}
            />
            <div className="pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground mb-3">
                Or start fresh by creating a new job
              </p>
              <Button
                variant="outline"
                onClick={() => setJobModalOpen({ isOpen: true, jobDetails: null })}
              >
                <Plus className="mr-2 h-4 w-4" />
                Create New Job
              </Button>
            </div>
          </div>
        </div>

        {/* Keep modal available even in error state */}
        {jobModalOpen.isOpen && (
          <JobModal
            closeModal={() =>
              setJobModalOpen({ isOpen: false, jobDetails: null })
            }
            jobDetails={jobModalOpen.jobDetails}
            session={(window as any).Clerk?.session || null}
          />
        )}
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Page Header */}
        <PageHeader
          title="Dashboard"
          description="Manage your scraping jobs and view analytics"
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
              <Button
                size="sm"
                onClick={() =>
                  setJobModalOpen({ isOpen: true, jobDetails: null })
                }
              >
                <Plus className="mr-2 h-4 w-4" />
                New Job
              </Button>
            </div>
          }
        />

        {/* Quick Start Guide */}
        <QuickStartGuide />

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Jobs"
            value={totalJobs}
            icon={<BriefcaseIcon className="h-5 w-5" />}
          />
          <StatCard
            title="Running"
            value={runningJobs}
            icon={<PlayCircleIcon className="h-5 w-5" />}
            trend={runningJobs > 0 ? 'up' : 'neutral'}
          />
          <StatCard
            title="Successful"
            value={successJobs}
            icon={<CheckCircle2Icon className="h-5 w-5" />}
          />
          <StatCard
            title="Failed"
            value={failedJobs}
            icon={<XCircleIcon className="h-5 w-5" />}
            trend={failedJobs > 0 ? 'down' : 'neutral'}
          />
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

        {/* Filters */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search jobs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Jobs Grid */}
        {filteredJobs.length === 0 ? (
          <EmptyState
            icon={<BriefcaseIcon className="h-12 w-12" />}
            title={
              searchQuery || statusFilter !== 'all'
                ? 'No jobs found'
                : 'No jobs yet'
            }
            description={
              searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'Create your first scraping job to get started.'
            }
            action={
              searchQuery || statusFilter !== 'all'
                ? {
                    label: 'Clear Filters',
                    onClick: () => {
                      setSearchQuery('');
                      setStatusFilter('all');
                    },
                  }
                : {
                    label: 'Create Job',
                    onClick: () =>
                      setJobModalOpen({ isOpen: true, jobDetails: null }),
                  }
            }
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredJobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                onClick={() =>
                  setJobModalOpen({ isOpen: true, jobDetails: job })
                }
                onPause={() => handlePauseJob(job.job_id)}
                onResume={() => handleResumeJob(job.job_id)}
                onDelete={() => handleDeleteJob(job.job_id)}
                onDownload={(format) => handleDownloadJob(job.job_id, format)}
                onPreview={() =>
                  setPreviewModalOpen({ isOpen: true, job: job })
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {jobModalOpen.isOpen && (
        <JobModal
          closeModal={() =>
            setJobModalOpen({ isOpen: false, jobDetails: null })
          }
          jobDetails={jobModalOpen.jobDetails}
          session={(window as any).Clerk?.session || null}
        />
      )}

      {previewModalOpen.isOpen && previewModalOpen.job && (
        <ResultPreviewModal
          jobId={previewModalOpen.job.job_id}
          jobName={previewModalOpen.job.name}
          token={(window as any).Clerk?.session?.lastActiveToken || null}
          closeModal={() => setPreviewModalOpen({ isOpen: false, job: null })}
        />
      )}

      {/* Onboarding Tour */}
      <OnboardingTour />
    </AppLayout>
  );
}
