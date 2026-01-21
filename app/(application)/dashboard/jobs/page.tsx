'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { JobModal } from '@/components/JobModal';
import { JobCard } from '@/components/JobCard';
import { ResultPreviewModal } from '@/components/ResultPreviewModal';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/EmptyState';
import { DashboardSkeleton } from '@/components/LoadingSkeleton';
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
import { Job } from '@/lib/types';
import {
  Search,
  RefreshCw,
  Plus,
  BriefcaseIcon,
  LayoutGrid,
  List,
} from 'lucide-react';
import { toast } from '@/lib/toast';

export default function JobsPage() {
  const router = useRouter();
  const { isLoaded: isUserLoaded } = useUser();

  const {
    data: jobs = [],
    isLoading,
    isError,
    refetch,
  } = useJobs();

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
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Filter jobs
  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.source?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || job.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Action handlers
  const handleEdit = (job: Job) => {
    setJobModalOpen({ isOpen: true, jobDetails: job });
  };

  const handleDelete = async (jobId: string) => {
    try {
      await deleteJobMutation.mutateAsync(jobId);
      toast.success('Job deleted successfully');
    } catch {
      toast.error('Failed to delete job');
    }
  };

  const handlePause = async (jobId: string) => {
    try {
      await pauseJobMutation.mutateAsync(jobId);
      toast.success('Job paused');
    } catch {
      toast.error('Failed to pause job');
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await resumeJobMutation.mutateAsync(jobId);
      toast.success('Job resumed');
    } catch {
      toast.error('Failed to resume job');
    }
  };

  const handleViewResults = (job: Job) => {
    setPreviewModalOpen({ isOpen: true, job });
  };

  if (!isUserLoaded || isLoading) {
    return (
      <AppLayout>
        <DashboardSkeleton />
      </AppLayout>
    );
  }

  if (isError) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <p className="text-destructive mb-4">Failed to load jobs</p>
            <Button onClick={() => refetch()}>Try Again</Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        <PageHeader
          title="Jobs"
          description="Manage your scraping jobs"
          actions={
            <Button asChild>
              <Link href="/dashboard/jobs/new">
                <Plus className="h-4 w-4 mr-2" />
                New Job
              </Link>
            </Button>
          }
        />

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex flex-1 gap-4 w-full sm:w-auto">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              value={statusFilter}
              onValueChange={setStatusFilter}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Filter status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setViewMode('grid')}
              className={viewMode === 'grid' ? 'bg-muted' : ''}
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setViewMode('list')}
              className={viewMode === 'list' ? 'bg-muted' : ''}
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => refetch()}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Jobs Grid/List */}
        {filteredJobs.length === 0 ? (
          <EmptyState
            icon={<BriefcaseIcon className="h-12 w-12" />}
            title="No jobs found"
            description={
              searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first scraping job to get started'
            }
            action={
              !searchQuery && statusFilter === 'all'
                ? {
                    label: 'Create Job',
                    onClick: () => router.push('/dashboard/jobs/new'),
                  }
                : undefined
            }
          />
        ) : (
          <div
            className={
              viewMode === 'grid'
                ? 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3'
                : 'space-y-4'
            }
          >
            {filteredJobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                onClick={() => handleEdit(job)}
                onDelete={() => handleDelete(job.job_id)}
                onPause={() => handlePause(job.job_id)}
                onResume={() => handleResume(job.job_id)}
                onPreview={() => handleViewResults(job)}
              />
            ))}
          </div>
        )}

        {/* Job Stats Footer */}
        <div className="flex items-center gap-6 text-sm text-muted-foreground pt-4 border-t">
          <span>Total: {jobs.length} jobs</span>
          <span>Running: {jobs.filter((j) => j.status === 'running').length}</span>
          <span>Success: {jobs.filter((j) => j.status === 'success').length}</span>
          <span>Failed: {jobs.filter((j) => j.status === 'failed').length}</span>
        </div>
      </div>

      {/* Modals */}
      {jobModalOpen.isOpen && (
        <JobModal
          closeModal={() => setJobModalOpen({ isOpen: false, jobDetails: null })}
          jobDetails={jobModalOpen.jobDetails}
          session={(typeof window !== 'undefined' && (window as any).Clerk?.session) || null}
        />
      )}

      {previewModalOpen.isOpen && previewModalOpen.job && (
        <ResultPreviewModal
          closeModal={() => setPreviewModalOpen({ isOpen: false, job: null })}
          jobId={previewModalOpen.job.job_id}
          jobName={previewModalOpen.job.name}
          token={(typeof window !== 'undefined' && (window as any).Clerk?.session?.lastActiveToken) || null}
        />
      )}
    </AppLayout>
  );
}
