/**
 * Jobs Query Hooks
 * React Query hooks for job-related data fetching
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { jobsAPI, type CreateJobDTO, type UpdateJobDTO } from '@/lib/api';
import { toast } from '@/lib/toast';
import { Job } from '@/lib/types';

/**
 * Fetch all jobs
 */
export function useJobs() {
  const { session } = useSession();

  return useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.list(token);
    },
    enabled: !!session,
    // Refetch every 30 seconds to keep data fresh
    refetchInterval: 30000,
  });
}

/**
 * Fetch a single job by ID
 */
export function useJob(id: string | null) {
  const { session } = useSession();

  return useQuery({
    queryKey: ['jobs', id],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token || !id) throw new Error('Not authenticated or missing ID');
      return jobsAPI.get(id, token);
    },
    enabled: !!session && !!id,
  });
}

/**
 * Create a new job
 */
export function useCreateJob() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (data: CreateJobDTO) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.create(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job created successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to create job', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Update an existing job
 */
export function useUpdateJob() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateJobDTO }) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.update(id, data, token);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['jobs', variables.id] });
      toast.success('Job updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update job', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Delete a job
 */
export function useDeleteJob() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.delete(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job deleted successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to delete job', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Pause a job
 */
export function usePauseJob() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.pause(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job paused');
    },
    onError: (error: any) => {
      toast.error('Failed to pause job', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Resume a job
 */
export function useResumeJob() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.resume(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job resumed');
    },
    onError: (error: any) => {
      toast.error('Failed to resume job', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Run a job immediately
 */
export function useRunJob() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return jobsAPI.run(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job started');
    },
    onError: (error: any) => {
      toast.error('Failed to run job', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Fetch job results
 */
export function useJobResults(id: string | null, limit = 100) {
  const { session } = useSession();

  return useQuery({
    queryKey: ['jobs', id, 'results', limit],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token || !id) throw new Error('Not authenticated or missing ID');
      return jobsAPI.results(id, token, limit);
    },
    enabled: !!session && !!id,
  });
}
