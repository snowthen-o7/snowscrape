/**
 * Export destination query/mutation hooks.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { destinationsAPI, type CreateDestinationInput, type ExportDestination } from '@/lib/api/destinations';
import { toast } from '@/lib/toast';

const KEY = ['export-destinations'] as const;

export function useDestinations() {
  const { session } = useSession();

  return useQuery<ExportDestination[]>({
    queryKey: KEY,
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      const data = await destinationsAPI.list(token);
      return data.destinations ?? [];
    },
    enabled: !!session,
    staleTime: 30_000,
  });
}

export function useCreateDestination() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation<ExportDestination, Error, CreateDestinationInput>({
    mutationFn: async (input: CreateDestinationInput) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return destinationsAPI.create(token, input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success('Destination created');
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to create destination');
    },
  });
}

export function useDeleteDestination() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (destinationId: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return destinationsAPI.delete(token, destinationId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success('Destination deleted');
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to delete destination');
    },
  });
}
