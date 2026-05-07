/**
 * API key query/mutation hooks.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { apiKeysAPI, type ApiKeyListItem, type CreateApiKeyResponse } from '@/lib/api';
import { toast } from '@/lib/toast';

export function useApiKeys() {
  const { session } = useSession();

  return useQuery<ApiKeyListItem[]>({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      const data = await apiKeysAPI.list(token);
      return data.keys ?? [];
    },
    enabled: !!session,
    staleTime: 30_000,
  });
}

export function useCreateApiKey() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation<CreateApiKeyResponse, Error, string>({
    mutationFn: async (name: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return apiKeysAPI.create(token, name);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to create API key');
    },
  });
}

export function useDeleteApiKey() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation<{ message: string }, Error, string>({
    mutationFn: async (apiKeyId: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return apiKeysAPI.delete(token, apiKeyId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      toast.success('API key revoked');
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to revoke API key');
    },
  });
}
